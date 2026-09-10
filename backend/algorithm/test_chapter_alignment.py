"""Chapter boundary validation and local fallback; no model or network required."""
import unittest
from unittest.mock import patch

from backend.algorithm.chapter_alignment import (
    align_outline_chunks, extract_outline_alignment, normalize_outline_structure,
)


OUTLINE = "# 课程\n\n## 植物生长\n根系吸水，叶片进行光合作用。\n\n## 天文观测\n望远镜观测恒星和银河。\n"


def chunks(texts):
    return [dict(start=i * 10, end=(i + 1) * 10, speaker="讲师", text=text) for i, text in enumerate(texts)]


class ChapterAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.dialogue = chunks(["根系吸水", "叶片光合作用", "植物生长", "望远镜观测恒星", "银河"])

    def test_metadata_is_removed_from_saved_markdown(self):
        raw = OUTLINE + '<!-- chapter-map: [{"title":"植物生长","start_chunk_id":1},{"title":"天文观测","start_chunk_id":4}] -->'
        markdown, starts = extract_outline_alignment(raw)
        self.assertEqual(markdown, OUTLINE.strip())
        result = align_outline_chunks(markdown, self.dialogue, starts)
        self.assertEqual(result["植物生长"], self.dialogue[:3])
        self.assertEqual(result["天文观测"], self.dialogue[3:])
        self.assertEqual(result["课程"], [])

    def test_duplicate_titles_are_unique_and_metadata_tracks_occurrences(self):
        outline = "# 课程\n## 练习\n第一部分\n## 讲解\n第二部分\n## 练习\n第三部分"
        metadata = [dict(title=title, start_chunk_id=i + 1) for i, title in enumerate(["练习", "讲解", "练习"])]
        normalized, starts = normalize_outline_structure(outline, metadata)
        self.assertIn("## 练习（2）", normalized)
        self.assertEqual(starts[-1], dict(title="练习（2）", start_chunk_id=3))
        self.assertEqual(metadata[-1]["title"], "练习")  # 不原地修改调用方元数据
        dialogue = self.dialogue[:3]
        result = align_outline_chunks(normalized, dialogue, starts)
        self.assertEqual(result["练习"], dialogue[:1])
        self.assertEqual(result["练习（2）"], dialogue[2:])
        self.assertEqual(sum(result.values(), []), dialogue)
        self.assertEqual(normalize_outline_structure(normalized, starts), (normalized, starts))

    def test_unique_titles_also_avoid_existing_suffixes_and_h1(self):
        outline = "# 练习\n## 练习\n甲\n## 练习\n乙\n## 练习（2）\n丙"
        normalized, _ = normalize_outline_structure(outline, None)
        titles = [line.removeprefix("## ") for line in normalized.splitlines() if line.startswith("## ")]
        self.assertEqual(len(set(titles)), 3)
        self.assertNotIn("练习", titles)
        self.assertIn("## 练习（2）", normalized)

    def test_only_h1_gets_one_mapped_chapter_without_losing_body(self):
        outline = "# 课程\n\n唯一正文。\n\n- 要点"
        normalized, metadata = normalize_outline_structure(outline, None)
        self.assertIn("# 课程\n\n## 内容概述\n\n唯一正文。", normalized)
        self.assertIn("- 要点", normalized)
        result = align_outline_chunks(normalized, self.dialogue, metadata)
        self.assertEqual(result["课程"], [])
        self.assertEqual(result["内容概述"], self.dialogue)
        self.assertEqual(normalize_outline_structure(normalized, metadata), (normalized, metadata))

    def test_invalid_metadata_is_not_silently_repaired(self):
        outline = "# 课程\n## 练习\n甲\n## 练习\n乙"
        normalized, metadata = normalize_outline_structure(outline, [{"title": "其他", "start_chunk_id": 1}])
        self.assertEqual(metadata, [{"title": "其他", "start_chunk_id": 1}])
        self.assertEqual(sum(align_outline_chunks(normalized, self.dialogue, metadata).values(), []), self.dialogue)

    def test_invalid_mapping_falls_back_without_dropping_or_reordering_chunks(self):
        invalid_maps = [None, {}, [1, 4],
                        [{"title": "植物生长", "start_chunk_id": 2}, {"title": "天文观测", "start_chunk_id": 4}],
                        [{"title": "植物生长", "start_chunk_id": 1}, {"title": "天文观测", "start_chunk_id": 1}],
                        [{"title": "植物生长", "start_chunk_id": 1}, {"title": "天文观测", "start_chunk_id": 99}],
                        [{"title": "植物生长", "start_chunk_id": True}, {"title": "天文观测", "start_chunk_id": 4}],
                        [{"title": "不存在", "start_chunk_id": 1}, {"title": "天文观测", "start_chunk_id": 4}]]
        for metadata in invalid_maps:
            with self.subTest(metadata=metadata):
                result = align_outline_chunks(OUTLINE, self.dialogue, metadata)
                self.assertEqual(result["植物生长"], self.dialogue[:3])
                self.assertEqual(result["天文观测"], self.dialogue[3:])
                self.assertEqual(sum(result.values(), []), self.dialogue)

    def test_malformed_or_truncated_metadata_never_leaks(self):
        for suffix in ['<!-- chapter-map: {invalid} -->', '<!-- chapter-map: [{"title":']:
            markdown, starts = extract_outline_alignment(OUTLINE + suffix)
            self.assertEqual(markdown, OUTLINE.strip())
            self.assertIsNone(starts)

    def test_short_dialogue_and_empty_dialogue(self):
        result = align_outline_chunks(OUTLINE, self.dialogue[:1])
        self.assertEqual(sum(result.values(), []), self.dialogue[:1])
        self.assertEqual(sum(align_outline_chunks(OUTLINE, []).values(), []), [])

    def test_no_lexical_signal_is_deterministic_and_covers_every_chunk(self):
        dialogue = chunks(["xyz"] * 7)
        first = align_outline_chunks(OUTLINE, dialogue)
        self.assertEqual(first, align_outline_chunks(OUTLINE, dialogue))
        self.assertEqual(sum(first.values(), []), dialogue)
        self.assertTrue(first["植物生长"])
        self.assertTrue(first["天文观测"])

    def test_many_chapter_and_chunk_counts_preserve_coverage(self):
        for chapter_count in range(1, 9):
            outline = "# 课程\n" + "\n".join(f"## 章节 {i}\n讲义" for i in range(chapter_count))
            for chunk_count in range(1, 25):
                with self.subTest(chapters=chapter_count, chunks=chunk_count):
                    dialogue = chunks(["内容"] * chunk_count)
                    result = align_outline_chunks(outline, dialogue)
                    self.assertEqual(sum(result.values(), []), dialogue)
                    if chunk_count >= chapter_count:
                        self.assertTrue(all(result[f"章节 {i}"] for i in range(chapter_count)))

    def test_handler_uses_one_call_and_does_not_retain_stale_mapping(self):
        # 引导项目原有 config 别名；构造 handler 时绕过模型初始化，全部调用使用桩。
        from backend.algorithm import settings_store  # noqa: F401
        from backend.algorithm.llm_handler import LLMHandler
        handler = LLMHandler.__new__(LLMHandler)
        handler.education_level = "自由学习"
        handler.model = object()
        response = OUTLINE + '<!-- chapter-map: [{"title":"植物生长","start_chunk_id":1},{"title":"天文观测","start_chunk_id":4}] -->'
        with patch("backend.algorithm.llm_handler.ChatAgent"), patch.object(handler, "_call_with_retry", return_value=response) as call:
            self.assertEqual(handler.get_outline(self.dialogue), OUTLINE.strip())
            call.assert_called_once()
            prompt = call.call_args.args[1]
            self.assertIn("[chunk_id=1]", prompt)
            self.assertIn("[chunk_id=5]", prompt)
            self.assertEqual(handler.chapter_starts[1]["start_chunk_id"], 4)
        with patch("backend.algorithm.llm_handler.ChatAgent"), patch.object(handler, "_call_with_retry", return_value=OUTLINE):
            handler.get_outline(self.dialogue)
            self.assertIsNone(handler.chapter_starts)


if __name__ == "__main__":
    unittest.main()
