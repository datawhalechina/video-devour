# -*- coding: utf-8 -*-
"""HTML → PNG / PDF 导出（无头 Chrome，经 CDP 协议精确控制）。

供 HTML 速读页传播使用：全页长图（captureBeyondViewport，无需预知页高）
与 A4 PDF（printBackground + 页面自带 @page 分页样式）。
实现思路参考 answer-me-with-html 的 src/video/export.js（MIT）：
spawn Chrome --headless=new --remote-debugging-port=0，读 DevToolsActivePort
拿端口，再连页面目标的 WebSocket 调 CDP。
"""
import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Optional

_EXPORT_TIMEOUT_SECONDS = 90          # 单次导出总上限（含 Chrome 冷启动）
_LOAD_TIMEOUT_SECONDS = 20

# 各平台浏览器候选路径（与 answer-me-with-html 保持一致的常见安装位置）
_CHROME_CANDIDATES = {
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ],
    "win32": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
}
_CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "microsoft-edge")


class HtmlExportError(RuntimeError):
    """导出失败（找不到浏览器 / Chrome 启动失败 / 渲染超时）。"""


def find_browser() -> Optional[str]:
    """定位可用的 Chromium 系浏览器；环境变量 VIDEO_DEVOUR_BROWSER 可强制指定。"""
    override = os.getenv("VIDEO_DEVOUR_BROWSER", "").strip()
    if override:
        return override if Path(override).exists() else None
    import sys
    for path in _CHROME_CANDIDATES.get(sys.platform, []):
        if Path(path).exists():
            return path
    for name in _CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


