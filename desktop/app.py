# -*- coding: utf-8 -*-
"""
桌面客户端统一入口（PyInstaller 冻结目标）

单个可执行文件承担两个角色，避免多 EXE 与 .app 内路径问题：

    VideoDevour              → 桌面壳：拉起自身子进程（--backend-only）并开窗口
    VideoDevour --backend-only → 后端服务：uvicorn 托管 API + 前端产物

壳通过 sys.executable 派生后端，因此冻结后无需在包内查找第二个可执行文件。
"""
import sys


def main():
    # multiprocessing 在 Windows 冻结环境下需要 freeze_support（防递归启动）
    import multiprocessing
    multiprocessing.freeze_support()

    if "--backend-only" in sys.argv:
        # 去掉角色标记后交给后端入口解析剩余参数
        sys.argv = [a for a in sys.argv if a != "--backend-only"]
        from desktop import backend_server
        backend_server.main()
    else:
        from desktop import shell
        shell.main()


if __name__ == "__main__":
    main()
