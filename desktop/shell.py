# -*- coding: utf-8 -*-
"""
VideoDevour 桌面壳（pywebview）

职责边界（方案 4.2）：
- 开窗口、加载本地服务、原生文件选择/另存为/打开目录
- 拉起并守护后端进程，退出时确保进程树被回收
- 单实例：二次启动唤起已有窗口
- 不向页面暴露任意 shell 执行或任意路径读取

启动流程：
    拉起后端 → 读 stdout 握手行拿到实际端口 → 轮询 /api/health 就绪 → 加载页面
"""
import json
import os
import subprocess
import sys
import threading
import time
import logging
from pathlib import Path

import webview

APP_NAME = "VideoDevour"
HANDSHAKE_TIMEOUT = 60          # 等待后端报告端口的秒数
HEALTH_TIMEOUT = 30             # 等待服务就绪的秒数
WINDOW_TITLE = "VideoDevour · 视频知识工作台"


def _exe_dir() -> Path:
    """冻结后为可执行文件所在目录（壳与后端 EXE 同级）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resource_root() -> Path:
    """只读资源根：_MEIPASS（onedir 下为 _internal / Frameworks）。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", _exe_dir()))
    return Path(__file__).resolve().parent.parent


def _data_root() -> Path:
    """与 backend/runtime/paths.py 保持一致的平台约定。"""
    explicit = os.getenv("VIDEO_DEVOUR_DATA_DIR")
    if explicit:
        root = Path(explicit).expanduser()
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
        root = Path(base) / APP_NAME
    else:
        root = Path.home() / ".local" / "share" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


class BackendProcess:
    """后端子进程的生命周期管理。"""

    def __init__(self):
        self.proc = None
        self.port = None
        self.log_file = None

    def start(self) -> int:
        """启动后端并等待端口握手，返回实际端口。"""
        res_root = _resource_root()
        data_root = _data_root()

        if getattr(sys, "frozen", False):
            # 冻结模式：以 --backend-only 派生自身作为后端进程
            # （单可执行文件承担双角色，避免在 .app 内查找第二个 EXE）
            cmd = [sys.executable, "--backend-only"]
        else:
            cmd = [sys.executable, str(res_root / "desktop" / "app.py"), "--backend-only"]

        # 握手文件：窗口模式（console=False）下 stdout 不可用，必须走文件
        handshake_file = data_root / "backend_handshake.json"
        if handshake_file.exists():
            try:
                handshake_file.unlink()
            except OSError:
                pass

        cmd += [
            "--host", "127.0.0.1",
            "--port", "0",
            "--data-dir", str(data_root),
            "--frontend-dist", str(res_root / "frontend" / "dist"),
            "--ffmpeg-dir", str(res_root / "bin"),
            "--handshake-file", str(handshake_file),
            # 显式传壳的 PID：后端据此在壳被强杀时自行退出。
            # 不传则后端不做父进程监测（终端调试/CI 场景的父进程可能是会立刻退出的 shell）。
            "--parent-pid", str(os.getpid()),
        ]

        # 后端日志落盘到数据目录，便于诊断启动失败
        log_path = data_root / "logs"
        log_path.mkdir(parents=True, exist_ok=True)
        self.log_file = open(log_path / "backend.log", "a", encoding="utf-8")

        creationflags = 0
        if sys.platform.startswith("win"):
            # 独立进程组 + 不弹出控制台窗口
            # （后端 exe 以 console=True 打包，否则 uvicorn 在无标准描述符时会静默退出）
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=self.log_file,
            text=True,
            creationflags=creationflags,
        )

        # 轮询握手文件（同时容忍 stdout 方式，便于源码模式调试）
        deadline = time.time() + HANDSHAKE_TIMEOUT
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("后端进程已退出，请查看 logs/backend.log")
            if handshake_file.exists():
                try:
                    msg = json.loads(handshake_file.read_text(encoding="utf-8").strip())
                except (json.JSONDecodeError, OSError):
                    time.sleep(0.2)
                    continue
                if msg.get("type") == "ready":
                    self.port = msg["port"]
                    return self.port
                if msg.get("type") == "error":
                    raise RuntimeError(f"后端启动失败: {msg.get('message')}")
            time.sleep(0.2)
        raise RuntimeError("等待后端就绪超时")

    def wait_healthy(self, timeout: int = HEALTH_TIMEOUT) -> bool:
        """轮询 /api/health，确认服务可响应。"""
        import urllib.request

        url = f"http://127.0.0.1:{self.port}/api/health"
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                time.sleep(0.3)
        return False

    def stop(self):
        """终止后端进程树。"""
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except Exception as e:
            logging.warning(f"终止后端进程失败: {e}")
        finally:
            if self.log_file:
                try:
                    self.log_file.close()
                except Exception:
                    pass


