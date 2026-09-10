# -*- coding: utf-8 -*-
"""
在线视频链接下载器（Bilibili / YouTube / 微信视频号等）

移植自 bilibili-video-download 与 youtube-downloader 两个工具的核心思路：
- 先取元数据（标题/封面/时长/作者）供预览确认，再执行下载
- yt-dlp 统一支持 B 站与 YouTube（含搜索），ffmpeg 负责合成 mp4
- 微信视频号不支持 yt-dlp：优先走分享链接解析服务换直链，失败时引导本地捕获
- 合理默认值：单个视频（不展开合集/列表）、优先最高 720p H.264、mp4 输出

说明：请仅对拥有版权或已获授权的内容进行下载处理。
"""
import logging
from backend.runtime import paths as _rt_paths
import re
from pathlib import Path
from typing import Dict, List, Optional


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# 视频号分享多来自手机端，用移动端 UA 提高分享页可达性
_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49"
)

# 公共解析服务（ltaoo/wx_channels_download 作者提供，第三方服务非微信官方）
DEFAULT_WECHAT_RESOLVER = "https://sph.litao.workers.dev"

_URL_IN_TEXT_RE = re.compile(r"https?://[^\s\"'<>【】（）()，。；]+", re.IGNORECASE)
_WECHAT_URL_RE = re.compile(r"https?://weixin\.qq\.com/sph/[A-Za-z0-9_\-]+", re.IGNORECASE)


def extract_share_url(text: str) -> str:
    """
    从用户粘贴的分享文本中提取视频链接。

    微信/B站 App 的分享内容通常是一段文案+链接，先抽出纯链接再交给平台识别；
    未匹配到链接时原样返回（视为用户直接粘贴了 URL）。
    """
    text = (text or "").strip()
    wechat = _WECHAT_URL_RE.search(text)
    if wechat:
        return wechat.group(0)
    generic = _URL_IN_TEXT_RE.search(text)
    if generic:
        return generic.group(0).rstrip(".,;，；")
    return text


def _get_ydl(**extra):
    from yt_dlp import YoutubeDL
    from backend.runtime import paths as _rt_paths

    referer = extra.pop("referer", "https://www.bilibili.com/")
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,   # 单视频优先，不展开合集
        "socket_timeout": 20,
        "retries": 3,
        # yt-dlp 下载高画质时需合并音视频轨，必须知道 ffmpeg 位置；
        # 不设置则只查系统 PATH，客户端捆绑的 ffmpeg 会被忽略
        # （表现为 "ffmpeg is not installed. Aborting due to --abort-on-error"）。
        "ffmpeg_location": _rt_paths.ffmpeg_path(),
        # 浏览器指纹：B站等平台对无 UA/Referer 的请求会返回 412
        "http_headers": {
            "User-Agent": _BROWSER_UA,
            "Referer": referer,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    }
    # 注：不启用 yt-dlp 的 impersonation（TLS 指纹伪装）——与 B站提取器
    # 存在兼容问题（No video formats），412 防护依赖指纹 cookie + 退避重试
    options.update(extra)
    return YoutubeDL(options)


def detect_platform(url: str) -> str:
    """根据链接判断来源平台：youtube | bilibili | wechat | other"""
    url = (url or "").lower()
    if re.search(r"(youtube\.com|youtu\.be)", url):
        return "youtube"
    if re.search(r"(bilibili\.com|b23\.tv)", url):
        return "bilibili"
    if re.search(r"weixin\.qq\.com/sph/", url):
        return "wechat"
    return "other"


def _extract_video_id(url: str, platform: str) -> Optional[str]:
    """从链接中提取用于前端嵌入播放器的 ID"""
    if platform == "youtube":
        m = re.search(
            r"(?:youtu\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{6,})", url
        )
        return m.group(1) if m else None
    if platform == "bilibili":
        m = re.search(r"(?:/video/|BV)([A-Za-z0-9]{10,})", url) or re.search(
            r"(BV[A-Za-z0-9]{8,})", url
        )
        return m.group(1) if m else None
    if platform == "wechat":
        m = re.search(r"weixin\.qq\.com/sph/([A-Za-z0-9_\-]+)", url, re.IGNORECASE)
        return m.group(1) if m else None
    return None


def _simplify_info(info: Dict, platform: str) -> Dict:
    """把 yt-dlp 的元数据精简为前端预览所需字段"""
    webpage_url = info.get("webpage_url") or info.get("original_url") or ""
    duration = info.get("duration")
    return {
        "id": info.get("id"),
        "title": info.get("title") or "未知标题",
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id") or "",
        "duration": int(duration) if duration else None,
        "thumbnail": info.get("thumbnail") or "",
        "platform": platform,
        "webpage_url": webpage_url,
        "video_id": _extract_video_id(webpage_url, platform) or info.get("id"),
        "description": (info.get("description") or "")[:200],
    }


