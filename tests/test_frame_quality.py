from pathlib import Path
import tempfile
import unittest

from backend.algorithm import settings_store
from backend.algorithm import image_processor


@unittest.skipUnless(image_processor.IMAGE_LIBS_AVAILABLE, 'image libraries unavailable')
class FrameQualityTests(unittest.TestCase):
    def test_deduplication_preserves_720p_readability(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as td:
            first = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(first, 'Readable slide text', (60, 150), cv2.FONT_HERSHEY_SIMPLEX,
                        2, (255, 255, 255), 3)
            for n, frame in [(1, first), (2, first), (3, np.full_like(first, 255))]:
                cv2.imwrite(str(Path(td, f'frame_{n:04d}.jpg')), frame)
            image_processor._process_single_directory(td)
            self.assertFalse(Path(td, 'frame_0002.jpg').exists())
            self.assertTrue(Path(td, 'frame_0003.jpg').exists())
            self.assertEqual(cv2.imread(str(Path(td, 'frame_0001.jpg'))).shape[:2], (720, 1280))


if __name__ == '__main__':
    unittest.main()