class _ChromePage:
    """无头 Chrome 的一个页面标签（CDP over WebSocket，同步客户端）。"""

    def __init__(self):
        self.browser: Optional[subprocess.Popen] = None
        self.ws = None
        self._msg_id = 0
        self._events: list = []

    def __enter__(self):
        self._launch()
        return self

    def __exit__(self, *exc):
        self.close()

    def _launch(self):
        exe = find_browser()
        if not exe:
            raise HtmlExportError(
                "未找到 Chrome / Chromium / Edge，无法导出 PNG / PDF。"
                "可安装 Chrome，或用环境变量 VIDEO_DEVOUR_BROWSER 指定浏览器路径。")
        user_data = tempfile.mkdtemp(prefix="vd_chrome_")
        self._user_data = user_data
        try:
            self.browser = subprocess.Popen(
                [exe, "--headless=new", "--remote-debugging-port=0",
                 f"--user-data-dir={user_data}", "--no-first-run",
                 "--disable-gpu", "--hide-scrollbars", "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL)
        except OSError as e:
            raise HtmlExportError(f"无法启动浏览器（{exe}）: {e}")

        # 端口写在 user-data-dir/DevToolsActivePort：首行端口，次行 ws 路径
        port_file = Path(user_data) / "DevToolsActivePort"
        deadline = time.time() + 15
        while time.time() < deadline:
            if port_file.exists():
                try:
                    port = int(port_file.read_text().split("\n")[0])
                    break
                except (ValueError, IndexError):
                    pass
            if self.browser.poll() is not None:
                err = (self.browser.stderr.read() or b"")[:300].decode("utf-8", "ignore")
                raise HtmlExportError(f"浏览器启动即退出: {err}")
            time.sleep(0.1)
        else:
            raise HtmlExportError("浏览器调试端口 15s 内未就绪")

        try:
            targets = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=5).read())
            page_ws = next(t["webSocketDebuggerUrl"] for t in targets
                           if t.get("type") == "page")
        except Exception as e:
            raise HtmlExportError(f"无法连接浏览器调试接口: {e}")

        from websockets.sync.client import connect
        # captureScreenshot 的返回帧可达数十 MB（全页 PNG base64），需放大帧上限
        self.ws = connect(page_ws, open_timeout=10, close_timeout=5, max_size=64 * 1024 * 1024)
        self.call("Page.enable")
        self.call("Runtime.enable")

    def close(self):
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self.browser is not None:
            try:
                self.browser.terminate()
                self.browser.wait(timeout=5)
            except Exception:
                self.browser.kill()
            self.browser = None
        if getattr(self, "_user_data", None):
            shutil.rmtree(self._user_data, ignore_errors=True)
            self._user_data = None

    def call(self, method: str, params: dict = None, timeout: float = _LOAD_TIMEOUT_SECONDS):
        """发一条 CDP 指令并等对应响应（事件先入队缓存）。"""
        self._msg_id += 1
        mid = self._msg_id
        self.ws.send(json.dumps({"id": mid, "method": method,
                                 "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                raw = self.ws.recv(timeout=max(0.1, deadline - time.time()))
            except TimeoutError:
                break
            msg = json.loads(raw)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise HtmlExportError(f"CDP {method} 失败: {msg['error']}")
                return msg.get("result", {})
            if "method" in msg:
                self._events.append(msg["method"])
        raise HtmlExportError(f"CDP {method} 超时")

    def wait_event(self, name: str, timeout: float = _LOAD_TIMEOUT_SECONDS):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if name in self._events:
                self._events.remove(name)
                return
            try:
                raw = self.ws.recv(timeout=max(0.1, deadline - time.time()))
                msg = json.loads(raw)
                if msg.get("method") == name:
                    return
                if "method" in msg:
                    self._events.append(msg["method"])
            except TimeoutError:
                break
        raise HtmlExportError(f"等待页面事件 {name} 超时")

    def navigate(self, url: str):
        self._events.clear()
        self.call("Page.navigate", {"url": url})
        self.wait_event("Page.loadEventFired")

    def evaluate(self, expression: str):
        result = self.call("Runtime.evaluate",
                           {"expression": expression, "returnByValue": True})
        return (result.get("result") or {}).get("value")


def _file_url(path) -> str:
    return Path(path).resolve().as_uri()


def _prepare_page(page: _ChromePage, html_path, mode: str):
    """导航并固定导出状态：锁定亮/暗主题、隐藏工具栏、等待图片解码。"""
    page.navigate(_file_url(html_path))
    mode_js = mode if mode in ("light", "dark") else "light"
    page.evaluate(f"document.documentElement.dataset.mode={json.dumps(mode_js)}")
    page.evaluate("document.body.classList.add('am-export')")
    # data URI 图片解码是异步的；等两帧确保 paint 完成后再截图
    page.call("Runtime.evaluate", {
        "expression": "new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))",
        "awaitPromise": True, "returnByValue": True,
    }, timeout=15)


def export_png(html_path, out_png, width: int = 1600, scale: int = 2,
               mode: str = "light") -> str:
    """HTML → 全页 PNG 长图（scale=2 为 2 倍分辨率，适合传播时保持清晰）。"""
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with _ChromePage() as page:
        page.call("Emulation.setDeviceMetricsOverride",
                  {"width": width, "height": 900, "deviceScaleFactor": scale,
                   "mobile": False}, timeout=10)
        _prepare_page(page, html_path, mode)
        result = page.call("Page.captureScreenshot",
                           {"format": "png", "captureBeyondViewport": True},
                           timeout=_EXPORT_TIMEOUT_SECONDS)
        data = base64.b64decode(result["data"])
    out_png.write_bytes(data)
    logging.info(f"HTML 已导出 PNG: {out_png}（{len(data) / 1024:.0f}KB, {width}px×{scale}）")
    return str(out_png)


def export_pdf(html_path, out_pdf, mode: str = "light") -> str:
    """HTML → A4 PDF（页面自带 @page 与分页样式，printBackground 保留底色）。"""
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with _ChromePage() as page:
        _prepare_page(page, html_path, mode)
        result = page.call("Page.printToPDF",
                           {"printBackground": True, "preferCSSPageSize": True},
                           timeout=_EXPORT_TIMEOUT_SECONDS)
        data = base64.b64decode(result["data"])
    out_pdf.write_bytes(data)
    logging.info(f"HTML 已导出 PDF: {out_pdf}（{len(data) / 1024:.0f}KB）")
    return str(out_pdf)
