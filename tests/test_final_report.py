"""精简报告：结构（结论先行/数据速查）与重复小节合并。"""
import unittest

from backend.algorithm import settings_store  # noqa: F401  引导 sys.path，使 config 可导入
from backend.algorithm.outline_handler import (
    _consolidate_data_section, _FINAL_REPORT_PROMPT, _inline_outline_images,
)


class FinalReportPromptTests(unittest.TestCase):
    def test_prompt_anchors_facts_to_raw_excerpts(self):
        # 事实必须取自原话，否则会退化成「概括的概括」
        self.assertIn("匹配的文本片段", _FINAL_REPORT_PROMPT)
        self.assertIn("唯一的事实来源", _FINAL_REPORT_PROMPT)

    def test_prompt_forbids_filler_and_requires_specifics(self):
        self.assertIn("严禁空泛套话", _FINAL_REPORT_PROMPT)
        self.assertIn("数字、名称、步骤、机制、对比或明确结论", _FINAL_REPORT_PROMPT)
        self.assertIn("不要写\"元描述\"", _FINAL_REPORT_PROMPT)

    def test_prompt_defines_value_first_structure(self):
        for section in ("一句话总结", "## 核心结论", "关键数据与术语"):
            self.assertIn(section, _FINAL_REPORT_PROMPT)


class OutlineImageRestorationTests(unittest.TestCase):
    OUTLINE = (
        "# T\n\n## 第一章\n![关键帧: 第一章](keyframes/01_x.jpg)\n\n"
        "## 第二章\n![关键帧: 第二章](keyframes/02_y.jpg)\n"
    )

    def test_broken_image_alt_is_replaced_with_outline_images(self):
        # LLM 可能把图片 alt 写坏（甚至写成字幕行），必须以大纲为准还原
        report = ("# T\n\n## 第一章\n![00:00 - 00:37] SPEAKER_spk0\n\n正文一。\n\n"
                  "## 第二章\n正文二。\n")
        out = _inline_outline_images(self.OUTLINE, report)
        self.assertIn("![关键帧: 第一章](keyframes/01_x.jpg)", out)
        self.assertIn("![关键帧: 第二章](keyframes/02_y.jpg)", out)   # 漏图也补回
        self.assertNotIn("SPEAKER_spk0", out)
        self.assertEqual(out.count("!["), 2)

    def test_body_text_and_other_sections_are_preserved(self):
        report = "# T\n\n## 第一章\n正文甲。\n- 要点甲\n\n## 关键数据与术语\n- 150ms：时延\n"
        out = _inline_outline_images(self.OUTLINE, report)
        for kept in ("正文甲。", "- 要点甲", "## 关键数据与术语", "- 150ms：时延"):
            self.assertIn(kept, out)


class DataSectionConsolidationTests(unittest.TestCase):
    def test_duplicate_data_sections_merge_into_single_trailing_section(self):
        md = (
            "# 标题\n\n> 一句话总结：X\n\n"
            "## 核心结论\n- 结论一\n\n"
            "## 第一章\n正文。\n- 要点A\n\n"
            "## 关键数据与术语\n- 150ms：P99 时延\n- Micro VM：极简内核虚拟机\n\n"
            "## 第二章\n正文。\n- 要点B\n\n"
            "## 关键数据与术语\n- 150ms：P99 时延\n- 几MB：内存开销\n"
        )
        out = _consolidate_data_section(md)
        self.assertEqual(out.count("## 关键数据与术语"), 1)
        self.assertEqual(out.count("150ms"), 1)                       # 去重
        self.assertTrue(out.strip().endswith("几MB：内存开销"))        # 统一收尾
        for kept in ("## 核心结论", "## 第一章", "## 第二章", "- 要点A", "- 要点B"):
            self.assertIn(kept, out)

    def test_single_data_section_is_moved_to_end(self):
        md = "# T\n\n## 关键数据与术语\n- 5ms：示例\n\n## 后一节\n正文。\n"
        out = _consolidate_data_section(md)
        self.assertEqual(out.count("## 关键数据与术语"), 1)
        self.assertTrue(out.strip().endswith("- 5ms：示例"))

    def test_no_data_section_leaves_markdown_untouched(self):
        md = "# T\n\n## A\n正文。\n"
        self.assertEqual(_consolidate_data_section(md), md)


if __name__ == "__main__":
    unittest.main()
