"""文档库：按视频聚合存储 + 同视频多次处理存为 V1/V2…，可按版本打开内容。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.algorithm import document_library


def _write_run(root: Path, task_id: str, stamp: str, filename: str, body: str,
               source_url: str = "", video_key: str = ""):
    d = root / f"frames_{task_id}_{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "final_report.md").write_text(body, encoding="utf-8")
    (d / "detailed_outline.md").write_text(f"# 大纲 {body}", encoding="utf-8")
    (d / "detailed_report.md").write_text(f"# 详细 {body}", encoding="utf-8")
    return d


class LibraryVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "output").mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.patch_out = patch.object(document_library, "OUTPUT_DIR", self.root / "output")
        self.patch_root = patch.object(document_library, "DATA_ROOT", self.root)
        self.patch_out.start()
        self.patch_root.start()
        self.addCleanup(self.patch_out.stop)
        self.addCleanup(self.patch_root.stop)

    def _tasks(self, mapping):
        (self.root / "tasks.json").write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    def test_same_video_multiple_runs_are_grouped_as_versions(self):
        self._tasks({
            "tid1": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T09:00:00"},
            "tid2": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T10:00:00"},
        })
        _write_run(self.root / "output", "tid1", "20260910_090000", "课程.mp4", "第一次", "https://x/v")
        _write_run(self.root / "output", "tid2", "20260910_100000", "课程.mp4", "第二次", "https://x/v")

        videos = document_library.scan_videos()
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["version_count"], 2)
        self.assertEqual([r["version_label"] for r in videos[0]["versions"]], ["V1", "V2"])
        self.assertTrue(videos[0]["versions"][0]["run_id"])
        self.assertNotEqual(videos[0]["versions"][0]["run_id"],
                            videos[0]["versions"][1]["run_id"])

    def test_different_videos_stay_separate(self):
        self._tasks({
            "a": {"filename": "甲.mp4", "source_url": "https://x/a", "video_key": "vkA",
                  "created_at": "2026-09-10T09:00:00"},
            "b": {"filename": "乙.mp4", "source_url": "https://x/b", "video_key": "vkB",
                  "created_at": "2026-09-10T09:00:00"},
        })
        _write_run(self.root / "output", "a", "20260910_090000", "甲.mp4", "甲内容", "https://x/a")
        _write_run(self.root / "output", "b", "20260910_090100", "乙.mp4", "乙内容", "https://x/b")
        self.assertEqual(len(document_library.scan_videos()), 2)

    def test_article_scope_by_run_id_returns_that_version(self):
        # 同一任务重复处理会留下多个输出目录（真实场景：同 doc_id、不同 run_id）
        self._tasks({
            "tid1": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T10:00:00"},
        })
        _write_run(self.root / "output", "tid1", "20260910_090000", "课程.mp4", "第一次版本内容", "https://x/v")
        _write_run(self.root / "output", "tid1", "20260910_100000", "课程.mp4", "第二次版本内容", "https://x/v")

        video = document_library.get_video("vk1")
        by_label = {r["version_label"]: r for r in video["versions"]}
        v1, v2 = by_label["V1"], by_label["V2"]
        first = document_library.get_article("tid1", "report", v1["run_id"])
        second = document_library.get_article("tid1", "report", v2["run_id"])
        self.assertIn("第一次版本内容", first["content"])
        self.assertIn("第二次版本内容", second["content"])
        self.assertEqual(first["doc"]["version_label"], "V1")
        self.assertEqual(second["doc"]["version_label"], "V2")
        # 不带 run_id 时取最新版本
        latest = document_library.get_article("tid1", "report")
        self.assertIn("第二次版本内容", latest["content"])

    def test_list_videos_exposes_version_chain_and_latest_articles(self):
        self._tasks({
            "tid1": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T09:00:00"},
            "tid2": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T10:00:00"},
        })
        _write_run(self.root / "output", "tid1", "20260910_090000", "课程.mp4", "旧", "https://x/v")
        _write_run(self.root / "output", "tid2", "20260910_100000", "课程.mp4", "新", "https://x/v")
        data = document_library.list_videos()
        self.assertEqual(data["total"], 1)
        card = data["results"][0]
        self.assertEqual(card["version_count"], 2)
        self.assertEqual(card["latest_version"], 2)
        # 最新版本在前，且携带各篇文章
        self.assertEqual([v["version_label"] for v in card["versions"]], ["V2", "V1"])
        scopes = {a["scope"] for a in card["versions"][0]["articles"]}
        self.assertEqual(scopes, {"outline", "report", "detailed"})

    def test_export_library_zip_is_organized_by_video_and_version(self):
        import io
        import zipfile
        self._tasks({
            "tid1": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T09:00:00"},
            "tid2": {"filename": "课程.mp4", "source_url": "https://x/v", "video_key": "vk1",
                     "created_at": "2026-09-10T10:00:00"},
        })
        _write_run(self.root / "output", "tid1", "20260910_090000", "课程.mp4", "一", "https://x/v")
        _write_run(self.root / "output", "tid2", "20260910_100000", "课程.mp4", "二", "https://x/v")
        content, name = document_library.export_library_zip()
        self.assertTrue(name.endswith(".zip"))
        zf = zipfile.ZipFile(io.BytesIO(content))
        names = zf.namelist()
        self.assertIn("manifest.json", names)
        self.assertTrue(any(n.startswith("课程/V1/") for n in names), names)
        self.assertTrue(any(n.startswith("课程/V2/") for n in names), names)
        manifest = json.loads(zf.read("manifest.json"))
        self.assertEqual(manifest["total_videos"], 1)
        self.assertEqual(manifest["total_versions"], 2)


if __name__ == "__main__":
    unittest.main()
