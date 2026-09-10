# -*- coding: utf-8 -*-
"""
个人文档库：以「单次视频处理任务」为单位组织全部生成内容。

数据模型（一个任务 = 一篇文档，含多个文章维度）：
    doc_id      = task_id（任务唯一 ID）
    title       = 视频/任务标题
    platform    = bilibili | youtube | wechat | upload | ...
    articles:
        outline   → detailed_outline.md（图文大纲）
        report    → final_report.md（精简报告）
        detailed  → detailed_report.md（详细报告：原文+笔记对照）

入库方式：自动。文章生成落盘后即被扫描收录（按文件 mtime 增量重建索引）。
检索：BM25（CJK 字符级 + 英文词级分词），返回 top-k 及命中摘要。
导出：单篇 .md 下载 / 整库 ZIP（含 manifest.json）。
"""
import hashlib
import json
import logging
import math
import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.runtime import paths as _rt_paths

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = _rt_paths.data_root()
OUTPUT_DIR = DATA_ROOT / "output"

# 文章维度 → 文件名 / 中文名
ARTICLE_TYPES = {
    "outline": ("detailed_outline.md", "图文大纲"),
    "report": ("final_report.md", "精简报告"),
    "detailed": ("detailed_report.md", "详细报告"),
    # 衍生文体：按需生成（style_articles），生成后自动入库
    "quantum": ("quantum_read.md", "量子速读"),
    "wechat": ("wechat_article.md", "公众号文章"),
    "xiaohongshu": ("xiaohongshu_article.md", "小红书笔记"),
}

# 可被「按需生成」的维度（文件不存在时由 style_articles 生成）
GENERATABLE_SCOPES = ("quantum", "wechat", "xiaohongshu")

# 文档库展示顺序：先分析报告，后衍生文体
ARTICLE_ORDER = ("outline", "report", "detailed", "quantum", "wechat", "xiaohongshu")

PLATFORM_LABELS = {
    "bilibili": "B站", "youtube": "YouTube", "wechat": "微信视频号", "upload": "本地上传",
}


# ---------------------------------------------------------------------------
# BM25 检索（轻量实现：CJK 字符级 + 英文/数字词级分词，无需额外依赖）
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff\u3400-\u4dbf]")


