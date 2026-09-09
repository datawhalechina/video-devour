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
}

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


def scan_library() -> List[Dict]:
    """
    扫描 output/frames_* 目录，返回文档条目列表（以单次视频处理为单位）。

    每个条目：
    {
      doc_id, title, platform, platform_label, source_url,
      education_level, created_at,
      articles: {scope: {"file": 绝对路径, "name": 文件名, "mtime": ..., "size": ...}}
    }
    """
    docs: List[Dict] = []
    if not OUTPUT_DIR.exists():
        return docs
    for dir_path in OUTPUT_DIR.iterdir():
        if not (dir_path.is_dir() and dir_path.name.startswith("frames_")):
            continue
        parts = dir_path.name.split("_")
        if len(parts) < 2:
            continue
        doc_id = parts[1]
        meta = _load_task_meta(doc_id)
        source_url = meta.get("source_url") or ""
        platform = _detect_platform(source_url) if source_url else "upload"

        articles = {}
        for scope, (fname, label) in ARTICLE_TYPES.items():
            f = dir_path / fname
            if f.exists() and f.stat().st_size > 0:
                articles[scope] = {
                    "file": str(f), "name": fname, "label": label,
                    "mtime": f.stat().st_mtime, "size": f.stat().st_size,
                }
        if not articles:
            continue

        # 标题：优先任务记录文件名，其次详细报告的首个一级标题
        title = meta.get("filename") or ""
        if not title or title == doc_id:
            detail = dir_path / "detailed_report.md"
            src = detail if detail.exists() else dir_path / "detailed_outline.md"
            if src.exists():
                m = re.search(r"^#\s+(.+)", src.read_text(encoding="utf-8"), re.MULTILINE)
                title = m.group(1).strip() if m else doc_id
        title = title.replace("\n", " ")[:120]

        docs.append({
            "doc_id": doc_id,
            "dir": dir_path.name,
            "title": title,
            "platform": platform,
            "platform_label": PLATFORM_LABELS.get(platform, platform),
            "source_url": source_url,
            "education_level": meta.get("education_level") or "自由学习",
            "created_at": datetime.fromtimestamp(dir_path.stat().st_ctime).isoformat(),
            "articles": articles,
        })
    docs.sort(key=lambda d: d["created_at"], reverse=True)
    return docs


def get_article(doc_id: str, scope: str) -> Optional[Dict]:
    """获取单篇文章全文（md）"""
    label = ARTICLE_TYPES.get(scope, (None, scope))[1]
    for doc in scan_library():
        if doc["doc_id"] == doc_id:
            art = doc["articles"].get(scope)
            if not art:
                return None
            content = Path(art["file"]).read_text(encoding="utf-8")
            return {"doc": doc, "scope": scope, "label": label,
                    "content": content, "file": art["file"]}
    return None


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
            "scope": sc,
            "label": ARTICLE_TYPES[sc][1],
            "title": doc["title"],
            "platform": doc["platform"],
            "platform_label": doc["platform_label"],
            "source_url": doc["source_url"],
            "created_at": doc["created_at"],
            "score": score,
            "snippet": _snippet(text, query.strip()),
            "view_url": f"/report/{doc_id}",
        })
    return {"query": query, "scope": scope, "total": len(results), "results": results}


def list_library(scope: str = "all") -> Dict:
    """无关键词：返回全部文档索引"""
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
                "doc_id": doc["doc_id"], "scope": sc,
                "label": ARTICLE_TYPES[sc][1],
                "title": doc["title"], "platform": doc["platform"],
                "platform_label": doc["platform_label"],
                "created_at": doc["created_at"],
                "snippet": preview,
                "view_url": f"/report/{doc['doc_id']}",
            })
    return {"query": "", "scope": scope, "total": len(results), "results": results}


# ---------------------------------------------------------------------------
# 导出：单篇 / 整库
# ---------------------------------------------------------------------------

def export_article_zip(doc_id: str, scope: str) -> Optional[Tuple[bytes, str]]:
    """单篇导出（md + 该篇引用的 keyframes 图片打包）"""
    art = get_article(doc_id, scope)
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


def export_library_zip() -> Tuple[bytes, str]:
    """整库导出：按任务组织的全部文章 + manifest.json 索引"""
    docs = scan_library()
    buf = BytesIO()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"videodevour_library_{ts}.zip"
    manifest = {"exported_at": datetime.now().isoformat(), "total_docs": len(docs), "documents": []}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            entry = {
                "doc_id": doc["doc_id"], "title": doc["title"],
                "platform": doc["platform"], "source_url": doc["source_url"],
                "education_level": doc["education_level"],
                "created_at": doc["created_at"], "articles": {},
            }
            doc_dir = f"{doc['doc_id'][:8]}_{doc['platform']}"
            for scope, art in doc["articles"].items():
                label = ARTICLE_TYPES[scope][1]
                arcname = f"{doc_dir}/{label}.md"
                try:
                    zf.writestr(arcname, Path(art["file"]).read_text(encoding="utf-8"))
                    entry["articles"][scope] = {"label": label, "path": arcname}
                except Exception as e:
                    logging.warning(f"整库导出：读取 {art['file']} 失败: {e}")
            # 关键帧图片
            kf = DATA_ROOT / "output" / doc["dir"] / "keyframes"
            if kf.exists():
                for img in sorted(kf.iterdir()):
                    if img.is_file():
                        zf.write(img, f"{doc_dir}/keyframes/{img.name}")
            manifest["documents"].append(entry)
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return buf.getvalue(), name
