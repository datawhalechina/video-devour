# -*- coding: utf-8 -*-
"""
微信公众号发布：把 VideoDevour 报告（Markdown）转为公众号图文并创建草稿。

链路（全部官方接口，2026-10 实测可用）：
  appid+secret → access_token（2h 有效，缓存+提前刷新）
  报告内本地图片 → media/uploadimg（图文正文禁止外链图片，必须换公众号 URL）
  封面 → material/add_material(type=thumb) → thumb_media_id（草稿必填封面）
  Markdown → 内联样式 HTML（公众号编辑器不支持外部样式表）
  draft/add 创建草稿 → 用户在公众号后台预览确认后手动发布

不自动群发：群发有次数限制且内容责任在运营者，草稿模式更安全；
未认证订阅号本也无 freepublish 权限（草稿接口不受影响）。

凭据存 settings.json（wechat_mp_appid / wechat_mp_secret），已在 gitignore。
"""
import io
import json
import logging
import re
import time
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.weixin.qq.com/cgi-bin"
_HTTP_TIMEOUT = 30
_CONTENT_MAX_CHARS = 19000   # 官方正文上限约 2 万字符，留余量
_THUMB_SIZE = (900, 383)     # 公众号封面推荐比例 2.35:1

# 模块级 token 缓存：{token, expires_at( epoch 秒 )}
_token_cache: Dict = {}


class WechatMpError(Exception):
    """面向用户的发布失败（文案可直接透出前端）。"""


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

def _get_credentials() -> Dict:
    """从设置读取 appid/secret（缺失时抛带引导的错误）。"""
    from backend.algorithm import settings_store
    s = settings_store.load_settings()
    appid = (s.get("wechat_mp_appid") or "").strip()
    secret = (s.get("wechat_mp_secret") or "").strip()
    if not appid or not secret:
        raise WechatMpError("未配置公众号凭据：请在设置页填写「公众号 AppID / AppSecret」")
    return {"appid": appid, "secret": secret}


# ---------------------------------------------------------------------------
# API 封装
# ---------------------------------------------------------------------------

def get_access_token(force: bool = False) -> str:
    """获取并缓存 access_token（提前 5 分钟过期，避免临界失效）。"""
    now = time.time()
    if not force and _token_cache.get("token") and _token_cache.get("expires_at", 0) > now + 300:
        return _token_cache["token"]

    cred = _get_credentials()
    try:
        resp = requests.get(
            f"{_API_BASE}/token",
            params={"grant_type": "client_credential",
                    "appid": cred["appid"], "secret": cred["secret"]},
            timeout=_HTTP_TIMEOUT,
        ).json()
    except requests.RequestException as e:
        raise WechatMpError(f"访问微信接口失败（网络异常）：{e}") from e

    if "access_token" not in resp:
        raise WechatMpError(_map_error(resp))
    _token_cache.update({
        "token": resp["access_token"],
        "expires_at": now + int(resp.get("expires_in", 7200)),
    })
    return resp["access_token"]


def _map_error(resp: Dict) -> str:
    """微信 errcode → 用户可理解的文案。"""
    code = resp.get("errcode")
    msg = (resp.get("errmsg") or "")[:120]
    if code == 40164:
        ip = re.search(r"invalid ip ([\d.]+)", msg)
        ip_hint = f"（本机出口 IP：{ip.group(1)}）" if ip else ""
        return (f"本机 IP 不在公众号白名单内{ip_hint}。"
                "请在公众号后台「设置与开发 → 基本配置 → IP 白名单」添加后重试")
    if code in (40001, 42001, 40014):
        return "access_token 已失效或 AppSecret 有误，请确认凭据最新（后台重置 Secret 后需同步更新设置页）"
    if code == 40013:
        return "AppID 无效，请核对公众号 AppID"
    if code == 40125:
        return "AppSecret 无效，请在公众号后台「基本配置」重置后填入新值"
    if code == 45002:
        return "正文内容超出公众号限制（约 2 万字符），请精简后重试"
    if code == 53401:
        return "封面图校验失败，请更换封面后重试"
    return f"微信接口返回错误 {code}：{msg}"


