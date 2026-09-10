"""衍生文体（量子速读/公众号/小红书）：取材约束、图片白名单、缓存复用。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.algorithm import settings_store  # noqa: F401  引导 sys.path，使 config 可导入
from backend.algorithm import style_articles


REPORT = (
    "# 演示视频\n\n"
    "> 一句话总结：这是结论。\n\n"
    "## 核心结论\n- 要点甲\n\n"
    "## 第一章\n![关键帧: 第一章](keyframes/01_a.jpg)\n\n正文。\n\n"
    "## 数据\n- 150ms：时延\n"
)


class StyleArticleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "final_report.md").write_text(REPORT, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)

    def _generate(self, scope, llm_output):
        with patch.object(style_articles, "LLMHandler") as handler:
            handler.return_value.get_response.return_value = llm_output
            return style_articles.generate_style(self.root, scope, "自由学习")

    def test_generates_file_for_each_style(self):
        for scope, (fname, label, _) in style_articles.STYLE_TYPES.items():
            path = self._generate(scope, f"# {label}\n\n正文。\n")
            self.assertEqual(path.name, fname)
            self.assertIn(label, path.read_text(encoding="utf-8"))

    def test_invented_images_are_stripped(self):
        # 成品里不能出现报告没有的关键帧链接（防止编造图片）
        out = self._generate(
            "wechat",
            "# 标题\n\n![编造图](keyframes/99_hallucinated.jpg)\n\n![真图](keyframes/01_a.jpg)\n\n正文。\n")
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("hallucinated", text)
        self.assertIn("keyframes/01_a.jpg", text)

    def test_all_images_stripped_when_report_has_none(self):
        (self.root / "final_report.md").write_text("# 无图视频\n\n只有文字。\n", encoding="utf-8")
        out = self._generate("xiaohongshu", "# 标题\n\n![任意](keyframes/x.jpg)\n\n正文。\n")
        self.assertNotIn("![", out.read_text(encoding="utf-8"))

    def test_result_is_cached_and_not_regenerated(self):
        first = self._generate("quantum", "# 首次\n\n内容。\n")
        mtime = first.stat().st_mtime_ns
        with patch.object(style_articles, "LLMHandler") as handler:
            again = style_articles.generate_style(self.root, "quantum", "自由学习")
            handler.return_value.get_response.assert_not_called()   # 命中缓存不再调用 LLM
        self.assertEqual(again, first)
        self.assertEqual(first.stat().st_mtime_ns, mtime)

    def test_code_fences_are_stripped(self):
        out = self._generate("quantum", "```markdown\n# 标题\n\n内容。\n```\n")
        text = out.read_text(encoding="utf-8")
        self.assertFalse(text.startswith("```"))
        self.assertNotIn("```", text)

    def test_missing_report_raises(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        with self.assertRaises(ValueError):
            style_articles.generate_style(empty, "quantum")

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            style_articles.generate_style(self.root, "nope")

    def test_prompts_share_fact_constraints(self):
        for scope, prompt in style_articles._PROMPTS.items():
            self.assertIn("取材约束", prompt, scope)
            self.assertIn("__REPORT__", prompt, scope)


if __name__ == "__main__":
    unittest.main()