def probe_video_info(url: str) -> Dict:
    """
    获取视频元数据（不下载），用于前端预览确认。

    Raises:
        ValueError: 链接不受支持或视频不存在
    """
    platform = detect_platform(url)
    if platform == "wechat":
        # 视频号不支持 yt-dlp：分享页兜底信息 + 直连链路尽力补全真实元数据
        info = _wechat_share_info(url)
        cookie = _wechat_setting("wechat_yuanbao_cookie", "YUANBAO_COOKIE")
        if cookie:
            try:
                eid, token = _wechat_parse_share(url, cookie)
                meta = _feed_meta(_wechat_feed_info(eid, token))
                info.update({k: v for k, v in meta.items()
                             if k in ("title", "uploader", "thumbnail") and v})
            except Exception as e:
                logging.warning(f"视频号元数据直连解析失败（不影响下载重试）: {e}")
        return info
    if platform == "bilibili":
        # B站视频页接口对无指纹请求返回 412，优先走官方 view API
        bvid = _extract_video_id(url, "bilibili")
        if bvid:
            try:
                return _bilibili_view_info(bvid)
            except Exception as e:
                logging.warning(f"B站 view API 获取失败，回退 yt-dlp: {e}")
    try:
        with _get_ydl(referer=_platform_referer(platform)) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        if platform == "youtube" and ("Sign in" in str(e) or "not a bot" in str(e)):
            # YouTube bot 检查：按 youtube-downloader 工具的实践回退 oEmbed
            logging.warning("YouTube bot 检查拦截，回退 oEmbed 获取元数据")
            return _youtube_oembed_info(url)
        raise
    if not info:
        raise ValueError(f"无法获取视频信息: {url}")
    if "entries" in info:  # 命中了合集/列表，取第一个
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise ValueError("该链接下没有可用的视频")
        info = entries[0]
    return _simplify_info(info, platform)


def _youtube_oembed_info(url: str) -> Dict:
    """
    YouTube oEmbed 兜底：bot 检查拦截时仍可取到标题/作者/封面（无时长）。
    """
    import requests

    resp = requests.get(
        "https://www.youtube.com/oembed",
        params={"url": url, "format": "json"},
        timeout=10,
        headers={"User-Agent": _BROWSER_UA},
    )
    if resp.status_code != 200:
        raise ValueError(f"无法获取视频信息（oEmbed {resp.status_code}）")
    data = resp.json()
    return {
        "id": _extract_video_id(url, "youtube"),
        "title": data.get("title") or "未知标题",
        "uploader": data.get("author_name") or "",
        "duration": None,
        "thumbnail": data.get("thumbnail_url") or "",
        "platform": "youtube",
        "webpage_url": url,
        "video_id": _extract_video_id(url, "youtube"),
        "description": "（YouTube bot 检查限制，仅获取到基本信息；下载需配置 cookies）",
    }


def _platform_referer(platform: str) -> str:
    return "https://www.youtube.com/" if platform == "youtube" else "https://www.bilibili.com/"


# ---------------------------------------------------------------------------
# 微信视频号（weixin.qq.com/sph/...）
# 机制参考 joeseesun/qiaomu-wx-video 与 ltaoo/wx_channels_download 的 sph worker：
# 视频号没有公开直链，解析链路为——
# 1) 直连（优先，无第三方）：腾讯元宝 get_parse_result（需元宝网页 Cookie）
#    换取 exportId + token → 视频号 finder-preview get_feed_info 取媒体列表
#    （url+urlToken，decodeKey 指示前 N 字节经 ISAAC64 加密）→ 下载后本地解密
# 2) 自建解析服务：WECHAT_RESOLVER_URL 指向 sph worker 等服务（支持 Bearer token）
# 3) 本地捕获（引导用户手动）：wx_channels_download 桌面端方案，失败时提示
# ---------------------------------------------------------------------------

_WECHAT_FAIL_HINT = (
    "视频号解析失败。当前链路：①直连腾讯元宝解析（需在设置页填写元宝 Cookie，"
    "登录 yuanbao.tencent.com 后从浏览器开发者工具复制）；②自建解析服务"
    "（WECHAT_RESOLVER_URL）；③本地捕获工具 wx_channels_download 下载后上传。"
)

# 元宝解析接口的浏览器指纹头（来自 sph worker，缺失会 401）
_YUANBAO_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
_YUANBAO_PARSE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://yuanbao.tencent.com",
    "referer": "https://yuanbao.tencent.com/chat/naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1",
    "user-agent": _BROWSER_UA,
    "t-userid": "b9575f6b0a8c4a55a08096904a5ef20a",
    "x-agentid": "naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1",
    "x-commit-tag": "72282a0d",
    "x-device-id": "1921b001708100d7fa31002b9646bd0cc15a3e2e1f",
    "x-id": "b9575f6b0a8c4a55a08096904a5ef20a",
    "x-language": "zh-CN",
    "x-os_version": "Mac OS(10.15.7)-Blink",
    "x-platform": "mac",
    "x-requested-with": "XMLHttpRequest",
    "x-source": "web",
    "x-webversion": "2.69.0",
}

_FEED_INFO_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
_FEED_INFO_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://channels.weixin.qq.com",
    "User-Agent": _BROWSER_UA,
}


class _WeChatError(Exception):
    """视频号解析链路中可向用户展示的错误"""


def _plain_text(value) -> str:
    """HTML 片段转纯文本（微信 errMsg 常带标签与实体）"""
    import html as _html
    text = str(value or "")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]*>", "", text)
    return _html.unescape(text).strip()


def _wechat_setting(key: str, env_name: str = "") -> str:
    """视频号相关配置：settings.json 优先，环境变量兜底"""
    import os
    value = ""
    try:
        from backend.algorithm.settings_store import load_settings
        value = (load_settings().get(key) or "").strip()
    except Exception:
        pass
    if not value and env_name:
        value = (os.getenv(env_name) or "").strip()
    return value