def _api_call(method: str, path: str, *, params=None, data=None,
              files=None, json_body=None, retry_on_token: bool = True) -> Dict:
    """统一调用：自动带 token，40001/42001 时强刷 token 重试一次。"""
    token = get_access_token()
    try:
        resp = requests.request(
            method, f"{_API_BASE}{path}",
            params={**(params or {}), "access_token": token},
            data=data, files=files, json=json_body, timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise WechatMpError(f"访问微信接口失败（网络异常）：{e}") from e

    try:
        out = resp.json()
    except ValueError:
        raise WechatMpError(f"微信接口返回非 JSON：HTTP {resp.status_code}")

    code = out.get("errcode", 0)
    if code in (40001, 42001, 40014) and retry_on_token:
        # token 失效：强刷后重试一次
        get_access_token(force=True)
        return _api_call(method, path, params=params, data=data, files=files,
                         json_body=json_body, retry_on_token=False)
    if code and "access_token" not in out:
        raise WechatMpError(_map_error(out))
    return out


# ---------------------------------------------------------------------------
# 素材上传
# ---------------------------------------------------------------------------

def upload_content_image(image_path) -> str:
    """图文正文图片上传（返回公众号 URL，可内嵌正文）。"""
    p = Path(image_path)
    if not p.exists():
        raise WechatMpError(f"图片不存在：{p.name}")
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    with open(p, "rb") as f:
        out = _api_call("POST", "/media/uploadimg",
                        files={"media": (p.name, f, mime)})
    url = out.get("url")
    if not url:
        raise WechatMpError(f"图片上传未返回 URL：{p.name}")
    return url


def upload_thumb_material(image_path) -> str:
    """封面图上传为永久素材（返回 thumb_media_id，草稿必填）。"""
    p = Path(image_path)
    if not p.exists():
        raise WechatMpError(f"封面图不存在：{p.name}")
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    with open(p, "rb") as f:
        out = _api_call("POST", "/material/add_material",
                        params={"type": "thumb"},
                        files={"media": (p.name, f, mime)})
    media_id = out.get("thumb_media_id") or out.get("media_id")
    if not media_id:
        raise WechatMpError("封面上传未返回 media_id")
    return media_id


def draft_count() -> int:
    """草稿总数（用于连通性探测，只读）"""
    out = _api_call("GET", "/draft/count")
    return int(out.get("total_count", 0))


# ---------------------------------------------------------------------------
# Markdown → 公众号 HTML
# ---------------------------------------------------------------------------

# 公众号编辑器兼容的内联样式（不支持外部 CSS / class 选择器样式会被剥离）
_STYLE = {
    "h1": ("font-size:22px;font-weight:700;color:#1f2937;line-height:1.4;"
           "margin:28px 0 14px;text-align:center;"),
    "h2": ("font-size:18px;font-weight:700;color:#1d4ed8;line-height:1.4;"
           "margin:26px 0 12px;padding-left:10px;border-left:4px solid #1d4ed8;"),
    "h3": "font-size:16px;font-weight:700;color:#374151;line-height:1.5;margin:20px 0 8px;",
    "h4": "font-size:15px;font-weight:700;color:#4b5563;line-height:1.5;margin:16px 0 6px;",
    "p": "font-size:15px;color:#374151;line-height:1.9;margin:12px 0;letter-spacing:0.5px;",
    "blockquote": ("margin:16px 0;padding:12px 16px;background:#f0f7ff;"
                   "border-left:4px solid #60a5fa;border-radius:4px;"
                   "font-size:14px;color:#4b5563;line-height:1.8;"),
    "ul": "padding-left:22px;margin:10px 0;",
    "ol": "padding-left:26px;margin:10px 0;",
    "li": "font-size:15px;color:#374151;line-height:1.9;margin:4px 0;",
    "code": ("background:#f3f4f6;color:#c7254e;padding:2px 5px;border-radius:3px;"
             "font-size:13.5px;font-family:Menlo,Consolas,monospace;"),
    "pre": ("background:#f8f9fa;padding:14px;border-radius:6px;overflow-x:auto;"
            "font-size:13px;line-height:1.6;margin:14px 0;"),
    "table": ("border-collapse:collapse;width:100%;margin:14px 0;font-size:14px;"),
    "th": ("border:1px solid #d1d5db;background:#f3f4f6;padding:8px 10px;"
           "font-weight:600;text-align:left;"),
    "td": "border:1px solid #d1d5db;padding:8px 10px;line-height:1.7;",
    "img": "max-width:100%;border-radius:6px;margin:14px auto;display:block;",
    "a": "color:#1d4ed8;text-decoration:none;border-bottom:1px solid #93c5fd;",
    "hr": "border:none;border-top:1px solid #e5e7eb;margin:24px 0;",
}


def _inline_styles(html: str) -> str:
    """给 markdown 库产出的规范标签打内联样式（微信会剥离 class/style 标签）。"""
    for tag, style in _STYLE.items():
        # 仅补 style：已有 style 的保留原值，属性顺序按库输出稳定可控
        html = re.sub(
            rf"<{tag}([^>]*)>",
            lambda m, t=tag, s=style: (f"<{t}{m.group(1)} style=\"{s}\">"
                                       if "style=" not in m.group(1) else m.group(0)),
            html)
    return html


def markdown_to_wechat_html(md_text: str,
                            image_resolver: Optional[Callable[[str], Optional[str]]] = None,
                            drop_mermaid: bool = True) -> str:
    """
    Markdown → 公众号正文 HTML。

    Args:
        image_resolver: 本地图片路径 → 公众号 URL 的回调（None 时图片全部移除）
        drop_mermaid: 公众号不支持 JS，mermaid 代码块默认剔除（避免读者看到原始代码）
    """
    import markdown as _md

    if drop_mermaid:
        md_text = re.sub(r"```mermaid[\s\S]*?```", "", md_text)

    # 本地/相对图片 → 占位处理：先抽出，渲染后统一替换（渲染器可能改写 alt/顺序）
    image_paths = []
    if image_resolver:
        def _collect(m):
            image_paths.append(m.group(2))
            return f"![{m.group(1)}](__VD_IMG_{len(image_paths) - 1}__)"
        md_text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _collect, md_text)

    html = _md.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])

    # 占位图替换为公众号 URL；解析失败（文件缺失/上传失败）则剔除该图
    def _resolve_img(m):
        idx = int(m.group(1))
        if 0 <= idx < len(image_paths):
            url = image_resolver(image_paths[idx])
            if url:
                return f"<img src=\"{url}\" />"
        return ""
    html = re.sub(r'<img[^>]*src="__VD_IMG_(\d+)__"[^>]*/?>', _resolve_img, html)
    # 渲染器把占位放进 alt 的情况兜底
    html = re.sub(r'<img[^>]*alt="__VD_IMG_(\d+)__"[^>]*/?>', _resolve_img, html)

    html = _inline_styles(html)
    # 公众号正文根节点用 section 包裹（部分编辑器对顶层 div 样式兼容差）
    return (f'<section style=\"max-width:677px;margin:0 auto;font-family:'
            f'-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Helvetica Neue\',sans-serif;\">'
            f"{html}</section>")


