# -*- coding: utf-8 -*-
"""
一键读取本机浏览器 Cookie（B站 / YouTube / 腾讯元宝）

原理：用户在本机浏览器（Chrome/Edge/Firefox/Safari 等）中登录过目标网站后，
登录 cookie 存储在浏览器的本地 cookie 数据库中。本模块用 browser-cookie3
按域名定向读取（仅读取三个目标域，不接触其他任何网站的 cookie），
自动填入设置控制台对应字段，免去手动 F12 复制。

注意：
- macOS 首次读取 Chrome/Edge 时系统会弹出钥匙串授权，点「允许」即可
- Windows 下 Chrome/Edge 127+ 的 cookie 受 App-Bound 加密保护可能读取
  失败，可改用 Firefox 或手动粘贴
- 单个浏览器读取限时，超时按失败处理（多半在等钥匙串授权）
"""
import logging
import multiprocessing as mp
import time
from typing import Dict

READ_TIMEOUT_SECONDS = 20
AUTO_ORDER = ["chrome", "edge", "firefox", "safari", "brave", "opera", "vivaldi"]
SUPPORTED_BROWSERS = AUTO_ORDER

# 目标域 → (设置字段, 登录关键 cookie 名或 None)
_TARGETS = {
    "bilibili": (".bilibili.com", "bilibili_sessdata", ("SESSDATA",)),
    "youtube": (".youtube.com", "youtube_cookies", ("SID", "SAPISID", "LOGIN_INFO")),
    "yuanbao": ("yuanbao.tencent.com", "wechat_yuanbao_cookie", ("hy_token", "hy_user", "tongyi_sso_ticket")),
}


def _read_jar_in_process(browser: str, domain: str, queue) -> None:
    """子进程入口：读取 cookie 并 tuple 化放回队列（超时后子进程会被强杀）"""
    try:
        import browser_cookie3
        fn = getattr(browser_cookie3, browser, None)
        if fn is None:
            raise ValueError(f"不支持的浏览器: {browser}")
        jar = fn(domain_name=domain)
        payload = [{"name": c.name, "value": c.value, "domain": c.domain or "",
                    "path": c.path or "/", "expires": int(getattr(c, "expires", 0) or 0)}
                   for c in jar]
        queue.put(("ok", payload))
    except Exception as e:
        queue.put(("err", f"{type(e).__name__}: {str(e)[:120]}"))


def _read_cookies(browser: str, domain: str, timeout: int = READ_TIMEOUT_SECONDS):
    """
    子进程读取 + 超时强杀。不能用线程：钥匙串弹窗会无限阻塞，
    ThreadPoolExecutor 的 with 退出会等待卡死线程导致接口挂起。
    """
    queue = mp.Queue()
    proc = mp.Process(target=_read_jar_in_process, args=(browser, domain, queue), daemon=True)
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(3)
        raise TimeoutError("读取超时（可能在等待钥匙串授权，请在弹窗点「允许」后重试）")
    if queue.empty():
        raise RuntimeError("子进程无返回")
    status, payload = queue.get()
    if status != "ok":
        raise RuntimeError(payload)
    return payload


def _netscape_line(cookie: Dict) -> str:
    domain = cookie["domain"]
    include_sub = domain.startswith(".")
    secure = True  # youtube 全站 https
    expiry = cookie["expires"] or 2147483647
    return f"{domain}\t{'TRUE' if include_sub else 'FALSE'}\t{cookie['path']}\t" \
           f"{'TRUE' if secure else 'FALSE'}\t{expiry}\t{cookie['name']}\t{cookie['value']}"


def _collect_from_browser(browser: str):
    """从单个浏览器读取三个目标域，返回 ({设置字段: 值}, attempts 明细)。

    先用短超时快速探测第一个域：cookie 库打不开（未安装/无权限/挂起）
    立即抛异常让 auto 模式换下一个浏览器；打开后继续读剩余两个域。
    """
    fields = {}
    attempts = []
    target_list = list(_TARGETS.items())

    # 快速探针（12s）：判断该浏览器 cookie 库是否可读
    first_label, (first_domain, first_key, first_names) = target_list[0]
    try:
        cookies = _read_cookies(browser, first_domain, timeout=12)
    except Exception as e:
        raise RuntimeError(f"{browser}: {e}") from e

    failures = 0
    for label, (domain, setting_key, key_names) in [(first_label, target_list[0][1])] + target_list[1:]:
        if label != first_label:
            try:
                cookies = _read_cookies(browser, domain, timeout=READ_TIMEOUT_SECONDS)
            except TimeoutError as e:
                attempts.append(f"{browser}/{label}: {e}")
                failures += 1
                continue
            except Exception as e:
                attempts.append(f"{browser}/{label}: {type(e).__name__}: {str(e)[:80]}")
                failures += 1
                continue
        if not cookies:
            attempts.append(f"{browser}/{label}: 无 cookie（该浏览器可能未登录此站）")
            continue
        names = {c["name"] for c in cookies}
        if label == "bilibili":
            sessdata = next((c["value"] for c in cookies if c["name"] == "SESSDATA"), "")
            if sessdata:
                fields[setting_key] = sessdata
                attempts.append(f"{browser}/{label}: 命中 SESSDATA ✅")
            else:
                attempts.append(f"{browser}/{label}: 有 {len(cookies)} 个 cookie 但无 SESSDATA（可能未登录）")
        elif label == "youtube":
            if names & set(key_names):
                lines = [_netscape_line(c) for c in cookies]
                fields[setting_key] = "# Netscape HTTP Cookie File\n" + "\n".join(lines)
                attempts.append(f"{browser}/{label}: 命中 {len(cookies)} 个 cookie（含登录态）✅")
            else:
                attempts.append(f"{browser}/{label}: 有 {len(cookies)} 个 cookie 但缺登录态（可能未登录）")
        else:  # yuanbao
            if names & set(key_names):
                header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                fields[setting_key] = header
                attempts.append(f"{browser}/{label}: 命中登录 cookie ✅")
            else:
                attempts.append(f"{browser}/{label}: 有 {len(cookies)} 个 cookie 但无登录态（可能未登录）")
    if failures == len(_TARGETS):
        raise RuntimeError("所有域均读取失败")
    return fields, attempts


def collect_target_cookies(browser: str = "") -> Dict:
    """
    一键读取：browser 为空时按 AUTO_ORDER 自动尝试，
    第一个「能打开 cookie 库」的浏览器即被采用（无论是否登录目标站）。

    Returns:
        {"browser_used": str|None, "fields": {设置字段: 值}, "attempts": [明细]}
    """
    started = time.time()
    order = [browser] if browser else AUTO_ORDER
    attempts = []
    all_fields = {}
    browser_used = None
    for name in order:
        try:
            fields, detail = _collect_from_browser(name)
        except Exception as e:
            attempts.append(f"{name}: 读取失败 — {type(e).__name__}: {str(e)[:80]}")
            continue
        attempts.extend(detail)
        browser_used = name  # 能打开 cookie 库即视为采用该浏览器
        all_fields.update(fields)
        break
    logging.info(f"浏览器 Cookie 读取完成（{browser_used or '未找到可用浏览器'}，"
                 f"耗时 {time.time() - started:.1f}s）")
    return {"browser_used": browser_used, "fields": all_fields, "attempts": attempts}
