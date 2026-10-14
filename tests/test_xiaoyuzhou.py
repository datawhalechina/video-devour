# -*- coding: utf-8 -*-
"""小宇宙播客链接支持：平台识别 / 单集解析 / 音频直下 / 纯音频档案。"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.devour import video_downloader as vd  # noqa: E402


def _fake_page_html(eid="6123983acc5f215c6e0b7e6d", title="E01 测试单集",
                    audio="https://media.xyzcdn.net/TEST.m4a", duration=6348):
    episode = {
        "eid": eid,
        "title": title,
        "duration": duration,
        "pubDate": "2021-09-25T12:00:00.000Z",
        "shownotes": "<p><span>shownotes <b>测试</b>内容</span></p>",
        "enclosure": {"url": audio},
        "podcast": {
            "title": "无人知晓",
            "author": "孟岩",
            "image": {"picUrl": "https://image.xyzcdn.net/cover.jpg",
                      "middlePicUrl": "https://image.xyzcdn.net/cover.jpg@middle"},
        },
    }
    data = {"props": {"pageProps": {"episode": episode}}}
    return ('<html><head><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(data, ensure_ascii=False)
            + '</script></head><body></body></html>')


class _FakeResp:
    def __init__(self, text="", content=b"", headers=None):
        self.text = text
        self.content = content
        self.headers = headers or {}
        self.status_code = 200

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class XiaoyuzhouDetectTests(unittest.TestCase):
    def test_detect_platform(self):
        self.assertEqual(vd.detect_platform(
            "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d"), "xiaoyuzhou")
        self.assertEqual(vd.detect_platform(
            "https://xiaoyuzhoufm.com/podcast/67be80ac04e133067664a6de"), "xiaoyuzhou")
        self.assertEqual(vd.detect_platform(
            "https://www.bilibili.com/video/BV1nuap67E4L"), "bilibili")
        self.assertEqual(vd.detect_platform(
            "https://weixin.qq.com/sph/A2jF8l8Ac8"), "wechat")

    def test_extract_video_id(self):
        self.assertEqual(
            vd._extract_video_id(
                "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d",
                "xiaoyuzhou"),
            "6123983acc5f215c6e0b7e6d")
        # 频道页暂不支持展开，不应误返回 id
        self.assertIsNone(vd._extract_video_id(
            "https://www.xiaoyuzhoufm.com/podcast/67be80ac04e133067664a6de", "xiaoyuzhou"))


class XiaoyuzhouParseTests(unittest.TestCase):
    def test_episode_info(self):
        with mock.patch("requests.get", return_value=_FakeResp(_fake_page_html())):
            raw = vd._xyz_episode_info(
                "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d")
        self.assertEqual(raw["title"], "E01 测试单集")
        self.assertEqual(raw["uploader"], "无人知晓")
        self.assertEqual(raw["duration"], 6348)
        self.assertEqual(raw["audio"], "https://media.xyzcdn.net/TEST.m4a")
        self.assertEqual(raw["thumbnail"], "https://image.xyzcdn.net/cover.jpg@middle")
        self.assertEqual(raw["published_at"], "2021-09-25")
        # shownotes 去标签、压空白
        self.assertEqual(raw["description"], "shownotes 测试 内容")

    def test_probe_info_shape(self):
        with mock.patch("requests.get", return_value=_FakeResp(_fake_page_html())):
            info = vd.probe_video_info(
                "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d")
        self.assertEqual(info["platform"], "xiaoyuzhou")
        self.assertEqual(info["video_id"], "6123983acc5f215c6e0b7e6d")
        self.assertEqual(set(info.keys()), {
            "id", "title", "uploader", "duration", "thumbnail", "platform",
            "webpage_url", "video_id", "description", "published_at", "stats"})

    def test_missing_next_data_raises_value_error(self):
        with mock.patch("requests.get", return_value=_FakeResp("<html>empty</html>")):
            with self.assertRaises(ValueError):
                vd._xyz_episode_info(
                    "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d")


class XiaoyuzhouDownloadTests(unittest.TestCase):
    def test_download_writes_m4a(self):
        audio_bytes = b"\x00" * 20480  # 超过最小体积校验
        page = _FakeResp(_fake_page_html())
        stream = _FakeResp(content=audio_bytes,
                           headers={"Content-Length": str(len(audio_bytes))})
        events = []
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("requests.get", side_effect=[page, stream]):
                result = vd._download_xiaoyuzhou(
                    "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d",
                    tmp, progress_hook=lambda d: events.append(d))
            out = Path(result["file_path"])
            self.assertTrue(out.exists())
            self.assertEqual(out.suffix, ".m4a")
            self.assertEqual(out.read_bytes(), audio_bytes)
            self.assertEqual(result["info"]["platform"], "xiaoyuzhou")
        self.assertTrue(events and events[-1]["status"] == "downloading")

    def test_download_retries_on_network_error(self):
        """首次网络抖动应重试而不是直接失败。"""
        import requests as _requests
        audio_bytes = b"\x00" * 20480
        page = _FakeResp(_fake_page_html())
        stream = _FakeResp(content=audio_bytes,
                           headers={"Content-Length": str(len(audio_bytes))})
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("requests.get",
                            side_effect=[page, _requests.ConnectionError("boom"), stream]):
                with mock.patch("time.sleep"):
                    result = vd._download_xiaoyuzhou(
                        "https://www.xiaoyuzhoufm.com/episode/6123983acc5f215c6e0b7e6d",
                        tmp)
            self.assertEqual(Path(result["file_path"]).read_bytes(), audio_bytes)


@unittest.skipUnless(shutil.which("ffprobe"), "需要 ffprobe")
class AudioOnlyProfileTests(unittest.TestCase):
    """纯音频文件应返回 audio_only 档案并直通 prepare_video，而不是报错。"""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.audio = cls.root / 'sine.m4a'
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi',
             '-i', 'sine=frequency=440:duration=1.4',
             '-c:a', 'aac', str(cls.audio)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_probe_audio_only(self):
        from backend.algorithm import media_profile
        info = media_profile.probe_video(self.audio)
        self.assertTrue(info.get('audio_only'))
        self.assertTrue(info['has_audio'])
        self.assertIsNone(info['video_codec'])
        self.assertAlmostEqual(info['duration'], 1.4, delta=0.2)

    def test_prepare_audio_passthrough(self):
        from backend.algorithm import media_profile
        target = self.root / 'target.m4a'
        result = media_profile.prepare_video(self.audio, target)
        # 直通：不复制、不转码，路径即源文件
        self.assertEqual(result['profile'], 'audio-passthrough')
        self.assertEqual(Path(result['path']), self.audio)
        self.assertTrue(result.get('audio_only'))

    def test_probe_corrupt_rejected(self):
        from backend.algorithm import media_profile
        bad = self.root / 'bad.bin'
        bad.write_bytes(b'\x00' * 65536)
        with self.assertRaises(Exception):
            media_profile.probe_video(bad)


if __name__ == '__main__':
    unittest.main()