def _wechat_parse_share(share_url: str, cookie: str):
    """元宝解析分享链接 → (exportId, token)"""
    import requests

    headers = dict(_YUANBAO_PARSE_HEADERS)
    if cookie:
        headers["cookie"] = cookie
    resp = requests.post(
        _YUANBAO_PARSE_URL,
        json={"type": "video_channel_url", "url": share_url, "scene": 1},
        headers=headers, timeout=30,
    )
    if resp.status_code in (401, 403):
        raise _WeChatError("元宝解析接口返回 401：Cookie 缺失或已过期，请在设置页更新")
    if not resp.ok:
        raise _WeChatError(f"元宝解析接口异常: HTTP {resp.status_code}")
    data = (resp.json() or {}).get("data") or {}
    export_id = data.get("wx_export_id") or ""
    token, eid = "", export_id
    playable = data.get("playable_url") or ""
    if playable:
        from urllib.parse import urlsplit, parse_qs
        query = parse_qs(urlsplit(playable).query)
        token = (query.get("token") or [""])[0]
        eid = (query.get("eid") or [export_id])[0]
    if not eid:
        raise _WeChatError("元宝解析未返回 export id（分享链接可能已失效）")
    return eid, token


def _wechat_feed_info(eid: str, token: str) -> Dict:
    """调用视频号 finder-preview feed 接口（无需登录，但需有效 eid+token）"""
    import random
    import time
    from urllib.parse import quote
    import requests

    rid = f"{int(time.time()):x}-" + "".join(random.choice("0123456789abcdef") for _ in range(8))
    api = (f"{_FEED_INFO_URL}?_rid={rid}"
           "&_pageUrl=https%3A%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed")
    referer = ("https://channels.weixin.qq.com/finder-preview/pages/feed"
               f"?entry_card_type=48&comment_scene=39&appid=0"
               f"&token={quote(token)}&entry_scene=0&eid={quote(eid)}")
    resp = requests.post(
        api,
        json={"baseReq": {"generalToken": token}, "exportId": eid},
        headers={**_FEED_INFO_HEADERS, "Referer": referer},
        timeout=30,
    )
    if not resp.ok:
        raise _WeChatError(f"视频号接口异常: HTTP {resp.status_code}")
    result = resp.json()
    if result.get("errCode"):
        raise _WeChatError(f"视频号接口错误: {_plain_text(result.get('errMsg'))}")
    detail = (result.get("data") or {}).get("errMsg") or {}
    title = _plain_text(detail.get("title"))
    content = _plain_text(detail.get("content"))
    if detail.get("type") or title or content:
        raise _WeChatError(content and f"{title}: {content}" or title or "内容无法播放（可能为回放或已下架）")
    return result


def _walk_collect_video_media(node, found=None):
    """
    递归在 feed JSON 中收集视频媒体项。

    兼容两种结构：老版 mediaList（mediaUrl + decodeKey/fileType）与
    finder-preview 新版（videoUrl / h264VideoInfo / h265VideoInfo，可能无 decodeKey）。
    """
    if found is None:
        found = []
    if isinstance(node, dict):
        url = None
        for key in ("mediaUrl", "videoUrl", "url"):
            value = node.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                url = value
                break
        if url and ("decodeKey" in node or "fileType" in node or "mediaUrl" in node
                    or "videoUrl" in node or "spec" in node):
            token = node.get("urlToken") or ""
            if token and token not in url:
                url = url + token
            decode_key = node.get("decodeKey")
            try:
                decode_key = int(str(decode_key)) if decode_key not in (None, "") else None
            except (TypeError, ValueError):
                decode_key = None
            found.append({"url": url, "decode_key": decode_key})
        for value in node.values():
            _walk_collect_video_media(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_collect_video_media(value, found)
    return found


def _feed_meta(feed: Dict) -> Dict:
    """从 feed JSON 中提取标题/作者/封面（兼容 mediaList 与 authorInfo 两种结构）"""
    meta = {}

    def _walk(node):
        if isinstance(node, dict):
            if "description" in node:
                meta.setdefault("title", _plain_text(node.get("description"))[:120])
                for key in ("nickname", "objectNickname", "userName"):
                    if node.get(key):
                        meta.setdefault("uploader", str(node[key]))
                        break
                for key in ("coverUrl", "coverImgUrl", "thumbUrl"):
                    if node.get(key):
                        meta.setdefault("thumbnail", str(node[key]))
                        break
            if node.get("nickname") and "headImgUrl" in node:
                # finder-preview 新版：authorInfo.nickname
                meta.setdefault("uploader", str(node["nickname"]))
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(feed)
    return {k: v for k, v in meta.items() if v}


def _wechat_resolve_via_service(share_url: str, target_dir: Path, vid: str):
    """外部解析服务路径：返回 (sources, last_status)，sources 元素为 (kind, payload)"""
    import requests

    sources = []
    base = (_wechat_setting("wechat_resolver_url", "WECHAT_RESOLVER_URL")
            or DEFAULT_WECHAT_RESOLVER).rstrip("/")
    token = _wechat_setting("wechat_resolver_token", "WECHAT_RESOLVER_TOKEN")
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    attempts = [
        ("GET", f"{base}/?url={share_url}", None),
        ("POST", base, {"url": share_url}),
    ]
    last_status = None
    for method, req_url, data in attempts:
        try:
            resp = requests.request(
                method, req_url, data=data, timeout=30,
                headers={
                    "User-Agent": _BROWSER_UA,
                    "Referer": "https://weixin.qq.com/",
                    "Accept": "*/*",
                    **auth,
                },
                allow_redirects=True,
            )
        except Exception as e:
            logging.warning(f"解析服务请求失败({method} {req_url}): {e}")
            continue
        if resp.status_code != 200:
            last_status = resp.status_code
            logging.warning(f"解析服务返回 {resp.status_code}: {req_url}")
            continue
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if ctype.startswith(("video/", "audio/", "application/octet-stream")):
            # 解析服务直接回流媒体内容：落盘后按本地文件处理
            tmp = target_dir / f"{vid}_resolve.tmp"
            with open(tmp, "wb") as f:
                f.write(resp.content)
            sources.append(("local", str(tmp)))
            break
        # JSON 或 HTML：先按 feed 结构提取（兼容 sph worker），再退回直链正则
        payload = _safe_json(resp)
        feed_media = _walk_collect_video_media(payload or {})
        if feed_media:
            sources = [("m3u8" if item["url"].lower().split("?")[0].endswith(".m3u8")
                        else "url", item["url"]) for item in feed_media]
        else:
            media = _find_media_urls(payload)
            if not media:
                media = re.findall(
                    r"https?://[^\"'\\\s<>]+\.(?:mp4|m3u8)[^\"'\\\s<>]*",
                    resp.text or "", re.IGNORECASE,
                )
            sources = [("m3u8" if u.lower().split("?")[0].endswith(".m3u8") else "url", u)
                       for u in dict.fromkeys(media)]
        if sources:
            break
    return sources, last_status


def _wechat_share_info(url: str) -> Dict:
    """视频号元数据：先解析分享页 HTML 尽力取标题，取不到就用占位信息。"""
    import requests

    vid = _extract_video_id(url, "wechat") or ""
    info = {
        "id": vid,
        "title": f"微信视频号 {vid}",
        "uploader": "",
        "duration": None,
        "thumbnail": "",
        "platform": "wechat",
        "webpage_url": url,
        "video_id": vid,
        "description": "视频号内容不支持网页内嵌预览；可直接“一键下载处理”，"
                       "解析失败时请用本地工具下载后在“上传视频”页上传。",
    }
    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": _MOBILE_UA, "Referer": "https://weixin.qq.com/",
        })
        if resp.ok:
            m = (re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', resp.text, re.IGNORECASE)
                 or re.search(r"<title[^>]*>([^<]+)<", resp.text))
            title = m.group(1).strip() if m else ""
            # 分享页兜底标题常为“视频号”三个字，过滤掉避免误导
            if title and title not in ("视频号", "微信视频号"):
                info["title"] = title
    except Exception as e:
        logging.warning(f"视频号分享页标题获取失败: {e}")
    return info


