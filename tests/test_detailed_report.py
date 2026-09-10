"""详细报告：原文完整不截断、长章节分段合并、思维导图落盘。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.algorithm import settings_store  # noqa: F401  引导 sys.path，使 config 可导入
from backend.algorithm import outline_handler


def _dialogue(n):
    return [{"speaker": "S", "text": f"第{i}句话，讲述一个足够长的内容片段用于测试。",
             "start": i * 10.0, "end": i * 10.0 + 9.0} for i in range(n)]


OUTLINE = "# 主题\n\n## 第一章\n概述。\n\n## 第二章\n概述。\n"


class DetailedReportTests(unittest.TestCase):
    def _run(self, chunks_per_chapter, notes_impl, outline=OUTLINE, dialogue=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "detailed_outline.md").write_text(outline, encoding="utf-8")
            if dialogue is None:
                dialogue = _dialogue(sum(len(v) for v in chunks_per_chapter.values()))
            matched = {h: chunks for h, chunks in chunks_per_chapter.items()}
            with patch.object(outline_handler, "_build_mindmap", return_value=None), \
                 patch.object(outline_handler, "_generate_chapter_notes",
                              side_effect=notes_impl), \
                 patch.object(outline_handler, "_merge_chapter_notes",
                              side_effect=lambda llm, parts, h, *a: "合并:" + "|".join(parts)):
                out = outline_handler.generate_detailed_report(
                    str(root / "detailed_outline.md"), td, "自由学习",
                    headings_with_level=[(1, "主题"), (2, "第一章"), (2, "第二章")],
                    matched_data=matched, dialogue=dialogue)
            return Path(out).read_text(encoding="utf-8")

    def test_original_text_is_complete_without_truncation_marker(self):
        chunks = {"第一章": _dialogue(6), "第二章": []}
        content = self._run(chunks, lambda llm, raw, heading, level, *a: "笔记")
        for c in chunks["第一章"]:
            self.assertIn(c["text"], content)
        self.assertNotIn("已截取", content)
        self.assertNotIn("…（本章原文过长", content)

    def test_every_dialogue_chunk_appears_exactly_once(self):
        chunks = {"第一章": _dialogue(3), "第二章": _dialogue(7)[3:]}
        content = self._run(chunks, lambda llm, raw, heading, level, *a: "笔记")
        for c in _dialogue(7):
            self.assertEqual(content.count(c["text"]), 1)

    def test_long_chapter_is_split_merged_not_cut(self):
        long_chunks = _dialogue(400)  # 约 8800 字，超过单次上限
        seen = []

        def notes_impl(llm, raw, heading, level, *a):
            seen.append(raw)
            return f"笔记({len(raw)})"

        content = self._run({"第一章": long_chunks, "第二章": []}, notes_impl)
        self.assertGreater(len(seen), 1)          # 确实分段生成
        self.assertIn("合并:", content)            # 分段结果被合并
        joined = "".join(seen)
        for c in long_chunks:                     # 分段没有丢内容
            self.assertIn(c["text"], joined)

    def test_chinese_dialogue_skips_translation_section(self):
        """中文原话不应出现「内容翻译」小节，笔记只保留主旨/解读/要点。"""
        chinese = [{"speaker": "S", "text": f"第{i}句中文原话，用于确认中文视频跳过翻译。",
                    "start": i * 10.0, "end": i * 10.0 + 9.0} for i in range(4)]
        captured = {}

        def notes_impl(llm, raw, heading, level, translate=True):
            captured["translate"] = translate
            return "笔记"

        content = self._run({"第一章": chinese, "第二章": []}, notes_impl, dialogue=chinese)
        self.assertFalse(captured["translate"])
        self.assertNotIn("内容翻译", content)

    def test_non_chinese_dialogue_keeps_translation_section(self):
        """英文原话必须保留「内容翻译」（逐句翻译为中文）。"""
        english = [{"speaker": "S", "text": f"Sentence {i} explains the concept in English.",
                    "start": i * 10.0, "end": i * 10.0 + 9.0} for i in range(4)]
        captured = {}

        def notes_impl(llm, raw, heading, level, translate=True):
            captured["translate"] = translate
            return "笔记"

        self._run({"第一章": english, "第二章": []}, notes_impl, dialogue=english)
        self.assertTrue(captured["translate"])


if __name__ == "__main__":
    unittest.main()