def tokenize(text: str) -> List[str]:
    """CJK 逐字成词（中文检索的标准轻量做法），英文/数字按连续词切分"""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class BM25Index:
    """Okapi BM25。corpus 为 {doc_key: text}，支持增量重建（指纹变化才重算）"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self._fingerprint = ""
        self._doc_tokens: Dict[str, List[str]] = {}
        self._doc_freq: Dict[str, int] = {}       # 词 → 含该词的文档数
        self._tf: Dict[str, Dict[str, int]] = {}  # doc_key → {词: 词频}
        self._doc_len: Dict[str, int] = {}
        self._avgdl = 0.0
        self._N = 0

    def _fingerprint_of(self, corpus: Dict[str, str]) -> str:
        h = hashlib.sha1()
        for key in sorted(corpus):
            h.update(key.encode())
            h.update(str(len(corpus[key])).encode())
        return h.hexdigest()

    def build(self, corpus: Dict[str, str]):
        fp = self._fingerprint_of(corpus)
        if fp == self._fingerprint:
            return  # 内容未变，跳过重建
        self._fingerprint = fp
        self._tf, self._doc_len = {}, {}
        self._doc_freq = {}
        for key, text in corpus.items():
            tokens = tokenize(text)
            self._doc_len[key] = len(tokens)
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self._tf[key] = tf
            for t in tf:
                self._doc_freq[t] = self._doc_freq.get(t, 0) + 1
        self._N = len(corpus)
        self._avgdl = (sum(self._doc_len.values()) / self._N) if self._N else 0

    def score(self, query_tokens: List[str], doc_key: str) -> float:
        score = 0.0
        dl = self._doc_len.get(doc_key, 0)
        if not dl:
            return 0.0
        tf = self._tf.get(doc_key, {})
        for t in query_tokens:
            f = tf.get(t)
            if not f:
                continue
            df = self._doc_freq.get(t, 0)
            idf = math.log(1 + (self._N - df + 0.5) / (df + 0.5))
            score += idf * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self._avgdl))
        return round(score, 4)

    def search(self, corpus: Dict[str, str], query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if not corpus:
            return []
        self.build(corpus)
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scored = [(k, self.score(q_tokens, k)) for k in corpus]
        scored = [(k, s) for k, s in scored if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# 库扫描：收集所有任务的文档（自动入库——生成即收录）
# ---------------------------------------------------------------------------

def _load_task_meta(task_id: str) -> Dict:
    """从 tasks.json 读取任务元信息（标题/来源/学习阶段）"""
    tasks_file = DATA_ROOT / "tasks.json"
    try:
        tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        return tasks.get(task_id) or {}
    except Exception:
        return {}


def _detect_platform(source_url: str) -> str:
    u = (source_url or "").lower()
    if "bilibili.com" in u or "b23.tv" in u:
        return "bilibili"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "weixin.qq.com" in u:
        return "wechat"
    return "upload" if u == "" else "other"


def _parse_iso(value: str) -> float:
    try:
        return datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0


def _title_from_report(dir_path: Path, fallback: str) -> str:
    detail = dir_path / "detailed_report.md"
    src = detail if detail.exists() else dir_path / "detailed_outline.md"
    if src.exists():
        try:
            m = re.search(r"^#\s+(.+)", src.read_text(encoding="utf-8"), re.MULTILINE)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
    return fallback


def scan_videos() -> List[Dict]:
    """
    按「视频」聚合全部处理任务：同一视频多次处理形成 V1、V2…的版本链。

    每个条目：
    {
      video_key, title, platform, platform_label, source_url,
      version_count, created_at(最新), first_seen_at,
      versions: [ {doc_id, version, version_label, education_level,
                   created_at, dir, articles:{scope:{file,name,label,mtime,size}}} ]
    }
    versions 按处理时间升序，即 versions[0] = V1。
    """
    videos: Dict[str, Dict] = {}
    if not OUTPUT_DIR.exists():
        return []
    for dir_path in OUTPUT_DIR.iterdir():
        if not (dir_path.is_dir() and dir_path.name.startswith("frames_")):
            continue
        parts = dir_path.name.split("_")
        if len(parts) < 2:
            continue
        doc_id = parts[1]
        meta = _load_task_meta(doc_id)
        source_url = meta.get("source_url") or ""
        try:
            from backend.devour.video_identity import video_key as _vk
            vkey = meta.get("video_key") or _vk(source_url) or f"task_{doc_id}"
        except Exception:
            vkey = meta.get("video_key") or f"task_{doc_id}"
        platform = _detect_platform(source_url) if source_url else "upload"

        articles = {}
        newest_mtime = 0.0
        for scope, (fname, label) in ARTICLE_TYPES.items():
            f = dir_path / fname
            if f.exists() and f.stat().st_size > 0:
                articles[scope] = {
                    "file": str(f), "name": fname, "label": label,
                    "mtime": f.stat().st_mtime, "size": f.stat().st_size,
                }
                newest_mtime = max(newest_mtime, f.stat().st_mtime)
        if not articles:
            continue

        filename = (meta.get("filename") or "").strip()
        # 标题：任务文件名（非 URL）优先，其次详细报告一级标题
        if filename and not filename.startswith(("http://", "https://")):
            title = filename
        else:
            title = _title_from_report(dir_path, filename or doc_id)
        title = title.replace("\n", " ")[:120]

        created_ts = _parse_iso(meta.get("created_at") or "") or dir_path.stat().st_ctime
        created_ts = max(created_ts, newest_mtime) if newest_mtime else created_ts

        entry = videos.setdefault(vkey, {
            "video_key": vkey, "title": title, "platform": platform,
            "platform_label": PLATFORM_LABELS.get(platform, platform),
            "source_url": source_url, "versions": [],
        })
        entry["versions"].append({
            "doc_id": doc_id,
            "run_id": dir_path.name[len("frames_"):] if dir_path.name.startswith("frames_") else dir_path.name,
            "dir": dir_path.name,
            "education_level": meta.get("education_level") or "自由学习",
            "created_at": datetime.fromtimestamp(created_ts).isoformat(),
            "articles": articles,
            "_sort": created_ts,
        })

    result = []
    for entry in videos.values():
        entry["versions"].sort(key=lambda v: (v["_sort"], v["doc_id"]))
        for index, run in enumerate(entry["versions"], 1):
            run.pop("_sort", None)
            run["version"] = index
            run["version_label"] = f"V{index}"
        latest = entry["versions"][-1]
        entry["version_count"] = len(entry["versions"])
        entry["latest_doc_id"] = latest["doc_id"]
        entry["latest_version"] = latest["version"]
        entry["created_at"] = latest["created_at"]
        entry["first_seen_at"] = entry["versions"][0]["created_at"]
        # 标题以最新一次为准（更可能是被修正过的正式标题）
        if latest.get("title"):
            entry["title"] = latest["title"]
        # 同一视频的来源以最新记录为准
        result.append(entry)
    result.sort(key=lambda v: v["created_at"], reverse=True)
    return result


def scan_library() -> List[Dict]:
    """兼容旧接口：展平为「每个处理任务一项」，并附带视频/版本信息。"""
    flat = []
    for video in scan_videos():
        for run in video["versions"]:
            flat.append({
                "doc_id": run["doc_id"],
                "run_id": run.get("run_id", ""),
                "dir": run["dir"],
                "title": video["title"],
                "platform": video["platform"],
                "platform_label": video["platform_label"],
                "source_url": video["source_url"],
                "video_key": video["video_key"],
                "version": run["version"],
                "version_label": run["version_label"],
                "version_count": video["version_count"],
                "education_level": run["education_level"],
                "created_at": run["created_at"],
                "articles": run["articles"],
            })
    flat.sort(key=lambda d: d["created_at"], reverse=True)
    return flat


def get_video(identifier: str) -> Optional[Dict]:
    """按 video_key（或任一版本的 doc_id）取视频详情，含全部版本与文章。

    articles 统一为列表 [{scope,label,size}]，与 list_videos 的形状保持一致。
    """
    target = None
    for video in scan_videos():
        if video["video_key"] == identifier or any(
                run["doc_id"] == identifier for run in video["versions"]):
            target = video
            break
    if target is None:
        return None
    return {
        **{k: v for k, v in target.items() if k != "versions"},
        "versions": [
            {
                **{k: v for k, v in run.items() if k != "articles"},
                "articles": [
                    {"scope": sc, "label": info["label"], "size": info["size"]}
                    for sc, info in run["articles"].items()
                ],
            }
            for run in reversed(target["versions"])   # 最新版本在前，与 list_videos 一致
        ],
    }


def get_article(doc_id: str, scope: str, run_id: str = "") -> Optional[Dict]:
    """获取单篇文章全文（md）。

    同一任务可能产出多个版本（重复处理），此时用 run_id 精确指定某一次输出；
    run_id 缺省时取该任务最近一次的版本。
    """
    label = ARTICLE_TYPES.get(scope, (None, scope))[1]
    fallback = None
    for video in scan_videos():
        for run in video["versions"]:
            if run["doc_id"] != doc_id:
                continue
            if run_id and run.get("run_id") != run_id:
                continue
            hit = {
                "doc": {
                    "doc_id": doc_id, "title": video["title"],
                    "platform": video["platform"], "platform_label": video["platform_label"],
                    "source_url": video["source_url"], "video_key": video["video_key"],
                    "version": run["version"], "version_label": run["version_label"],
                    "version_count": video["version_count"],
                    "run_id": run.get("run_id", ""),
                    "dir": run["dir"],
                },
                "scope": scope, "label": label,
                "file": (run["articles"].get(scope) or {}).get("file"),
            }
            if run_id:
                if not hit["file"]:
                    return None
                hit["content"] = Path(hit["file"]).read_text(encoding="utf-8")
                return hit
            if hit["file"] and (fallback is None or run["version"] >= fallback["doc"]["version"]):
                fallback = hit          # 无 run_id：保留最新的可用版本
    if fallback is None:
        return None
    fallback["content"] = Path(fallback["file"]).read_text(encoding="utf-8")
    return fallback


def _snippet(text: str, query: str, width: int = 140) -> str:
    """取关键词命中的上下文片段"""
    plain = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # 去图片
    plain = re.sub(r"`+", "", plain)
    pos = plain.lower().find(query.lower())
    if pos < 0:
        return plain[:width] + "…"
    start = max(0, pos - width // 2)
    return ("…" if start > 0 else "") + plain[start:start + width].replace("\n", " ") + "…"


# ---------------------------------------------------------------------------
# BM25 检索入口（索引进程内缓存，指纹变化自动重建）
# ---------------------------------------------------------------------------

_search_index = BM25Index()


def build_corpus(docs: List[Dict], scope_set: set) -> Dict[str, str]:
    """corpus key = f"{doc_id}:{scope}"，文本 = 标题(加权) + 正文"""
    corpus = {}
    for doc in docs:
        for scope in scope_set:
            art = doc["articles"].get(scope)
            if not art:
                continue
            try:
                text = Path(art["file"]).read_text(encoding="utf-8")
            except Exception:
                continue
            # 标题重复 3 次参与打分，提升标题命中权重
            corpus[f"{doc['doc_id']}:{scope}"] = f"{doc['title']}\n{doc['title']}\n{doc['title']}\n{text}"
    return corpus


def search_library(query: str, scope: str = "all", top_k: int = 10) -> Dict:
    """BM25 相关度检索，返回 top-k 命中（含摘要与分数）"""
    scope_set = set(ARTICLE_TYPES) if scope == "all" else ({scope} & set(ARTICLE_TYPES))
    docs = scan_library()
    corpus = build_corpus(docs, scope_set)
    hits = _search_index.search(corpus, query, top_k=top_k) if query.strip() else []

    by_key = {f"{d['doc_id']}:{sc}": (d, sc) for d in docs for sc in scope_set if sc in d["articles"]}
    results = []
    for key, score in hits:
        doc_id, sc = key.split(":", 1)
        doc, _ = by_key[key]
        art = doc["articles"][sc]
        text = Path(art["file"]).read_text(encoding="utf-8")
        results.append({
            "doc_id": doc_id,
            "run_id": doc.get("run_id", ""),
            "scope": sc,
            "label": ARTICLE_TYPES[sc][1],
            "title": doc["title"],
            "platform": doc["platform"],
            "platform_label": doc["platform_label"],
            "source_url": doc["source_url"],
            "video_key": doc["video_key"],
            "version_label": doc["version_label"],
            "version_count": doc["version_count"],
            "created_at": doc["created_at"],
            "score": score,
            "snippet": _snippet(text, query.strip()),
            "view_url": f"/report/{doc_id}",
        })
    return {"query": query, "scope": scope, "total": len(results), "results": results}


def list_library(scope: str = "all") -> Dict:
    """无关键词：返回全部文档索引（同一视频的多个版本各成条目）"""
    docs = scan_library()
    scope_set = set(ARTICLE_TYPES) if scope == "all" else ({scope} & set(ARTICLE_TYPES))
    results = []
    for doc in docs:
        for sc in scope_set & set(doc["articles"]):
            art = doc["articles"][sc]
            try:
                preview = Path(art["file"]).read_text(encoding="utf-8")[:120] + "…"
            except Exception:
                preview = ""
            results.append({
                "doc_id": doc["doc_id"], "run_id": doc.get("run_id", ""), "scope": sc,
                "label": ARTICLE_TYPES[sc][1],
                "title": doc["title"], "platform": doc["platform"],
                "platform_label": doc["platform_label"],
                "video_key": doc["video_key"],
                "version_label": doc["version_label"],
                "version_count": doc["version_count"],
                "created_at": doc["created_at"],
                "snippet": preview,
                "view_url": f"/report/{doc['doc_id']}",
            })
    return {"query": "", "scope": scope, "total": len(results), "results": results}


def list_videos() -> Dict:
    """文档库按视频聚合的索引：每个视频一张卡片，携带版本列表。"""
    videos = scan_videos()
    cards = []
    for v in videos:
        latest = v["versions"][-1]
        preview, latest_scope = "", None
        for scope in ("report", "outline", "detailed"):
            art = latest["articles"].get(scope)
            if art:
                try:
                    preview = Path(art["file"]).read_text(encoding="utf-8")[:120] + "…"
                    latest_scope = scope
                except Exception:
                    pass
                break
        cards.append({
            "video_key": v["video_key"],
            "title": v["title"],
            "platform": v["platform"],
            "platform_label": v["platform_label"],
            "source_url": v["source_url"],
            "version_count": v["version_count"],
            "latest_version": v["latest_version"],
            "latest_doc_id": v["latest_doc_id"],
            "latest_scope": latest_scope,
            "created_at": v["created_at"],
            "first_seen_at": v["first_seen_at"],
            "snippet": preview,
            "versions": [
                {
                    "doc_id": run["doc_id"],
                    "run_id": run.get("run_id", ""),
                    "version_label": run["version_label"],
                    "education_level": run["education_level"],
                    "created_at": run["created_at"],
                    "articles": [
                        {"scope": sc, "label": info["label"], "size": info["size"]}
                        for sc, info in run["articles"].items()
                    ],
                }
                for run in reversed(v["versions"])   # 最新版本在前
            ],
        })
    return {"query": "", "total": len(cards), "results": cards}


# ---------------------------------------------------------------------------
# 导出：单篇 / 整库
# ---------------------------------------------------------------------------

def export_article_zip(doc_id: str, scope: str, run_id: str = "") -> Optional[Tuple[bytes, str]]:
    """单篇导出（md + 该篇引用的 keyframes 图片打包）"""
    art = get_article(doc_id, scope, run_id)
    if not art:
        return None
    doc = art["doc"]
    content = art["content"]
    buf = BytesIO()
    base = f"videodevour_{doc_id[:8]}_{scope}"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base}.md", content)
        # 把引用到的本地图片一并打包
        for m in re.finditer(r"!\[[^\]]*\]\(((?!https?://|data:)[^)]+)\)", content):
            rel = m.group(1).replace("\\", "/").lstrip("./")
            img = Path(art["file"]).parent / rel
            if img.exists():
                zf.write(img, rel)
    safe = f"videodevour_{doc_id[:8]}_{scope}.zip"
    return buf.getvalue(), safe


def _safe_name(text: str, fallback: str = "video") -> str:
    """把标题变成安全的目录名（去掉路径分隔符、视频扩展名与控制字符）。"""
    cleaned = re.sub(r"\.(mp4|mkv|mov|webm|m4v|avi|flv|wmv)$", "", (text or "").strip(),
                     flags=re.IGNORECASE)
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:60] or fallback


def export_library_zip() -> Tuple[bytes, str]:
    """整库导出：按「视频/版本」组织——{标题}/{V1,V2…}/各篇.md + 关键帧。"""
    videos = scan_videos()
    buf = BytesIO()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"videodevour_library_{ts}.zip"
    manifest = {
        "exported_at": datetime.now().isoformat(),
        "total_videos": len(videos),
        "total_versions": sum(v["version_count"] for v in videos),
        "videos": [],
    }
    used_dirs = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for video in videos:
            base = _safe_name(video["title"], video["video_key"])
            if base in used_dirs:                      # 同名视频加后缀去重
                used_dirs[base] += 1
                base = f"{base}_{used_dirs[base]}"
            else:
                used_dirs[base] = 1
            entry = {
                "video_key": video["video_key"], "title": video["title"],
                "platform": video["platform"], "source_url": video["source_url"],
                "version_count": video["version_count"], "versions": [],
            }
            for run in video["versions"]:              # V1, V2… 升序
                doc_dir = f"{base}/{run['version_label']}"
                v_entry = {
                    "doc_id": run["doc_id"], "version": run["version_label"],
                    "education_level": run["education_level"],
                    "created_at": run["created_at"], "articles": {},
                }
                for scope, art in run["articles"].items():
                    label = ARTICLE_TYPES[scope][1]
                    arcname = f"{doc_dir}/{label}.md"
                    try:
                        zf.writestr(arcname, Path(art["file"]).read_text(encoding="utf-8"))
                        v_entry["articles"][scope] = {"label": label, "path": arcname}
                    except Exception as e:
                        logging.warning(f"整库导出：读取 {art['file']} 失败: {e}")
                kf = DATA_ROOT / "output" / run["dir"] / "keyframes"
                if kf.exists():
                    for img in sorted(kf.iterdir()):
                        if img.is_file():
                            zf.write(img, f"{doc_dir}/keyframes/{img.name}")
                entry["versions"].append(v_entry)
            manifest["videos"].append(entry)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buf.getvalue(), name