# ---------------------------------------------------------------------------
# 封面兜底：无关键帧时用 Pillow 生成标题封面
# ---------------------------------------------------------------------------

def _find_cjk_font() -> Optional[str]:
    for p in (
        "/System/Library/Fonts/PingFang.ttc",                    # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",               # macOS 旧
        "C:/Windows/Fonts/msyh.ttc",                             # Windows 微软雅黑
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux Noto
    ):
        if Path(p).exists():
            return p
    return None


def generate_title_cover(title: str, out_path) -> str:
    """纯文字标题封面（900x383 深色渐变 + 白色标题）。生成失败抛 WechatMpError。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise WechatMpError("生成封面需要 Pillow（pip install Pillow）") from e

    w, h = _THUMB_SIZE
    img = Image.new("RGB", (w, h), "#1e3a5f")
    draw = ImageDraw.Draw(img)
    # 纵向渐变：#1e3a5f → #2563eb
    for y in range(h):
        t = y / h
        r = int(0x1e + (0x25 - 0x1e) * t)
        g = int(0x3a + (0x63 - 0x3a) * t)
        b = int(0x5f + (0xeb - 0x5f) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    font_path = _find_cjk_font()
    # 标题截断为两行、每行最多 14 字
    text = (title or "VideoDevour").strip()[:28]
    lines = [text[i:i + 14] for i in range(0, len(text), 14)][:2]
    if font_path:
        f_title = ImageFont.truetype(font_path, 44)
        f_sub = ImageFont.truetype(font_path, 20)
    else:
        f_title = f_sub = ImageFont.load_default()
    y0 = h // 2 - 36 * len(lines)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=f_title)
        draw.text(((w - (bbox[2] - bbox[0])) // 2, y0), line, fill="white", font=f_title)
        y0 += 76
    if font_path:
        sub = "VideoDevour · 视频知识笔记"
        bbox = draw.textbbox((0, 0), sub, font=f_sub)
        draw.text(((w - (bbox[2] - bbox[0])) // 2, h - 56), sub,
                  fill=(255, 255, 255, 200), font=f_sub)

    out_path = str(out_path)
    img.save(out_path, "JPEG", quality=90)
    return out_path


# ---------------------------------------------------------------------------
# 发布入口
# ---------------------------------------------------------------------------

def publish_report_to_draft(report_path, title: str, digest: str = "",
                            author: str = "", cover_path=None,
                            cover_title: str = "") -> Dict:
    """
    报告 Markdown → 公众号草稿。

    Args:
        report_path: 报告 md 文件路径（图片相对该文件所在目录解析）
        title: 图文标题（≤64 字）
        digest: 摘要（空则正文前 54 字）
        cover_path: 封面图；为空时自动生成标题封面
    Returns:
        {"media_id", "title", "url"(公众号后台提示用，无直链)}
    """
    report_path = Path(report_path)
    if not report_path.exists():
        raise WechatMpError(f"报告文件不存在：{report_path.name}")
    md_text = report_path.read_text(encoding="utf-8")
    if not md_text.strip():
        raise WechatMpError("报告内容为空")

    title = (title or report_path.stem).strip()[:64]
    base_dir = report_path.parent

    def _resolve_image(img_ref: str) -> Optional[str]:
        # 相对路径按报告目录解析；http(s) 链接直传会因外链限制失败，跳过
        if img_ref.startswith(("http://", "https://")):
            return None
        p = (base_dir / img_ref).resolve()
        if not p.exists():
            logger.warning(f"报告引用图片缺失，已剔除：{img_ref}")
            return None
        try:
            return upload_content_image(p)
        except WechatMpError as e:
            logger.warning(f"图片上传失败，已剔除 {img_ref}: {e}")
            return None

    html = markdown_to_wechat_html(md_text, image_resolver=_resolve_image)
    if len(html) > _CONTENT_MAX_CHARS:
        raise WechatMpError(
            f"正文约 {len(html)} 字符，超出公众号上限（约 2 万）。"
            "建议改用精简版报告（final_report）或缩短内容后重试"
        )

    # 封面：指定图 > 自动标题封面
    cover = cover_path
    if not cover:
        cover = generate_title_cover(cover_title or title,
                                     report_path.parent / "wechat_cover.jpg")
    thumb_media_id = upload_thumb_material(cover)

    article = {
        "title": title,
        "content": html,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    if digest:
        article["digest"] = digest.strip()[:120]
    if author:
        article["author"] = author.strip()[:8]

    out = _api_call("POST", "/draft/add", json_body={"articles": [article]})
    media_id = out.get("media_id")
    if not media_id:
        raise WechatMpError(f"草稿创建未返回 media_id：{json.dumps(out, ensure_ascii=False)[:200]}")
    logger.info(f"公众号草稿已创建: {title} (media_id={media_id})")
    return {"media_id": media_id, "title": title}