def _find_media_urls(obj, found=None):
    """递归在解析服务返回的 JSON 中收集疑似媒体直链"""
    if found is None:
        found = []
    if isinstance(obj, str):
        if re.match(r"https?://", obj) and re.search(r"\.(mp4|m3u8)(\?|$)", obj, re.IGNORECASE):
            found.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _find_media_urls(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _find_media_urls(v, found)
    return found


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def _validate_video_file(path: Path) -> bool:
    """ffprobe 验证存在视频流；ffprobe 不可用时退化为容器签名+大小弱验证"""
    import subprocess

    if not path.exists() or path.stat().st_size < 10240:
        return False
    try:
        proc = subprocess.run(
            [_rt_paths.ffprobe_path(), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
            capture_output=True, timeout=30,
        )
        if proc.returncode == 0:
            return bool(proc.stdout.strip())
    except FileNotFoundError:
        # 无 ffprobe：mp4 容器偏移 4 字节应为 'ftyp'
        with open(path, "rb") as f:
            head = f.read(8)
        return len(head) >= 8 and head[4:8] == b"ftyp"
    except Exception as e:
        logging.warning(f"ffprobe 校验异常: {e}")
    return False


# 视频号媒体流加密：仅前 N 字节经 ISAAC64 密钥流 XOR（WechatSphDecrypt 算法）
_WECHAT_ENC_LIMIT = 131072
_U64 = (1 << 64) - 1


def _isaac64_mix(a, b, c, d, e, f, g, h):
    a = (a - e) & _U64
    f ^= h >> 9
    h = (h + a) & _U64
    b = (b - f) & _U64
    g ^= (a << 9) & _U64
    a = (a + b) & _U64
    c = (c - g) & _U64
    h ^= b >> 23
    b = (b + c) & _U64
    d = (d - h) & _U64
    a ^= (c << 15) & _U64
    c = (c + d) & _U64
    e = (e - a) & _U64
    b ^= d >> 14
    d = (d + e) & _U64
    f = (f - b) & _U64
    c ^= (e << 20) & _U64
    e = (e + f) & _U64
    g = (g - c) & _U64
    d ^= f >> 17
    f = (f + g) & _U64
    h = (h - d) & _U64
    e ^= (g << 14) & _U64
    g = (g + h) & _U64
    return a, b, c, d, e, f, g, h


def _isaac64_keystream(key: int):
    """按 WechatSphDecrypt 的 ISAAC64 实现生成随机数流（每个数 XOR 8 字节，大端）"""
    golden = 0x9E3779B97F4A7C13
    seed = [0] * 256
    seed[0] = key & _U64
    mm = [0] * 256
    a = b = c = d = e = f = g = h = golden
    for _ in range(4):
        a, b, c, d, e, f, g, h = _isaac64_mix(a, b, c, d, e, f, g, h)
    for i in range(0, 256, 8):
        a = (a + seed[i]) & _U64
        b = (b + seed[i + 1]) & _U64
        c = (c + seed[i + 2]) & _U64
        d = (d + seed[i + 3]) & _U64
        e = (e + seed[i + 4]) & _U64
        f = (f + seed[i + 5]) & _U64
        g = (g + seed[i + 6]) & _U64
        h = (h + seed[i + 7]) & _U64
        a, b, c, d, e, f, g, h = _isaac64_mix(a, b, c, d, e, f, g, h)
        mm[i:i + 8] = [a, b, c, d, e, f, g, h]
    for i in range(0, 256, 8):
        a = (a + mm[i]) & _U64
        b = (b + mm[i + 1]) & _U64
        c = (c + mm[i + 2]) & _U64
        d = (d + mm[i + 3]) & _U64
        e = (e + mm[i + 4]) & _U64
        f = (f + mm[i + 5]) & _U64
        g = (g + mm[i + 6]) & _U64
        h = (h + mm[i + 7]) & _U64
        a, b, c, d, e, f, g, h = _isaac64_mix(a, b, c, d, e, f, g, h)
        mm[i:i + 8] = [a, b, c, d, e, f, g, h]

    state = {"aa": 0, "bb": 0, "cc": 0}

    def _refill():
        # 对齐 Go 实现：CC/BB 先自增，再重排 MM 并重填 seed
        state["cc"] = (state["cc"] + 1) & _U64
        state["bb"] = (state["bb"] + state["cc"]) & _U64
        aa, bb = state["aa"], state["bb"]
        for i in range(256):
            if i % 4 == 0:
                aa = ~(aa ^ ((aa << 21) & _U64)) & _U64
            elif i % 4 == 1:
                aa = (aa ^ (aa >> 5)) & _U64
            elif i % 4 == 2:
                aa = (aa ^ ((aa << 12) & _U64)) & _U64
            else:
                aa = (aa ^ (aa >> 33)) & _U64
            aa = (aa + mm[(i + 128) % 256]) & _U64
            x = mm[i]
            y = (mm[(x >> 3) % 256] + aa + bb) & _U64
            mm[i] = y
            bb = (mm[(y >> 11) % 256] + x) & _U64
            seed[i] = bb
        state["aa"], state["bb"] = aa, bb

    _refill()  # rand64Init 末尾的首次 isAAC64
    rand_cnt = 255
    while True:
        result = seed[rand_cnt]
        if rand_cnt == 0:
            _refill()
            rand_cnt = 255
        else:
            rand_cnt -= 1
        yield result


def _decrypt_wechat_media_head(path: Path, key: int, enc_len: int = _WECHAT_ENC_LIMIT):
    """就地解密媒体文件前 enc_len 字节（ISAAC64 密钥流 XOR，8 字节对齐）"""
    size = path.stat().st_size
    span = min(size, enc_len) // 8 * 8
    if span <= 0:
        return
    with open(path, "r+b") as f:
        head = f.read(span)
        out = bytearray(span)
        i = 0
        for rand_number in _isaac64_keystream(key):
            if i >= span:
                break
            stream = rand_number.to_bytes(8, "big")
            for j in range(8):
                if i + j >= span:
                    break
                out[i + j] = head[i + j] ^ stream[j]
            i += 8
        f.seek(0)
        f.write(bytes(out))


def _download_wechat_video(url: str, target_dir: str, progress_hook=None) -> Dict:
    """视频号下载：直连解析优先 → 流式下载（按需解密）→ ffprobe 验证 → {vid}.mp4"""
    import subprocess
    import requests

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    vid = _extract_video_id(url, "wechat") or "wechat_video"
    share_url = extract_share_url(url)

    def _hook(d):
        if progress_hook:
            try:
                progress_hook(d)
            except Exception:
                pass

    notes = []       # 各链路的失败原因，最终汇总进报错信息
    candidates = []  # [{"url", "decode_key"}]
    local_file = None
    meta = None

    # 1) 直连链路：元宝解析 + feed 接口（无第三方）
    cookie = _wechat_setting("wechat_yuanbao_cookie", "YUANBAO_COOKIE")
    if cookie:
        try:
            eid, token = _wechat_parse_share(share_url, cookie)
            feed = _wechat_feed_info(eid, token)
            meta = _feed_meta(feed)
            # feedInfo 顶层 videoUrl 与 h264VideoInfo 重复，按 URL 去重保持顺序
            seen = set()
            candidates = []
            for item in _walk_collect_video_media(feed):
                if item["url"] not in seen:
                    seen.add(item["url"])
                    candidates.append(item)
            if not candidates:
                notes.append("直连解析成功但未在返回中找到视频流")
        except _WeChatError as e:
            notes.append(str(e))
        except Exception as e:
            notes.append(f"直连解析异常: {e}")
    else:
        notes.append("未配置元宝 Cookie（设置页「微信视频号」或环境变量 YUANBAO_COOKIE）")

    # 2) 外部解析服务兜底（sph worker 等，支持 Bearer token）
    try:
        sources, resolver_status = _wechat_resolve_via_service(share_url, target, vid)
        for kind, payload in sources:
            if kind == "local":
                local_file = payload
            else:
                candidates.append({"url": payload, "decode_key": None})
        if not sources and resolver_status:
            notes.append(f"解析服务返回 {resolver_status}")
    except Exception as e:
        notes.append(f"解析服务异常: {e}")

    if not candidates and not local_file:
        raise ValueError(_WECHAT_FAIL_HINT + "（" + "；".join(notes[-2:]) + "）")

    final_path = target / f"{vid}.mp4"
    errors = []

    # 解析服务直接回流的本地内容
    if local_file:
        try:
            Path(local_file).replace(final_path)
            if _validate_video_file(final_path):
                return {"file_path": str(final_path), "info": _wechat_share_info(share_url)}
            errors.append("解析服务回流内容校验失败")
        finally:
            if Path(local_file).exists():
                Path(local_file).unlink(missing_ok=True)

    for cand in candidates:
        media_url, decode_key = cand["url"], cand["decode_key"]
        try:
            if media_url.lower().split("?")[0].endswith(".m3u8"):
                # 未加密 HLS 由 ffmpeg 直接合成；加密流会失败进入下一候选
                proc = subprocess.run(
                    [_rt_paths.ffmpeg_path(), "-y", "-i", media_url, "-c", "copy",
                     "-bsf:a", "aac_adtstoasc", str(final_path)],
                    capture_output=True, timeout=600,
                )
                if proc.returncode != 0:
                    raise RuntimeError("m3u8 下载失败（可能为加密流）")
            else:
                with requests.get(
                    media_url, stream=True, timeout=(10, 60),
                    headers={"User-Agent": _MOBILE_UA, "Referer": "https://weixin.qq.com/"},
                ) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("Content-Length") or 0)
                    done = 0
                    _hook({"status": "downloading", "downloaded_bytes": 0,
                           "total_bytes": total or None})
                    with open(final_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1 << 20):
                            if chunk:
                                f.write(chunk)
                                done += len(chunk)
                                _hook({"status": "downloading",
                                       "downloaded_bytes": done,
                                       "total_bytes": total or None})
            _hook({"status": "finished"})
            # 常规校验失败且带 decodeKey 时，尝试解密前 128KB 后重新校验
            if not _validate_video_file(final_path) and decode_key:
                _decrypt_wechat_media_head(final_path, decode_key)
            if _validate_video_file(final_path):
                logging.info(f"视频号下载完成: {final_path}")
                info = _wechat_share_info(share_url)
                if meta:
                    info.update({k: v for k, v in meta.items()
                                 if k in ("title", "uploader", "thumbnail") and v})
                return {"file_path": str(final_path), "info": info}
            errors.append(f"候选源校验失败: {media_url[:80]}")
        except Exception as e:
            errors.append(f"{str(e)[:120]} ({media_url[:60]})")
        finally:
            if final_path.exists() and not _validate_video_file(final_path):
                final_path.unlink(missing_ok=True)
    detail = f"（{'；'.join(errors[-2:])}）" if errors else ""
    raise ValueError(_WECHAT_FAIL_HINT + detail)


def _youtube_thumbnail_fallback(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def _bilibili_session():
    """
    带浏览器指纹的 B站会话：先访问主站获取 buvid3 cookie，再调用指纹
    接口补充 buvid3/buvid4（b_3/b_4）——B站 412 风控对这些指纹
    cookie 的完整性很敏感，只有主站 cookie 时容易被拦。
    """
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": _BROWSER_UA,
        "Referer": "https://www.bilibili.com/",
    })
    try:
        session.get("https://www.bilibili.com", timeout=10)
    except Exception as e:
        logging.warning(f"访问B站主站获取 cookie 失败: {e}")
    try:
        resp = session.get(
            "https://api.bilibili.com/x/frontend/finger/spi", timeout=10
        )
        payload = resp.json()
        if payload.get("code") == 0:
            data = payload.get("data") or {}
            b3, b4 = data.get("b_3"), data.get("b_4")
            if b3:
                session.cookies.set("buvid3", b3, domain=".bilibili.com")
            if b4:
                session.cookies.set("buvid4", b4, domain=".bilibili.com")
    except Exception as e:
        logging.warning(f"获取B站指纹 cookie 失败: {e}")
    return session


