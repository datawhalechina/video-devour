from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.algorithm import pipeline


class PipelinePerformanceTests(unittest.TestCase):
    def test_prepared_video_feeds_asr_and_direct_frames_with_real_stage_events(self):
        with tempfile.TemporaryDirectory() as td, ExitStack() as stack:
            target = str(Path(td, 'processing_video.mp4'))
            profile = dict(path=target, duration=12, original_bytes=100, size=20)
            prepare = stack.enter_context(patch.object(pipeline.video_handler, 'prepare_video',
                                                       return_value=profile, create=True))
            stack.enter_context(patch.object(pipeline, '_setup_environment', return_value=(td, 'v', 't')))
            stack.enter_context(patch.object(pipeline.settings_store, 'apply_to_config'))
            stack.enter_context(patch.object(pipeline.settings_store, 'load_settings', return_value={}))
            asr = stack.enter_context(patch.object(pipeline, '_run_asr_and_process',
                                                  return_value=[{'text': '讲解', 'start': 0, 'end': 12}]))
            stack.enter_context(patch.object(pipeline, '_generate_and_match_outline', return_value=(
                {'章节': [{'start': 0, 'end': 12}]}, [(2, '章节')], ['章节'], '## 章节')))
            cut = stack.enter_context(patch.object(pipeline.video_handler, 'cut_videos_by_headings'))
            direct = stack.enter_context(patch.object(pipeline.video_handler, 'extract_frames_by_headings'))
            for fn in ['generate_detailed_outline', 'generate_final_report', 'generate_detailed_report']:
                stack.enter_context(patch.object(pipeline.outline_handler, fn, return_value='outline.md'))
            stack.enter_context(patch.object(pipeline.image_processor, 'process_all_frames'))
            stack.enter_context(patch.object(pipeline.image_processor, 'select_keyframes_with_vlm', return_value={}))
            events, ready = [], []
            result = pipeline.run_full_pipeline('external.mov', education_level='自由学习',
                progress_callback=lambda *args: events.append(args),
                media_ready_callback=lambda *args: ready.append(args))
            prepare.assert_called_once()
            self.assertEqual(asr.call_args.args[0], target)
            self.assertEqual(direct.call_args.args[2], target)
            cut.assert_not_called()
            stages = [event[2] for event in events]
            self.assertLess(stages.index('preparing_video'), stages.index('asr'))
            self.assertLess(stages.index('asr'), stages.index('extracting_frames'))
            self.assertEqual(ready[0][0], profile)
            self.assertEqual(result['video_path'], target)
            self.assertTrue(Path(td, 'timing_report.json').exists())


if __name__ == '__main__':
    unittest.main()
