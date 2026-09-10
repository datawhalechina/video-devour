import unittest
from unittest.mock import patch
from backend.api import main


class PipelineProgressTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_forwards_real_stage_and_prepared_path(self):
        task_id = 'performance-test'
        snapshots = []

        def fake_pipeline(path, asr, level, **kwargs):
            self.assertTrue(kwargs['managed_source'])
            kwargs['progress_callback'](26, '视频压缩 75%', 'preparing_video')
            kwargs['media_ready_callback']({'path': 'prepared.mp4', 'size': 123})
            kwargs['progress_callback'](60, '章节抽帧 0/2', 'extracting_frames')
            return {'video_path': 'prepared.mp4'}

        with patch.dict(main.processing_tasks, {task_id: {'status': 'processing'}}, clear=True), \
             patch.object(main, 'save_tasks', side_effect=lambda: snapshots.append(dict(main.processing_tasks[task_id]))), \
             patch.object(main, 'run_full_pipeline', side_effect=fake_pipeline):
            await main.run_pipeline_with_progress('source.mov', task_id)
            self.assertTrue(any(s.get('message') == '视频压缩 75%' for s in snapshots))
            self.assertTrue(any(s.get('message') == '章节抽帧 0/2' for s in snapshots))
            self.assertEqual(main.processing_tasks[task_id]['file_path'], 'prepared.mp4')
            self.assertFalse(any(s.get('stage') == 'completed' for s in snapshots))


if __name__ == '__main__':
    unittest.main()