def _parse_duration_str(value) -> Optional[int]:
    """把 'MM:SS' / 'HH:MM:SS' / 秒数 统一为秒"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    parts = str(value).split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    seconds = 0
    for n in nums:
        seconds = seconds * 60 + n
    return seconds


def _bilibili_cookiefile() -> Optional[str]:
    """
    获取B站 cookie 并写成 Netscape 格式文件供 yt-dlp 使用。

    B站下载/搜索接口对无 buvid3 指纹的请求会间歇性返回 412，
    带上主站下发的 cookie 可显著提高成功率。
    """
    import os
    import tempfile

    try:
        session = _bilibili_session()
        if not session.cookies:
            return None
        fd, path = tempfile.mkstemp(prefix="bilibili_cookies_", suffix=".txt")
        with os.fdopen(fd, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in session.cookies:
                domain = c.domain or ".bilibili.com"
                f.write(f"{domain}\tTRUE\t/\tFALSE\t0\t{c.name}\t{c.value}\n")
        return path
    except Exception as e:
        logging.warning(f"获取B站 cookie 失败: {e}")
        return None


def _bilibili_view_info(bvid: str) -> Dict:
    """通过 B站官方 view API 获取视频元数据"""
    session = _bilibili_session()
    resp = session.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid}, timeout=10,
    )
    payload = resp.json()
    if payload.get("code") != 0:
        raise ValueError(f"B站视频信息获取失败: {payload.get('message')}")
    data = payload["data"]
    return {
        "id": data.get("bvid"),
        "title": data.get("title") or "未知标题",
        "uploader": (data.get("owner") or {}).get("name", ""),
        "duration": data.get("duration"),
        "thumbnail": data.get("pic") or "",
        "platform": "bilibili",
        "webpage_url": f"https://www.bilibili.com/video/{data.get('bvid')}",
        "video_id": data.get("bvid"),
        "description": (data.get("desc") or "")[:200],
    }


def search_videos(query: str, platform: str = "bilibili", max_results: int = 8) -> List[Dict]:
    """
    按关键词搜索视频（B站/YouTube），返回预览卡片所需信息列表。

    Args:
        query: 搜索关键词
        platform: bilibili | youtube
        max_results: 返回条数
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("搜索关键词不能为空")
    if platform not in ("bilibili", "youtube"):
        raise ValueError("platform 仅支持 bilibili 或 youtube（微信视频号暂不支持搜索，请直接粘贴分享链接）")

    if platform == "bilibili":
        return _bilibili_search(query, max_results)
    return _youtube_search(query, max_results)