class Bridge:
    """
    暴露给前端的原生桥（仅文件操作与窗口操作）。

    注意：窗口引用必须是下划线私有属性（`_window`）。
    pywebview 注入 js_api 时会递归展开对象的**公开**属性（webview/util.py 的
    get_functions），只跳过下划线开头的名字。若窗口引用是公开属性（如 `self.window`），
    它会一路走进原生窗口对象图：
        window.native.AccessibilityObject.Bounds.Empty.Empty.Empty...
    WinForms 的 `Rectangle.Empty` 每次返回新实例，pywebview 靠 id() 去重因此失效，
    导致无限递归（Windows 实测：窗口卡死、终端刷满 maximum recursion depth exceeded）。
    """

    def __init__(self, window=None):
        self._window = window

    def pick_video(self):
        """选择视频文件，返回绝对路径。"""
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("视频文件 (*.mp4;*.mov;*.mkv;*.avi;*.webm;*.flv;*.m4v)", "所有文件 (*.*)"),
        )
        return result[0] if result else None

    def save_as(self, suggested_name: str = "export.md", content: str = ""):
        """另存为：返回保存路径。"""
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=suggested_name
        )
        if not result:
            return None
        path = result if isinstance(result, str) else result[0]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def open_path(self, path: str):
        """在系统文件管理器中打开路径。"""
        target = Path(path).expanduser()
        if not target.exists():
            return False
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        elif sys.platform.startswith("win"):
            os.startfile(str(target))  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True


def _single_instance_lock():
    """
    单实例锁：已在运行则返回 False。

    使用文件锁而非进程名匹配——按进程名清理会误杀同名的无关进程（方案 6.2）。
    """
    lock_path = _data_root() / "app.lock"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
        if sys.platform.startswith("win"):
            import msvcrt
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError:
                os.close(fd)
                return False
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                return False
        return fd  # 保持打开以持有锁
    except Exception as e:
        logging.warning(f"单实例锁创建失败，继续启动: {e}")
        return True


def _install_signal_handlers(backend: "BackendProcess"):
    """
    处理外部终止信号，确保后端进程被回收。

    没有这段处理时，`kill`/系统退出只会终止壳本身，后端子进程会变成孤儿继续监听端口
    （实测残留）。这里统一转成"清理后退出"。
    """
    import signal

    def _handler(signum, _frame):
        logging.info(f"收到信号 {signum}，正在退出...")
        backend.stop()
        os._exit(0)

    for sig in (signal.SIGTERM, signal.SIGINT, getattr(signal, "SIGHUP", None)):
        if sig is not None:
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError):
                # 非主线程或平台不支持时忽略
                pass


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    lock = _single_instance_lock()
    if lock is False:
        logging.info("已有实例在运行，退出本次启动")
        return

    backend = BackendProcess()
    _install_signal_handlers(backend)
    try:
        port = backend.start()
        if not backend.wait_healthy():
            raise RuntimeError("后端服务未能在预期时间内就绪，请查看 logs/backend.log")
    except Exception as e:
        backend.stop()
        logging.error(f"启动失败: {e}")
        # 无窗口时用系统弹窗告知失败原因
        try:
            webview.create_window("VideoDevour 启动失败", html=f"<h3>启动失败</h3><p>{e}</p>")
            webview.start()
        except Exception:
            pass
        return

    bridge = Bridge()
    window = webview.create_window(
        WINDOW_TITLE,
        f"http://127.0.0.1:{port}/",
        js_api=bridge,
        width=1280,
        height=860,
        min_size=(900, 600),
    )
    # 赋给私有属性（不可写成 bridge.window，否则触发 pywebview 递归展开原生窗口对象）
    bridge._window = window

    def _on_closed():
        backend.stop()

    window.events.closed += _on_closed

    try:
        webview.start()
    finally:
        backend.stop()


if __name__ == "__main__":
    main()
