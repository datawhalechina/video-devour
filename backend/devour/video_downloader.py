# -*- coding: utf-8 -*-
"""
在线视频链接下载器（Bilibili / YouTube / 微信视频号等）

移植自 bilibili-video-download 与 youtube-downloader 两个工具的核心思路：
- 先取元数据（标题/封面/时长/作者）供预览确认，再执行下载
- yt-dlp 统一支持 B 站与 YouTube（含搜索），ffmpeg 负责合成 mp4
- 微信视频号不支持 yt-dlp：优先走分享链接解析服务换直链，失败时引导本地捕获
- 合理默认值：单个视频（不展开合集/列表）、最高 1080p、mp4 输出

说明：请仅对拥有版权或已获授权的内容进行下载处理。
"""
import logging
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

    referer = extra.pop("referer", "https://www.bilibili.com/")
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,   # 单视频优先，不展开合集
        "socket_timeout": 20,
        "retries": 3,
        # 浏览器指纹：B站等平台对无 UA/Referer 的请求会返回 412
        "http_headers": {
            "User-Agent": _BROWSER_UA,
            "Referer": referer,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    }
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
        # 视频号不支持 yt-dlp，先从分享页尽力取标题，解析下载在 download 阶段进行
        return _wechat_share_info(url)
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
# 机制参考 joeseesun/qiaomu-wx-video：视频号没有公开直链，两条路径——
# 1) 在线解析：把分享链接交给解析服务换媒体直链（尽力而为，服务可能限流/要求授权）
# 2) 本地捕获：ltaoo/wx_channels_download 依赖微信桌面端+根证书+本地代理，
#    属于重量级人工流程，本项目不自动执行，失败时引导用户走该路径后手动上传。
# ---------------------------------------------------------------------------

_WECHAT_FAIL_HINT = (
    "视频号在线解析失败：分享链接可能已过期、内容为直播回放，或解析服务暂时不可用。"
    "可尝试：1) 稍后重试；2) 自建解析服务并通过环境变量 WECHAT_RESOLVER_URL 指向它；"
    "3) 使用本地捕获工具（ltaoo/wx_channels_download，参考 joeseesun/qiaomu-wx-video 工作流）"
    "下载到本机后，在“上传视频”页直接处理。"
)


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


def _wechat_resolver_base() -> str:
    import os
    return (os.getenv("WECHAT_RESOLVER_URL") or DEFAULT_WECHAT_RESOLVER).rstrip("/")


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


def _wechat_resolve(share_url: str, target_dir: Path, vid: str):
    """
    调用解析服务，返回待下载源列表。

    每个元素为 (kind, payload)：kind 为 "url"（mp4/m3u8 直链）或
    "local"（解析服务直接回流的媒体内容，已落盘的临时文件）。
    """
    import requests

    sources = []
    base = _wechat_resolver_base()
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
        # JSON 或 HTML：提取媒体直链
        media = _find_media_urls(_safe_json(resp))
        if not media:
            media = re.findall(
                r"https?://[^\"'\\\s<>]+\.(?:mp4|m3u8)[^\"'\\\s<>]*",
                resp.text or "", re.IGNORECASE,
            )
        sources = [("m3u8" if u.lower().split("?")[0].endswith(".m3u8") else "url", u)
                   for u in dict.fromkeys(media)]
        if sources:
            break
    if not sources and last_status:
        sources = []  # 保留空列表，由调用方统一报错
    return sources, last_status


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
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
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


def _download_wechat_video(url: str, target_dir: str, progress_hook=None) -> Dict:
    """视频号下载：解析直链 → 流式下载 → ffprobe 验证 → 落盘为 {vid}.mp4"""
    import requests
    import subprocess

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

    sources, resolver_status = _wechat_resolve(share_url, target, vid)
    if not sources:
        if resolver_status in (401, 403):
            raise ValueError(_WECHAT_FAIL_HINT + f"（解析服务返回 {resolver_status}，公共实例可能已限流）")
        raise ValueError(_WECHAT_FAIL_HINT)

    final_path = target / f"{vid}.mp4"
    errors = []
    for kind, payload in sources:
        try:
            if kind == "local":
                Path(payload).replace(final_path)
            elif kind == "m3u8":
                # 未加密 HLS 可直接由 ffmpeg 下载合成；加密流会失败进入下一个候选
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-i", payload, "-c", "copy",
                     "-bsf:a", "aac_adtstoasc", str(final_path)],
                    capture_output=True, timeout=600,
                )
                if proc.returncode != 0:
                    raise RuntimeError("m3u8 下载失败（可能为加密流）")
            else:
                with requests.get(
                    payload, stream=True, timeout=(10, 60),
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
            if _validate_video_file(final_path):
                logging.info(f"视频号下载完成: {final_path}")
                return {"file_path": str(final_path),
                        "info": _wechat_share_info(share_url)}
            errors.append(f"候选源校验失败: {payload[:80]}")
        except Exception as e:
            errors.append(f"{str(e)[:120]} ({payload[:60]})")
        finally:
            if kind == "local" and Path(payload).exists():
                Path(payload).unlink(missing_ok=True)
    if final_path.exists():
        final_path.unlink(missing_ok=True)
    detail = f"（{'；'.join(errors[-2:])}）" if errors else ""
    raise ValueError(_WECHAT_FAIL_HINT + detail)


def _youtube_thumbnail_fallback(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def _bilibili_session():
    """
    带浏览器指纹的 B站会话：先访问主站获取 buvid3 cookie，
    否则搜索/信息接口会返回 412 Precondition Failed。
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


def download_video(url: str, target_dir: str, max_height: int = 1080,
                   progress_hook=None) -> Dict:
    """
    下载视频到指定目录（mp4），返回文件路径与元数据。

    Args:
        url: 视频链接（B站/YouTube/微信视频号分享链接）
        target_dir: 保存目录
        max_height: 最大分辨率（默认1080p；视频号清晰度由解析服务决定，此参数不生效）
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
        "format": (
            f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]"
            f"/b[height<={max_height}]/bv*[height<={max_height}]+ba/b"
        ),
        "merge_output_format": "mp4",
        "progress_hooks": [_wrap_hook],
        "concurrent_fragment_downloads": 4,
    }
    import time
    import os
    cookie_file = _bilibili_cookiefile() if platform == "bilibili" else None
    if cookie_file:
        options["cookiefile"] = cookie_file
    else:
        # YouTube bot 检查：允许通过环境变量提供浏览器导出的 cookies 文件
        env_cookies = os.getenv("YTDLP_COOKIES_FILE")
        if env_cookies and os.path.exists(env_cookies):
            options["cookiefile"] = env_cookies
    info = None
    last_error = None
    for attempt in range(3):
        try:
            with _get_ydl(**options) as ydl:
                info = ydl.extract_info(url, download=True)
            break
        except Exception as e:
            last_error = e
            message = str(e)
            if "Sign in" in message or "not a bot" in message:
                raise ValueError(
                    "YouTube 要求登录验证（bot 检查）。请用浏览器导出 cookies 为 Netscape 格式，"
                    "并设置环境变量 YTDLP_COOKIES_FILE 指向该文件后重试。"
                )
            if "412" in message or "Precondition" in message:
                wait = 5 * (attempt + 1)
                logging.warning(f"触发平台风控(412)，{wait}s 后重试 (第 {attempt + 1}/2 次)")
                time.sleep(wait)
                continue
            raise
    if cookie_file:
        try:
            import os
            os.remove(cookie_file)
        except Exception:
            pass
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