def _bilibili_search(query: str, max_results: int) -> List[Dict]:
    """
    B站搜索：直接调用官方 web 搜索接口（带 buvid3 cookie）。
    yt-dlp 的 bilisearch 对无浏览器指纹的请求会收到 412，故单独实现。
    """
    session = _bilibili_session()
    resp = session.get(
        "https://api.bilibili.com/x/web-interface/search/type",
        params={"search_type": "video", "keyword": query, "page": 1},
        timeout=10,
    )
    payload = resp.json()
    if payload.get("code") != 0:
        raise ValueError(f"B站搜索失败: {payload.get('message')}")

    results = []
    for v in payload.get("data", {}).get("result") or []:
        if v.get("type") != "video":
            continue
        bvid = v.get("bvid")
        if not bvid:
            continue
        title = re.sub(r"<[^>]+>", "", v.get("title") or "")
        pic = v.get("pic") or ""
        if pic.startswith("//"):
            pic = "https:" + pic
        results.append({
            "id": bvid,
            "title": title,
            "uploader": v.get("author") or "",
            "duration": _parse_duration_str(v.get("duration")),
            "thumbnail": pic,
            "platform": "bilibili",
            "webpage_url": f"https://www.bilibili.com/video/{bvid}",
            "video_id": bvid,
            "description": "",
        })
        if len(results) >= max_results:
            break
    return results


