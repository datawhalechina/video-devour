"""Offline checks for bounded download selection and immutable cache snapshots."""
import inspect
import itertools
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp import YoutubeDL

from backend.devour import download_cache, video_downloader


def video(format_id, height, codec="avc1.64001f", audio=False):
    return {"format_id": format_id, "url": f"https://example.invalid/{format_id}",
            "ext": "mp4", "height": height, "width": height * 16 // 9,
            "vcodec": codec, "acodec": "mp4a.40.2" if audio else "none",
            "fps": 30, "tbr": height}


class DownloadFormatTests(unittest.TestCase):
    def select(self, formats):
        options = video_downloader._download_format_options(720)
        with YoutubeDL({**options, "quiet": True, "no_warnings": True}) as ydl:
            info = {"formats": formats}
            ydl.sort_formats(info)
            selected = ydl._select_formats(info["formats"], ydl.build_format_selector(options["format"]))
        return selected[0]["format_id"]

    def test_default_is_720(self):
        self.assertEqual(inspect.signature(video_downloader.download_video).parameters["max_height"].default, 720)

    def test_prefers_h264_within_720_limit(self):
        formats = [video("1080", 1080), video("720av1", 720, "av01.0.05M.08"),
                   video("720h264", 720), {"format_id": "audio", "url": "https://example.invalid/a",
                   "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2", "abr": 128}]
        self.assertEqual(self.select(formats), "720h264+audio")

    def test_can_use_non_h264_when_no_h264_under_limit(self):
        self.assertEqual(self.select([video("1080", 1080, audio=True),
                                     video("720av1", 720, "av01.0.05M.08", True)]), "720av1")

    def test_no_low_resolution_uses_smallest_available(self):
        self.assertEqual(self.select([video("4k", 2160, audio=True),
                                     video("1080", 1080, audio=True)]), "1080")

    def test_low_resolution_combined_beats_high_resolution_split(self):
        self.assertEqual(self.select([video("1080", 1080, audio=True), video("4k", 2160),
                                     {"format_id": "audio", "url": "https://example.invalid/a",
                                      "ext": "m4a", "vcodec": "none", "acodec": "mp4a.40.2"}]), "1080")

    def test_silent_video_has_a_usable_fallback(self):
        self.assertEqual(self.select([video("1080", 1080), video("720", 720)]), "720")

    def test_missing_height_does_not_prevent_download(self):
        unknown = video("unknown", 480, audio=True)
        unknown.pop("height")
        unknown.pop("width")
        self.assertEqual(self.select([unknown]), "unknown")


_addr_seq = itertools.count()


def addr(width, height, size=1000, url=None):
    # 每次生成唯一 URL：同一 URL 会被候选去重，复用会让用例失去意义
    return {"url_list": [url or f"https://example.invalid/v{next(_addr_seq)}"],
            "width": width, "height": height, "data_size": size}


class DouyinAppCandidateTests(unittest.TestCase):
    """抖音 App 接口兜底：H.264 候选筛选与画质取舍（web 接口被签名校验拦截后启用）。"""

    def pick(self, video, max_height=720):
        return video_downloader._douyin_app_pick_video(
            video_downloader._douyin_app_h264_candidates(video), max_height)

    def test_h265_bitrate_entries_are_skipped(self):
        # bit_rate 里的 H.265 档会 403，必须排除；仅有 H.264 顶层源可用
        video = {
            "is_h265": 0,
            "bit_rate": [{"is_h265": 1, "gear_name": "720_1_1", "play_addr": addr(720, 1080)}],
            "play_addr_h264": addr(540, 810),
        }
        self.assertEqual([c["height"] for c in video_downloader._douyin_app_h264_candidates(video)], [810])

    def test_top_level_h265_play_addr_is_ignored(self):
        video = {"is_h265": 1, "play_addr": addr(720, 1080), "play_addr_h264": addr(540, 810)}
        urls = [c["url"] for c in video_downloader._douyin_app_h264_candidates(video)]
        self.assertNotIn(addr(720, 1080)["url_list"][0], urls)

    def test_prefers_highest_tier_within_cap(self):
        video = {"is_h265": 0, "play_addr_h264": addr(540, 810),
                 "download_addr": addr(720, 720)}
        picked = self.pick(video, 720)
        self.assertEqual((picked["width"], picked["height"]), (720, 720))

    def test_falls_back_to_lowest_tier_when_all_exceed_cap(self):
        video = {"is_h265": 0, "play_addr_h264": addr(1080, 1920),
                 "play_addr": addr(720, 1280)}
        picked = self.pick(video, 480)
        self.assertEqual(picked["height"], 1280)

    def test_same_tier_prefers_clean_source(self):
        video = {"is_h265": 0, "play_addr_h264": addr(720, 1280, size=10),
                 "download_addr": addr(720, 720, size=10)}
        picked = self.pick(video, 720)
        self.assertFalse(picked["watermark"])
        self.assertEqual(picked["height"], 1280)

    def test_portrait_tier_uses_short_side(self):
        # 竖屏 720x1280 与横屏 1280x720 应视为同一档（短边 720）
        video = {"is_h265": 0, "play_addr_h264": addr(720, 1280)}
        self.assertEqual(video_downloader._douyin_app_h264_candidates(video)[0]["tier"], 720)

    def test_no_candidates_returns_none(self):
        self.assertIsNone(self.pick({"is_h265": 1, "bit_rate": []}))

    def test_clean_preference_env_switches_away_from_higher_watermarked_tier(self):
        # 默认按档位取 720p（可能带水印）；置环境变量后改为优先无水印源
        video = {"is_h265": 0, "play_addr_h264": addr(540, 810, size=100),
                 "download_addr": addr(720, 720, size=296)}
        self.assertEqual(self.pick(video, 720)["tier"], 720)
        with patch.dict(os.environ, {"VIDEO_DEVOUR_DOUYIN_CLEAN": "1"}):
            picked = self.pick(video, 720)
        self.assertEqual(picked["tier"], 540)
        self.assertFalse(picked["watermark"])

    def test_deduplicates_identical_urls(self):
        same = addr(540, 810)
        video = {"is_h265": 0, "play_addr": same, "play_addr_h264": same}
        self.assertEqual(len(video_downloader._douyin_app_h264_candidates(video)), 1)

    def test_app_detail_raises_actionable_error_without_detail(self):
        class Resp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"status_code": None}
        with patch("requests.get", return_value=Resp()) as get:
            with self.assertRaises(ValueError) as ctx:
                video_downloader._douyin_app_detail("123", "sessionid=x")
        # 缺 Cookie/失效时必须带配置指引，而不是裸的接口异常
        self.assertIn("Cookie", str(ctx.exception))
        # App 接口依赖 App UA：换成 web UA 会返回空体
        self.assertEqual(get.call_args.kwargs["headers"]["User-Agent"],
                         video_downloader._DOUYIN_APP_UA)

    def test_app_download_without_cookie_gives_cookie_guidance(self):
        with patch.object(video_downloader, "_load_douyin_cookies_header", return_value=""):
            with self.assertRaises(ValueError) as ctx:
                video_downloader._download_douyin_app("123", tempfile.mkdtemp())
        self.assertIn("抖音 cookies", str(ctx.exception))


class CacheProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patch = patch.object(download_cache, "_data_root", return_value=self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.tmp.cleanup)
        self.url = "https://example.invalid/video"
        self.original = self.root / "original.mp4"
        self.original.write_bytes(b"old" * 100_000)

    def test_register_does_not_modify_materialized_hard_links(self):
        download_cache.register(self.url, str(self.original))
        task = self.root / "task.mp4"
        download_cache.materialize(self.url, task)
        compressed = self.root / "compressed.mp4"
        compressed.write_bytes(b"compressed" * 20_000)
        entry = download_cache.register(self.url, str(compressed))
        self.assertEqual(task.read_bytes(), self.original.read_bytes())
        self.assertEqual(Path(entry["file_path"]).read_bytes(), compressed.read_bytes())

    def test_failed_replacement_preserves_previous_cache(self):
        entry = download_cache.register(self.url, str(self.original))
        compressed = self.root / "compressed.mp4"
        compressed.write_bytes(b"replacement")
        def partial_copy(src, dest):
            Path(dest).write_bytes(b"partial")
            raise OSError("disk full")
        with patch.object(download_cache.os, "link", side_effect=OSError("cross-device")), \
                patch.object(download_cache.shutil, "copy2", side_effect=partial_copy):
            with self.assertRaises(OSError):
                download_cache.register(self.url, str(compressed))
        self.assertEqual(Path(entry["file_path"]).read_bytes(), self.original.read_bytes())

    def test_small_valid_compressed_file_is_reusable_and_profile_is_saved(self):
        compressed = self.root / "compressed.mp4"
        compressed.write_bytes(b"tiny-valid-video")
        profile = {"height": 720, "fps": 10, "vcodec": "h264"}
        download_cache.register(self.url, str(compressed), processing_profile=profile)
        entry = download_cache.lookup(self.url)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["processing_profile"], profile)

    def test_materializing_onto_cache_itself_preserves_file(self):
        entry = download_cache.register(self.url, str(self.original))
        self.assertIsNotNone(download_cache.materialize(self.url, entry["file_path"]))
        self.assertTrue(Path(entry["file_path"]).exists())

    def test_register_shares_storage_and_preserves_metadata(self):
        entry = download_cache.register(self.url, str(self.original),
                                        info={"id": "video123", "title": "Original title", "uploader": "Author"})
        self.assertEqual(Path(entry["file_path"]).stat().st_ino, self.original.stat().st_ino)
        compressed = self.root / "compressed.mp4"
        compressed.write_bytes(b"compressed")
        updated = download_cache.register(self.url, str(compressed), info={"title": "New title"})
        self.assertEqual(updated["video_id"], "video123")
        self.assertEqual(updated["title"], "New title")
        self.assertEqual(updated["uploader"], "Author")
        self.assertEqual(Path(updated["file_path"]).stat().st_ino, compressed.stat().st_ino)
        self.assertTrue(self.original.exists())

    def test_failed_materialize_preserves_existing_target(self):
        download_cache.register(self.url, str(self.original))
        target = self.root / "existing.mp4"
        target.write_bytes(b"existing")
        with patch.object(download_cache.os, "link", side_effect=OSError("cross-device")), \
                patch.object(download_cache.shutil, "copy2", side_effect=OSError("disk full")):
            self.assertIsNone(download_cache.materialize(self.url, target))
        self.assertEqual(target.read_bytes(), b"existing")

    def test_truncated_registered_file_is_not_reused(self):
        entry = download_cache.register(self.url, str(self.original))
        Path(entry["file_path"]).write_bytes(b"truncated")
        self.assertIsNone(download_cache.lookup(self.url))

    def test_new_container_releases_obsolete_cache_link(self):
        webm = self.root / "original.webm"
        webm.write_bytes(b"original-webm")
        old = download_cache.register(self.url, str(webm))
        updated = download_cache.register(self.url, str(self.original))
        self.assertFalse(Path(old["file_path"]).exists())
        self.assertTrue(webm.exists())
        self.assertTrue(Path(updated["file_path"]).exists())


if __name__ == "__main__":
    unittest.main()
