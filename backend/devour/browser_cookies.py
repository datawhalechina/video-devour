# -*- coding: utf-8 -*-
"""
浏览器 Cookie 读取（B站 / YouTube / 腾讯元宝 / 抖音）

提供两条路径：

1. collect_target_cookies()：从浏览器本地 cookie 数据库直读（browser-cookie3）。
   - macOS：Chrome/Edge 首次会弹钥匙串授权，点「允许」即可。
   - Windows：Firefox 等非 Chromium 浏览器可用；Chrome/Edge 自 127 起改用
     App-Bound 加密（cookie 值以 v20 前缀存储，密钥绑定浏览器安装且需管理员权限
     才能解密），同时运行中的浏览器会以独占方式锁住 Cookies 数据库。
     这两个限制都无法在普通权限进程内绕过，因此 Windows 下 Chrome/Edge
     请改用第二条路径。

2. 应用内登录窗口（WebView2）：由桌面壳 desktop/shell.py 打开一个内嵌浏览器
   窗口，用户在其中登录后经 WebView2 的 CookieManager 读取 Cookie。它读的是
   应用自身的登录会话，完全绕开上述加密与文件锁。平台元信息与字段格式化逻辑
   统一放在本模块，供 shell 与后端共同复用。

本模块只读取下面 PLATFORMS 声明的目标域，不接触其他网站的 Cookie。
"""
import logging
import multiprocessing as mp
import time
from typing import Dict, List

READ_TIMEOUT_SECONDS = 240      # 单域读取上限：browser-cookie3 全表解密可能很慢（实测冷启动 >4 分钟）
READ_TOTAL_TIMEOUT_SECONDS = 300
AUTO_ORDER = ["chrome", "edge", "firefox", "safari", "brave", "opera", "vivaldi"]
SUPPORTED_BROWSERS = AUTO_ORDER

# 目标平台元信息（唯一事实来源：数据库直读与应用内登录窗口共用）
#   domains       可接受的 cookie 域列表（应用内登录时用于筛掉无关域）；
#                 含父域——元宝的登录 cookie(hy_token/hy_user)写在 .tencent.com，
#                 并非 yuanbao.tencent.com
#   query_domain  数据库直读时传给 browser-cookie3 的域（其按 host_key LIKE 过滤，
#                 故元宝用 tencent.com 以同时命中父域与子域）
#   field         写入 settings 的字段名
#   required      判定「已登录」的关键 cookie 名（命中任一即可）
#   format        value=取单个 cookie 的值；netscape=Netscape cookies.txt；header=Cookie 请求头
#   login_url     应用内登录窗口打开的地址
PLATFORMS = {
    "bilibili": {
        "label": "B站",
        "title": "登录 B站（登录成功后会自动读取并关闭窗口）",
        "login_url": "https://passport.bilibili.com/login",
        "domains": [".bilibili.com"],
        "query_domain": ".bilibili.com",
        "field": "bilibili_sessdata",
        "required": ("SESSDATA",),
        "format": "value",
        "value_key": "SESSDATA",
    },
    "youtube": {
        "label": "YouTube",
        "title": "登录 YouTube（登录成功后会自动读取并关闭窗口）",
        "login_url": "https://www.youtube.com/",
        "domains": [".youtube.com"],
        "query_domain": ".youtube.com",
        "field": "youtube_cookies",
        "required": ("SID", "SAPISID", "LOGIN_INFO", "__Secure-1PSID", "__Secure-3PSID"),
        "format": "netscape",
    },
    "yuanbao": {
        "label": "腾讯元宝",
        "title": "登录 腾讯元宝（登录成功后会自动读取并关闭窗口）",
        "login_url": "https://yuanbao.tencent.com/",
        # 元宝登录态(hy_token/hy_user)在 .tencent.com；同时保留站点自身域。
        # 浏览器访问 yuanbao.tencent.com 时也会一并携带 .tencent.com 的 cookie，
        # 因此这里收集两者，拼出的 Cookie 头与真实请求一致。
        "domains": ["yuanbao.tencent.com", "tencent.com"],
        "query_domain": "tencent.com",
        "field": "wechat_yuanbao_cookie",
        "required": ("hy_token", "hy_user", "tongyi_sso_ticket"),
        "format": "header",
    },
    "douyin": {
        "label": "抖音",
        "title": "登录 抖音（登录成功后会自动读取并关闭窗口）",
        "login_url": "https://www.douyin.com/",
        "domains": [".douyin.com"],
        "query_domain": ".douyin.com",
        "field": "douyin_cookies",
        "required": ("sessionid", "passport_csrf_token", "ttwid"),
        "format": "netscape",
    },
}

