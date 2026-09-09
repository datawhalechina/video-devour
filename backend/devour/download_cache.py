# -*- coding: utf-8 -*-
"""
视频下载缓存与存储映射表

目的：同一视频重复处理时不再重复下载，直接复用本地文件。

设计：
- 缓存目录：<数据根>/downloads/
- 文件名：{platform}_{video_id}.mp4（跨任务稳定，与 task_id 解耦）
- 映射表：downloads/index.json，记录每个视频的来源 URL、平台、标题、
  文件名、大小、下载时间、最近使用时间、命中次数
- 并发安全：文件锁 + 原子写入
"""
import json
import logging
import os
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_lock = threading.RLock()

# 复用阈值：小于此大小视为无效缓存（下载中断残留）
MIN_VALID_BYTES = 100 * 1024


def _data_root() -> Path:
    """数据根目录（桌面端与 Web 端一致，统一走 runtime.paths）"""
    try:
        from backend.runtime import paths as _rt_paths
        return Path(_rt_paths.data_root())
    except Exception:
        return PROJECT_ROOT


def cache_dir() -> Path:
    d = _data_root() / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def index_file() -> Path:
    return cache_dir() / "index.json"


def _load_index() -> Dict:
    f = index_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning(f"下载索引读取失败，重建: {e}")
        return {}


def _save_index(index: Dict):
    f = index_file()
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, f)   # 原子替换


def _safe_id(value: str, limit: int = 80) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value or "").strip("_")
    return value[:limit] or "unknown"


def cache_key(url: str, platform: str = "") -> str:
    """缓存键：优先用平台+视频 ID（跨 URL 变体复用），否则用 URL 哈希"""
    try:
        from backend.devour.video_downloader import detect_platform, _extract_video_id
        platform = platform or detect_platform(url)
        vid = _extract_video_id(url, platform)
        if vid:
            return f"{platform}_{_safe_id(vid)}"
    except Exception:
        pass
    import hashlib
    return f"url_{hashlib.sha1((url or '').encode()).hexdigest()[:16]}"


def lookup(url: str, platform: str = "") -> Optional[Dict]:
    """
    查询缓存：命中且文件有效时返回条目（含 file_path），否则 None。
    同时更新 last_used_at 与 hit_count。
    """
    key = cache_key(url, platform)
    with _lock:
        index = _load_index()
        entry = index.get(key)
        if not entry:
            return None
        path = cache_dir() / entry.get("filename", "")
        if not path.exists() or path.stat().st_size < MIN_VALID_BYTES:
            # 缓存失效：清理条目
            index.pop(key, None)
            _save_index(index)
            return None
        entry["hit_count"] = int(entry.get("hit_count", 0)) + 1
        entry["last_used_at"] = datetime.now().isoformat()
        entry["file_path"] = str(path)
        index[key] = entry
        _save_index(index)
        logging.info(f"命中下载缓存: {key} → {path.name}（复用 {entry['hit_count']} 次）")
        return entry


def register(url: str, file_path: str, platform: str = "", info: Dict = None) -> Dict:
    """
    登记下载结果到缓存与映射表。

    若源文件已在缓存目录内则原地登记；否则复制进缓存（保留源文件）。
    返回映射表条目。
    """
    info = info or {}
    key = cache_key(url, platform)
    platform = platform or key.split("_", 1)[0]
    src = Path(file_path)
    if not src.exists():
        raise FileNotFoundError(f"登记失败，文件不存在: {file_path}")

    ext = src.suffix.lower() or ".mp4"
    filename = f"{key}{ext}"
    dest = cache_dir() / filename

    with _lock:
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        entry = {
            "key": key,
            "platform": platform,
            "source_url": url,
            "video_id": info.get("id") or key.split("_", 1)[-1],
            "title": (info.get("title") or "")[:200],
            "uploader": (info.get("uploader") or "")[:100],
            "filename": filename,
            "size": dest.stat().st_size,
            "downloaded_at": datetime.now().isoformat(),
            "last_used_at": datetime.now().isoformat(),
            "hit_count": 0,
        }
        index = _load_index()
        old = index.get(key)
        if old:   # 保留历史命中统计
            entry["hit_count"] = old.get("hit_count", 0)
            entry["downloaded_at"] = old.get("downloaded_at", entry["downloaded_at"])
        index[key] = entry
        _save_index(index)
        logging.info(f"已登记下载缓存: {key} → {filename}（{entry['size'] / 1024 / 1024:.1f}MB）")
        return {**entry, "file_path": str(dest)}