def _youtube_search(query: str, max_results: int) -> List[Dict]:
    """YouTube 搜索：yt-dlp ytsearch（flat 模式，只取列表信息）"""
    results = []
    with _get_ydl(referer="https://www.youtube.com/", extract_flat=True) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    for entry in info.get("entries") or []:
        if not entry:
            continue
        url = entry.get("url") or entry.get("webpage_url") or ""
        if url and not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={entry['id']}"
        item = _simplify_info({**entry, "webpage_url": url}, "youtube")
        item["video_id"] = _extract_video_id(url, "youtube") or entry.get("id")
        if not item["thumbnail"] and item["video_id"]:
            item["thumbnail"] = _youtube_thumbnail_fallback(item["video_id"])
        results.append(item)
    return results


def _bgutil_script_path() -> Optional[str]:
    """探测 bgutil PO Token 生成脚本（YouTube 下载增强，可选安装）"""
    import os
    env = os.getenv("BGUTIL_POT_SCRIPT")
    if env and os.path.exists(env):
        return env
    default = os.path.expanduser(
        "~/bgutil-ytdlp-pot-provider/server/build/generate_once.js")
    if os.path.exists(default):
        return default
    return None


def _youtube_js_runtime() -> Optional[str]:
    """
    YouTube 的 n challenge 需要 JS 运行时（yt-dlp EJS）求解：
    优先 Deno（yt-dlp 默认支持），其次 Node（≥22）。返回运行时名或 None。
    """
    import shutil
    import subprocess

    for name, min_major in (("deno", 2), ("node", 22)):
        exe = shutil.which(name)
        if not exe:
            continue
        try:
            out = subprocess.run([exe, "--version"], capture_output=True,
                                 text=True, timeout=10).stdout.strip()
            import re as _re
            m = _re.search(r"(\d+)\.", out)
            if m and int(m.group(1)) >= min_major:
                return name
        except Exception:
            continue
    return None


def _download_format_options(max_height: int = 720) -> Dict:
    """先限制源画质，缺少低清版本时取最低分辨率，避免回退到无上限 best。"""
    height = max(1, int(max_height))
    return {
        "format": (
            f"bv*[height<={height}][vcodec~='^(avc|h264)']+ba"
            f"/b[height<={height}][vcodec~='^(avc|h264)']"
            f"/bv*[height<={height}]+ba/b[height<={height}]"
            "/wv*+ba/w/wv*"
        ),
        # 确保 worst 兜底先比较分辨率；H.264 更适合后续本地解码和抽帧。
        "format_sort": ["res", "vcodec:h264", "fps", "size", "br"],
        "format_sort_force": True,
    }


