from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.algorithm import settings_store  # 引导 legacy config
from backend.algorithm import video_handler


class DirectFramesTests(unittest.TestCase):
    def test_direct_extraction_seeks_before_input_and_has_no_video_intermediate(self):
        headings = [(1, '总标题'), (2, '开头'), (2, '末尾')]
        matched = {'开头': [{'start': 0, 'end': 1}],
                   '末尾': [{'start': 355, 'end': 358}]}
        calls = []

        def ffmpeg(cmd, *args, **kwargs):
            calls.append(cmd)
            Path(cmd[-1].replace('%04d', '0001')).write_bytes(b'frame')

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(video_handler, 'run_ffmpeg', side_effect=ffmpeg, create=True):
                dirs = video_handler.extract_frames_by_headings(
                    headings, matched, 'input.mp4', tmp, duration=400)
            self.assertEqual(len(dirs), 2)
            self.assertFalse((Path(tmp) / 'videocut').exists())
            self.assertTrue((Path(tmp) / 'chapters.json').exists())
            for cmd in calls:
                self.assertLess(cmd.index('-ss'), cmd.index('-i'))
                self.assertIn('-t', cmd)
                self.assertNotIn('libx264', cmd)


if __name__ == '__main__':
    unittest.main()