def materialize(url: str, target_path, platform: str = "") -> Optional[Dict]:
    """
    把缓存文件复制到目标路径（供任务使用，缓存保留）。
    命中缓存时返回条目，否则 None。
    """
    entry = lookup(url, platform)
    if not entry:
        return None
    src = Path(entry["file_path"])
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # 同文件系统优先硬链接（零拷贝），失败回退复制
        if target.exists():
            target.unlink()
        try:
            os.link(src, target)
        except OSError:
            shutil.copy2(src, target)
        return {**entry, "file_path": str(target)}
    except Exception as e:
        logging.warning(f"缓存复用失败（{e}），将重新下载")
        return None


def stats() -> Dict:
    """缓存统计：条目数、总大小、节省的下载次数"""
    with _lock:
        index = _load_index()
    total_size = 0
    missing = 0
    for e in index.values():
        p = cache_dir() / e.get("filename", "")
        if p.exists():
            total_size += p.stat().st_size
        else:
            missing += 1
    return {
        "entries": len(index),
        "total_size": total_size,
        "total_size_human": f"{total_size / 1024 / 1024:.1f} MB",
        "reused_downloads": sum(int(e.get("hit_count", 0)) for e in index.values()),
        "missing_files": missing,
        "cache_dir": str(cache_dir()),
    }


def list_entries() -> list:
    """映射表全量列表（按最近使用倒序）"""
    with _lock:
        index = _load_index()
    items = []
    for key, e in index.items():
        p = cache_dir() / e.get("filename", "")
        items.append({
            **{k: v for k, v in e.items() if k != "filename"},
            "filename": e.get("filename"),
            "exists": p.exists(),
            "file_path": str(p),
        })
    items.sort(key=lambda x: x.get("last_used_at") or "", reverse=True)
    return items


def prune(max_age_days: int = 0, max_total_bytes: int = 0) -> Dict:
    """清理缓存：按时间或总量。两者都为 0 时不删除。"""
    removed, freed = 0, 0
    with _lock:
        index = _load_index()
        candidates = []
        for key, e in index.items():
            p = cache_dir() / e.get("filename", "")
            if not p.exists():
                candidates.append((key, None, 0))
                continue
            candidates.append((key, e, p.stat().st_size))
        # 按最近使用时间升序（最久未用的先删）
        candidates.sort(key=lambda c: (c[1] or {}).get("last_used_at") or "")
        total = sum(c[2] for c in candidates)
        now = time.time()
        for key, entry, size in candidates:
            if entry is None:
                index.pop(key, None)
                removed += 1
                continue
            drop = False
            if max_age_days > 0:
                last = entry.get("last_used_at") or entry.get("downloaded_at") or ""
                try:
                    if (now - datetime.fromisoformat(last).timestamp()) > max_age_days * 86400:
                        drop = True
                except Exception:
                    pass
            if max_total_bytes > 0 and total > max_total_bytes:
                drop = True
            if drop:
                p = cache_dir() / entry.get("filename", "")
                if p.exists():
                    p.unlink(); freed += size
                index.pop(key, None); removed += 1; total -= size
        _save_index(index)
    return {"removed": removed, "freed": freed, "freed_human": f"{freed / 1024 / 1024:.1f} MB"}
