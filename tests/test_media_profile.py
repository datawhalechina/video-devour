import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class MediaProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / 'source.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'testsrc2=size=1920x1080:rate=30:duration=1.4',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1.4',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-threads', '2',
                        '-c:a', 'aac', '-shortest', str(cls.source)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_normalizes_video_preserving_audio_duration_and_source(self):
        from backend.algorithm import media_profile
        before = self.source.read_bytes()
        target = self.root / 'prepared.mp4'
        events = []
        result = media_profile.prepare_video(self.source, target, progress=events.append)
        info = media_profile.probe_video(target)
        self.assertEqual((info['width'], info['height'], info['fps']), (1280, 720, 10))
        self.assertEqual(info['video_codec'], 'h264')
        self.assertTrue(info['has_audio'])
        self.assertLess(abs(info['duration'] - 1.4), .2)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result['path'], str(target))
        self.assertEqual(events[-1], 1.0)
        mtime = target.stat().st_mtime_ns
        again = media_profile.prepare_video(target, target)
        self.assertTrue(again['reused'])
        self.assertEqual(target.stat().st_mtime_ns, mtime)

    def test_compression_does_not_inflate_high_bitrate_source(self):
        """压缩产物必须小于原文件，否则"压缩"反而撑大存储。"""
        from backend.algorithm import media_profile
        target = self.root / 'smaller.mp4'
        result = media_profile.prepare_video(self.source, target)
        self.assertLess(result['size'], result['original_bytes'])
        self.assertNotIn('fallback', result)

    def test_falls_back_to_source_when_encoding_cannot_shrink(self):
        """编码结果始终大于原文件时保留原件并标注 fallback，不写更大的文件。"""
        from unittest.mock import patch
        from backend.algorithm import media_profile
        target = self.root / 'guarded.mp4'
        original_bytes = self.source.stat().st_size

        def fake_run(command, duration, progress=None):
            # 模拟一个压不小的编码器：写出比原文件更大的结果
            Path(command[-1]).write_bytes(b'x' * (original_bytes + 1024))

        with patch.object(media_profile, 'run_ffmpeg', side_effect=fake_run):
            result = media_profile.prepare_video(self.source, target)
        self.assertEqual(result['fallback'], 'encode-not-smaller')
        self.assertEqual(result['size'], original_bytes)
        self.assertEqual(target.stat().st_size, original_bytes)
        self.assertEqual(target.read_bytes(), self.source.read_bytes())


if __name__ == '__main__':
    unittest.main()