def download_video(url: str, target_dir: str, max_height: int = 720,
                   progress_hook=None) -> Dict:
    """
    下载视频到指定目录（mp4），返回文件路径与元数据。

    Args:
        url: 视频链接（B站/YouTube/微信视频号分享链接）
        target_dir: 保存目录
        max_height: 优先分辨率上限（默认720p；无低清则下载最低分辨率；
            视频号清晰度由解析服务决定，下载后由统一处理流程压缩）
        progress_hook: 进度回调，接收 dict（downloaded_bytes/total_bytes/status）

    Returns:
        {"file_path": str, "info": {...}}
    """
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    platform = detect_platform(url)
    if platform == "wechat":
        return _download_wechat_video(url, target_dir, progress_hook=progress_hook)
    referer = "https://www.youtube.com/" if platform == "youtube" else "https://www.bilibili.com/"

    def _wrap_hook(d):
        if progress_hook:
            try:
                progress_hook(d)
            except Exception:
                pass

    options = {
        "referer": referer,
        "outtmpl": str(target / "%(id)s.%(ext)s"),
        **_download_format_options(max_height),
        "merge_output_format": "mp4",
        "progress_hooks": [_wrap_hook],
        # 分片流（YouTube DASH/HLS）多线程下载；B站等单文件流不受影响
        "concurrent_fragment_downloads": 8,
        # 对支持 Range 的直链启用分块请求，提高单文件吞吐
        "http_chunk_size": 10485760,   # 10MB
        "retries": 5,
        "fragment_retries": 5,
    }
    import time
    import os
    import tempfile

    def _settings_text(key: str) -> str:
        try:
            from backend.algorithm.settings_store import load_settings
            return (load_settings().get(key) or "").strip()
        except Exception:
            return ""

    def _build_cookiefile():
        """返回 (cookie 文件路径, 是否为本进程生成的临时文件)"""
        if platform == "bilibili":
            path = _bilibili_cookiefile()
            return (path, True) if path else (None, False)
        # YouTube bot 检查：环境变量 cookies 文件优先，其次设置控制台粘贴的 cookies.txt
        env_cookies = os.getenv("YTDLP_COOKIES_FILE")
        if env_cookies and os.path.exists(env_cookies):
            return env_cookies, False
        text = _settings_text("youtube_cookies")
        if text and "youtube.com" in text.lower():
            fd, path = tempfile.mkstemp(prefix="yt_cookies_", suffix=".txt")
            with os.fdopen(fd, "w") as f:
                f.write(text if text.endswith("\n") else text + "\n")
            return path, True
        return None, False

    def _remove_cookiefile(entry):
        if entry and entry[1]:
            try:
                os.remove(entry[0])
            except Exception:
                pass

    cookie_entry = _build_cookiefile()
    if cookie_entry[0]:
        options["cookiefile"] = cookie_entry[0]
    # YouTube：集成 bgutil PO Token 插件的脚本路径（若已安装，绕过 PO Token 限制）
    if platform == "youtube":
        pot_script = _bgutil_script_path()
        if pot_script:
            options["extractor_args"] = {
                "youtubepot-bgutilscript": {"script_path": [pot_script]}}
            logging.info("已启用 bgutil PO Token 脚本")
        # n challenge（EJS）需要 JS 运行时，否则大量格式会被服务端隐藏
        js_runtime = _youtube_js_runtime()
        if js_runtime:
            options["js_runtimes"] = {js_runtime: {}}
            logging.info(f"YouTube JS challenge 运行时: {js_runtime}")

    info = None
    last_error = None
    for attempt in range(4):
        try:
            with _get_ydl(**options) as ydl:
                info = ydl.extract_info(url, download=True)
            break
        except Exception as e:
            last_error = e
            message = str(e)
            if "Sign in" in message or "not a bot" in message:
                _remove_cookiefile(cookie_entry)
                raise ValueError(
                    "YouTube 要求登录验证（bot 检查）。请在设置控制台「YouTube cookies」"
                    "粘贴浏览器导出的 cookies.txt（Netscape 格式，需含 youtube.com 的登录 cookie）"
                    "后重试；或设置环境变量 YTDLP_COOKIES_FILE 指向该文件。"
                )
            if "needs to be reloaded" in message or "SABR" in message:
                _remove_cookiefile(cookie_entry)
                raise ValueError(
                    "YouTube 对当前网络出口强制启用 SABR 流（常见于数据中心/代理 IP），"
                    "下载被服务端限制。可尝试：1) 更换网络环境或代理节点后重试；"
                    "2) 安装 PO Token 支持（scripts/install_yt_pot.sh，详见 README）；"
                    "3) 更新 yt-dlp 至最新版本。"
                )
            if "412" in message or "Precondition" in message:
                wait = 10 * (attempt + 1)   # 10/20/30/40s：412 是分钟级 IP 风控窗口，短退避穿不透
                logging.warning(f"触发平台风控(412)，{wait}s 后重试（第 {attempt + 1}/4 次）")
                time.sleep(wait)
                # 窗口可能已解除：重新生成指纹 cookie 再试
                if platform == "bilibili":
                    _remove_cookiefile(cookie_entry)
                    cookie_entry = _build_cookiefile()
                    if cookie_entry[0]:
                        options["cookiefile"] = cookie_entry[0]
                continue
            raise
    _remove_cookiefile(cookie_entry)
    if info is None:
        raise last_error
    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise ValueError("该链接下没有可用的视频")
        info = entries[0]

    file_path = Path(info.get("filename") or info.get("id") or "")
    # merge 后容器可能是 mp4，yt-dlp 的 filename 已反映最终后缀
    if not file_path.exists():
        candidates = sorted(target.glob(f"{info.get('id')}.*"))
        if not candidates:
            raise ValueError(f"下载完成但未找到文件: {info.get('id')}")
        file_path = candidates[0]

    logging.info(f"视频下载完成: {file_path}")
    return {"file_path": str(file_path), "info": _simplify_info(info, platform)}
