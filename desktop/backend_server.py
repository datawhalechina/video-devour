# -*- coding: utf-8 -*-
"""
桌面客户端后端入口（PyInstaller 冻结目标）

职责：
1. 冻结环境下初始化数据目录（VIDEO_DEVOUR_DATA_DIR 默认指向用户数据目录）
2. 绑定 127.0.0.1 的随机空闲端口（由 OS 分配，避免先探测再启动的竞争）
3. 通过 stdout 握手行向桌面壳报告实际端口
4. 启动 uvicorn 托管 API + 前端静态产物

握手协议：
- 优先写握手文件（--handshake-file 指定路径）：{"type": "ready", "port": ..., "pid": ...}
  文件方式在 macOS 窗口模式（console=False，stdout 不可用）下仍然可靠。
- 同时向 stdout 输出同样的 JSON 行，便于源码模式调试与 CI。
"""
import json
import os
import socket
import sys
import argparse
import logging
import threading
import time
from pathlib import Path

_HANDSHAKE_FILE = None


def _emit(payload: dict):
    """报告握手信息：写文件（主）+ stdout（辅）。"""
    line = json.dumps(payload, ensure_ascii=False)
    if _HANDSHAKE_FILE:
        try:
            tmp = _HANDSHAKE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(line)
            os.replace(tmp, _HANDSHAKE_FILE)  # 原子替换，避免壳读到半截内容
        except Exception as e:
            logging.error(f"写入握手文件失败: {e}")
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        # 窗口模式下 stdout 不可用，忽略
        pass


def _prepare_runtime(args):
    """冻结/客户端模式下确定数据目录与前端产物位置。"""
    # 源码模式下把项目根加入 sys.path（冻结模式下由 spec 的 pathex 处理）
    if not getattr(sys, "frozen", False):
        project_root = str(Path(__file__).resolve().parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

    if args.data_dir:
        os.environ["VIDEO_DEVOUR_DATA_DIR"] = os.path.abspath(os.path.expanduser(args.data_dir))
    if args.frontend_dist:
        os.environ["VIDEO_DEVOUR_FRONTEND_DIST"] = os.path.abspath(os.path.expanduser(args.frontend_dist))
    if args.ffmpeg_dir:
        os.environ["VIDEO_DEVOUR_FFMPEG"] = os.path.join(os.path.abspath(args.ffmpeg_dir), "ffmpeg")
        os.environ["VIDEO_DEVOUR_FFPROBE"] = os.path.join(os.path.abspath(args.ffmpeg_dir), "ffprobe")


def _bind_socket(host: str, preferred: int) -> socket.socket:
    """
    绑定监听 socket 并保持打开。

    绑定后立即交给 uvicorn 使用，不做"探测端口→关闭→再启动"的操作：
    那会在关闭与重新绑定之间留下竞争窗口，端口可能被其它进程抢占。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, preferred))
    sock.listen(128)
    return sock


def _watch_parent(parent_pid: int):
    """
    监测指定的父进程（桌面壳）是否存活。

    仅当壳通过 --parent-pid 显式传入 PID 时启用：
    独立启动（终端调试、CI 冒烟测试）时父进程可能是会立刻退出的 shell，
    若按 os.getppid() 推断会把正常服务误杀。

    壳被 SIGKILL 时无法执行自己的清理逻辑，后端需自行退出，
    否则会变成孤儿进程继续占用端口与内存（方案 4.3 要求的回收机制）。
    """
    if not parent_pid or parent_pid <= 1:
        return

    def _loop():
        while True:
            time.sleep(2)
            if os.getppid() != parent_pid:
                logging.info("父进程已退出，后端自行终止")
                os._exit(0)

    threading.Thread(target=_loop, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="VideoDevour 桌面后端")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（客户端模式固定回环）")
    parser.add_argument("--port", type=int, default=0, help="端口，0 表示自动分配")
    parser.add_argument("--data-dir", default=None, help="可写数据目录")
    parser.add_argument("--frontend-dist", default=None, help="前端构建产物目录")
    parser.add_argument("--ffmpeg-dir", default=None, help="捆绑的 ffmpeg/ffprobe 所在目录")
    parser.add_argument("--handshake-file", default=None, help="握手信息写入路径（窗口模式下 stdout 不可用）")
    parser.add_argument("--parent-pid", type=int, default=0, help="桌面壳 PID；设置后壳退出时后端自行终止")
    args = parser.parse_args()

    global _HANDSHAKE_FILE
    if args.handshake_file:
        _HANDSHAKE_FILE = os.path.abspath(os.path.expanduser(args.handshake_file))

    _prepare_runtime(args)

    # 日志走 stderr：stdout 仅用于握手协议，避免日志行混入 JSON 解析
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    sock = None
    try:
        import uvicorn
        from backend.api.main import app

        _watch_parent(args.parent_pid)

        # 先绑定再握手：报告的端口就是实际监听端口，不存在竞争
        sock = _bind_socket(args.host, args.port)
        port = sock.getsockname()[1]
        _emit({"type": "ready", "port": port, "pid": os.getpid(), "protocol": 1})

        config = uvicorn.Config(app, log_level="info")
        server = uvicorn.Server(config)
        server.run(sockets=[sock])
    except Exception as e:
        logging.exception("后端启动失败")
        _emit({"type": "error", "message": str(e)})
        sys.exit(1)
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    # PyInstaller 多进程（如 multiprocessing）在 Windows 下需要 freeze_support
    import multiprocessing
    multiprocessing.freeze_support()
    main()
