# -*- coding: utf-8 -*-
"""抓取指定标题的窗口为 PNG（DPI 感知）。

用法: python capture_window.py <标题子串> <输出路径> [--client]
"""
import ctypes
import sys
import time

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 物理像素坐标

import win32gui
from PIL import ImageGrab


def _force_foreground(hwnd):
    """把窗口可靠地置于最前（SetForegroundWindow 单独调用常被系统拒绝）。"""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    try:
        u.ShowWindow(hwnd, 9)  # SW_RESTORE
        fg = u.GetForegroundWindow()
        if fg == hwnd:
            return
        cur_tid = k.GetCurrentThreadId()
        fg_tid = u.GetWindowThreadProcessId(fg, None)
        tgt_tid = u.GetWindowThreadProcessId(hwnd, None)
        u.AttachThreadInput(cur_tid, fg_tid, True)
        u.AttachThreadInput(cur_tid, tgt_tid, True)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        u.AttachThreadInput(cur_tid, fg_tid, False)
        u.AttachThreadInput(cur_tid, tgt_tid, False)
    except Exception as e:
        print("foreground warn:", e)


def find_window(substr: str):
    hits = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if substr in title:
            rect = win32gui.GetWindowRect(hwnd)
            # 只要有一定尺寸的真实窗口
            if rect[2] - rect[0] > 300 and rect[3] - rect[1] > 300:
                hits.append((hwnd, title, rect))

    win32gui.EnumWindows(cb, None)
    return hits


def capture(title_substr: str, out_path: str, client_only: bool = False, pad: int = 0):
    hits = find_window(title_substr)
    if not hits:
        print(f"NOT FOUND: {title_substr}")
        return 1
    hwnd, title, rect = hits[0]
    _force_foreground(hwnd)
    time.sleep(1.2)
    if client_only:
        l, t, r, b = win32gui.GetClientRect(hwnd)
        # GetClientRect 是 0,0 起；转屏幕坐标
        sx, sy = win32gui.ClientToScreen(hwnd, (l, t))
        ex, ey = win32gui.ClientToScreen(hwnd, (r, b))
        l, t, r, b = sx, sy, ex, ey
    else:
        l, t, r, b = rect
    box = (l - pad, t - pad, r + pad, b + pad)
    img = ImageGrab.grab(bbox=box, all_screens=True)
    img.save(out_path)
    print(f"SAVED {out_path}  size={img.size}  box={box}  title={title!r}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    sys.exit(capture(args[0], args[1], client_only="--client" in flags))
