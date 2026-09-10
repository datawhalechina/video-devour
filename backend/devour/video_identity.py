# -*- coding: utf-8 -*-
"""视频身份：把「同一个视频的多次处理」归并到同一个存储标记下。

- 有来源链接：复用下载缓存键（平台 + 视频 ID），跨 URL 变体稳定
- 本地文件：用文件指纹（大小 + 首尾分片）标识，同一视频重复上传可归并

同一 video_key 的多次处理按完成先后得到 V1、V2…，内容各自保留。
"""
import hashlib
from pathlib import Path
from typing import Optional

_FINGERPRINT_SLICE = 1024 * 1024


def content_fingerprint(path) -> str:
    """文件指纹：大小 + 首尾各 1MB，避免为几百 MB 视频做全量哈希。"""
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha1(str(size).encode())
    with p.open("rb") as f:
        h.update(f.read(_FINGERPRINT_SLICE))
        if size > _FINGERPRINT_SLICE * 2:
            f.seek(-_FINGERPRINT_SLICE, 2)
            h.update(f.read(_FINGERPRINT_SLICE))
    return h.hexdigest()[:16]


def video_key(source_url: str = "", file_path=None) -> str:
    """解析视频身份键：来源链接优先，否则用本地文件指纹。"""
    url = (source_url or "").strip()
    if url:
        try:
            from backend.devour.download_cache import cache_key
            return cache_key(url)
        except Exception:
            pass
    if file_path:
        try:
            return f"local_{content_fingerprint(file_path)}"
        except Exception:
            pass
    return ""


def version_of(meta: dict) -> Optional[int]:
    """读取任务记录中的版本号（缺失时返回 None，由调用方按时间补齐）。"""
    value = meta.get("version")
    return int(value) if isinstance(value, int) and value > 0 else None