# 数据库直读用：平台 → (查询域, 设置字段, 关键 cookie 名)
_TARGETS = {k: (v["query_domain"], v["field"], v["required"]) for k, v in PLATFORMS.items()}


# --------------------------------------------------------------------------- #
# 通用 cookie 结构化（数据库直读与应用内登录窗口共用）
# --------------------------------------------------------------------------- #
def _parse_expiry(value) -> int:
    """把各种形态的过期时间（epoch 数字 / HTTP 日期串）归一到 epoch 秒，会话 cookie 记 0。"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    # pywebview 对会话 cookie 返回 "Mon, 01 Jan 0001 00:00:00 GMT"。
    # 直接用 parsedate_to_datetime 会把年份 0001 归一成 2001（视为已过期），
    # 因此先取字符串里的 4 位年份判断。
    import re
    m = re.search(r"\b(\d{4})\b", text)
    if m and int(m.group(1)) < 1970:
        return 0
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(text)
        if dt.year < 1970:
            return 0
        return int(dt.timestamp())
    except Exception:
        return 0


def to_netscape_line(cookie: Dict) -> str:
    """单个 cookie → 一行 Netscape cookies.txt 记录。"""
    domain = cookie.get("domain") or ""
    include_sub = domain.startswith(".")
    secure = cookie.get("secure", True)
    # expires 可能是 epoch 数字或 HTTP 日期串（应用内登录窗口返回后者），统一解析
    expiry = _parse_expiry(cookie.get("expires")) or 2147483647
    return (f"{domain}\t{'TRUE' if include_sub else 'FALSE'}\t{cookie.get('path') or '/'}\t"
            f"{'TRUE' if secure else 'FALSE'}\t{expiry}\t{cookie.get('name', '')}\t{cookie.get('value', '')}")


def build_fields(platform: str, cookies: List[Dict]) -> Dict[str, str]:
    """
    通用 cookie 字典列表 → settings 字段。

    仅当包含平台声明的关键 cookie 时才返回内容（否则视为未登录，返回空 dict）。
    cookie 字典需含 name/value，可选 domain/path/expires/secure。
    """
    meta = PLATFORMS.get(platform)
    if not meta or not cookies:
        return {}
    names = {c.get("name") for c in cookies}
    if not (names & set(meta["required"])):
        return {}

    fmt = meta["format"]
    if fmt == "value":
        value = next((c.get("value", "") for c in cookies if c.get("name") == meta.get("value_key")), "")
        return {meta["field"]: value} if value else {}
    if fmt == "netscape":
        lines = [to_netscape_line(c) for c in cookies]
        return {meta["field"]: "# Netscape HTTP Cookie File\n" + "\n".join(lines)}
    if fmt == "header":
        return {meta["field"]: "; ".join(f"{c.get('name', '')}={c.get('value', '')}" for c in cookies)}
    return {}


def cookie_in_domain(cookie_domain: str, accepted_domains) -> bool:
    """
    cookie 域是否属于平台可接受的域（用于筛掉登录过程中经过的第三方域 cookie）。

    accepted_domains 可以是单个域字符串或域列表。匹配规则：cookie 域与某个可接受域
    相等，或是它的子域。列表里可包含父域（如元宝需要 tencent.com），
    以覆盖登录态写在父域上的情况。
    """
    cd = (cookie_domain or "").lstrip(".").lower()
    if not cd:
        return False
    domains = [accepted_domains] if isinstance(accepted_domains, str) else list(accepted_domains)
    for d in domains:
        pd = (d or "").lstrip(".").lower()
        if pd and (cd == pd or cd.endswith("." + pd)):
            return True
    return False


# --------------------------------------------------------------------------- #
# 路径一：从浏览器本地 cookie 数据库直读
# --------------------------------------------------------------------------- #
def _friendly_read_error(browser: str, err: Exception) -> str:
    """把底层解密/占用异常翻译成用户能照做的提示。"""
    detail = f"{type(err).__name__}: {str(err)[:140]}"
    low = str(err).lower()
    if "admin" in low or "appbound" in low or "app-bound" in low:
        return (f"{detail}（该浏览器 Cookie 受 App-Bound 加密保护，仅浏览器自身或管理员可解密；"
                f"请在设置页改用「应用内登录读取」）")
    if "being used" in low or "permission" in low or "unable to read database" in low:
        return (f"{detail}（Cookie 数据库被浏览器独占占用；可关闭浏览器后重试，"
                f"或改用「应用内登录读取」）")
    if "dpapi" in low or "aes key" in low:
        return (f"{detail}（Chrome/Edge 127+ 的 App-Bound 加密无法被第三方库解密；"
                f"请改用「应用内登录读取」）")
    return detail


def _read_jar_in_process(browser: str, domain: str, queue) -> None:
    """子进程入口：读取 cookie 并 tuple 化放回队列（超时后子进程会被强杀）"""
    try:
        import browser_cookie3
        fn = getattr(browser_cookie3, browser, None)
        if fn is None:
            raise ValueError(f"不支持的浏览器: {browser}")
        jar = fn(domain_name=domain)
        payload = [{"name": c.name, "value": c.value, "domain": c.domain or "",
                    "path": c.path or "/", "expires": _parse_expiry(getattr(c, "expires", 0)),
                    "secure": bool(getattr(c, "secure", True))}
                   for c in jar]
        queue.put(("ok", payload))
    except Exception as e:
        queue.put(("err", _friendly_read_error(browser, e)))


def _collect_from_browser(browser: str):
    """
    从单个浏览器并行读取各目标域，返回 ({设置字段: 值}, attempts 明细)。

    browser-cookie3 会全表解密 cookie 库，单域冷读可能耗时数分钟，
    因此多域并行读 + 总超时兜底；全部失败时抛异常让 auto 换下一个浏览器。
    """
    fields = {}
    attempts = []

    procs, queues = {}, {}
    for label, meta in PLATFORMS.items():
        q = mp.Queue()
        p = mp.Process(target=_read_jar_in_process, args=(browser, meta["query_domain"], q), daemon=True)
        p.start()
        procs[label], queues[label] = p, q

    deadline = time.time() + READ_TOTAL_TIMEOUT_SECONDS
    results = {}
    for label in PLATFORMS:
        proc = procs[label]
        remaining = max(15, deadline - time.time())
        proc.join(remaining)
        if proc.is_alive():
            proc.terminate()
            proc.join(3)
            attempts.append(f"{browser}/{label}: 读取超时（cookie 库较大或正在等待钥匙串授权；"
                            f"弹窗请点「允许」，读取可能需要 1-3 分钟）")
            results[label] = None
            continue
        q = queues[label]
        if q.empty():
            attempts.append(f"{browser}/{label}: 子进程无返回")
            results[label] = None
            continue
        status, payload = q.get()
        if status != "ok":
            attempts.append(f"{browser}/{label}: {payload}")
            results[label] = None
            continue
        results[label] = payload
        attempts.append(f"{browser}/{label}: 读取到 {len(payload)} 个 cookie")

    failures = 0
    for label, meta in PLATFORMS.items():
        cookies = results.get(label)
        if cookies is None:
            failures += 1
            continue
        if not cookies:
            attempts.append(f"{browser}/{label}: 无 cookie（该浏览器可能未登录此站）")
            continue
        got = build_fields(label, cookies)
        if got:
            fields.update(got)
            attempts.append(f"{browser}/{label}: 命中 {meta['label']} 登录态 ✅")
        else:
            attempts.append(f"{browser}/{label}: 有 {len(cookies)} 个 cookie 但缺登录态"
                            f"（未在浏览器登录 {meta['label']}；登录后重新读取即可）")
    if failures == len(PLATFORMS):
        # 该浏览器 cookie 库整体不可读：返回 ok=False 让上层换下一个浏览器，
        # 同时保留逐域明细（含 App-Bound / 文件锁等针对性提示）供展示。
        return fields, attempts, False
    return fields, attempts, True


def collect_target_cookies(browser: str = "") -> Dict:
    """
    一键读取：browser 为空时按 AUTO_ORDER 自动尝试，
    第一个「能打开 cookie 库」的浏览器即被采用。

    Windows 下 Chrome/Edge 因 App-Bound 加密通常不可用，此时请改用桌面壳的
    「应用内登录读取」（见桌面设置页）。

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
            fields, detail, ok = _collect_from_browser(name)
        except Exception as e:
            attempts.append(f"{name}: 读取失败 — {type(e).__name__}: {str(e)[:120]}")
            continue
        attempts.extend(detail)
        if not ok:
            # 该浏览器 cookie 库整体不可读（如 Windows 下 Chrome/Edge 的
            # App-Bound 加密或文件锁），换下一个
            continue
        browser_used = name  # 能打开 cookie 库即视为采用该浏览器
        all_fields.update(fields)
        break
    logging.info(f"浏览器 Cookie 读取完成（{browser_used or '未找到可用浏览器'}，"
                 f"耗时 {time.time() - started:.1f}s）")
    return {"browser_used": browser_used, "fields": all_fields, "attempts": attempts}
