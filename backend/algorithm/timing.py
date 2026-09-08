# -*- coding: utf-8 -*-
"""
处理耗时追踪（性能剖析）

为每个任务的每个阶段 / 每个关键函数记录耗时，输出结构化 JSON 与
人类可读摘要，便于定位优化点。

设计要点：
- 零侵入：用装饰器 / 上下文管理器包裹，不改变业务逻辑
- 线程安全：并发阶段（切分/抽帧/ASR 分段）各自累加，用锁保护
- 嵌套感知：支持阶段内嵌套函数计时，按层级记录
- 结果落盘：任务输出目录下 timing_report.json + timing_summary.txt
"""
import functools
import json
import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_lock = threading.Lock()


class TimingTracker:
    """单个任务的耗时追踪器"""

    def __init__(self, task_name: str = ""):
        self.task_name = task_name
        self.started_at = time.time()
        self.records: List[Dict] = []       # 完成记录（含嵌套 parent）
        self._stack = threading.local()     # 每线程独立的阶段栈
        self._open: Dict[int, Dict] = {}    # id(record) -> 进行中记录

    # ---------------- 内部：线程局部栈 ----------------
    def _stack_get(self) -> List[Dict]:
        if not hasattr(self._stack, "items"):
            self._stack.items = []
        return self._stack.items

    # ---------------- 记录 API ----------------
    @contextmanager
    def stage(self, name: str, category: str = "stage", **extra):
        """上下文管理器：记录一段耗时（可用于阶段或任意代码块）"""
        parent = self._stack_get()[-1]["name"] if self._stack_get() else None
        record = {
            "name": name,
            "category": category,
            "parent": parent,
            "start": time.time(),
            "thread": threading.current_thread().name,
            "extra": extra or {},
        }
        self._stack_get().append(record)
        try:
            yield record
        finally:
            self._stack_get().pop()
            record["duration"] = round(time.time() - record["start"], 3)
            record.pop("start", None)
            with _lock:
                self.records.append(record)

    def wrap(self, name: str, category: str = "function"):
        """装饰器：为函数计时（自动使用函数名）"""
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                with self.stage(name or fn.__name__, category=category):
                    return fn(*args, **kwargs)
            return wrapper
        return decorator

    # ---------------- 汇总 ----------------
    def summary(self) -> Dict:
        """按名称聚合（并发场景同一函数会多次出现，取总耗时/次数/最大单次）"""
        agg: Dict[str, Dict] = {}
        for r in self.records:
            key = r["name"]
            item = agg.setdefault(key, {
                "name": key, "category": r["category"],
                "count": 0, "total": 0.0, "max": 0.0, "min": None,
            })
            item["count"] += 1
            item["total"] = round(item["total"] + r["duration"], 3)
            item["max"] = max(item["max"], r["duration"])
            item["min"] = r["duration"] if item["min"] is None else min(item["min"], r["duration"])
        for item in agg.values():
            item["avg"] = round(item["total"] / item["count"], 3) if item["count"] else 0
        ordered = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
        total_elapsed = round(time.time() - self.started_at, 3)
        # 顶层阶段（parent 为 None）耗时占比
        top = [r for r in self.records if r["parent"] is None]
        return {
            "task_name": self.task_name,
            "generated_at": datetime.now().isoformat(),
            "total_elapsed": total_elapsed,
            "top_level_total": round(sum(r["duration"] for r in top), 3),
            "phases": ordered,
            "top_level": sorted(
                [{"name": r["name"], "duration": r["duration"],
                  "pct": round(r["duration"] / total_elapsed * 100, 1) if total_elapsed else 0}
                 for r in top],
                key=lambda x: x["duration"], reverse=True),
        }

    def write_reports(self, output_dir) -> Optional[Path]:
        """落盘 timing_report.json 与 timing_summary.txt"""
        output_dir = Path(output_dir)
        if not output_dir.exists():
            return None
        summary = self.summary()
        try:
            json_path = output_dir / "timing_report.json"
            json_path.write_text(
                json.dumps({"summary": summary, "records": self.records},
                           ensure_ascii=False, indent=2), encoding="utf-8")
            txt_path = output_dir / "timing_summary.txt"
            lines = [
                f"任务: {summary['task_name']}",
                f"总耗时: {summary['total_elapsed']}s",
                "",
                f"{'阶段/函数':<38} {'类别':<10} {'次数':>4} {'总耗时(s)':>10} {'平均(s)':>9} {'最大(s)':>9}",
                "-" * 88,
            ]
            for p in summary["phases"]:
                lines.append(
                    f"{p['name'][:37]:<38} {p['category']:<10} {p['count']:>4} "
                    f"{p['total']:>10.3f} {p['avg']:>9.3f} {p['max']:>9.3f}")
            lines += ["", "顶层阶段耗时占比："]
            for t in summary["top_level"]:
                lines.append(f"  {t['name'][:40]:<42} {t['duration']:>8.2f}s  {t['pct']:>5.1f}%")
            txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logging.info(f"耗时报告已保存: {json_path}")
            return json_path
        except Exception as e:
            logging.warning(f"耗时报告写入失败: {e}")
            return None


# ---------------- 全局当前任务追踪器 ----------------
_current: Optional[TimingTracker] = None
_current_lock = threading.Lock()


def start_tracking(task_name: str = "") -> TimingTracker:
    global _current
    with _current_lock:
        _current = TimingTracker(task_name)
        return _current


def current_tracker() -> Optional[TimingTracker]:
    return _current


@contextmanager
def track(name: str, category: str = "stage"):
    """便捷用法：若当前有追踪器则计时，否则空操作（零成本）"""
    tracker = _current
    if tracker is None:
        yield None
        return
    with tracker.stage(name, category=category) as rec:
        yield rec
