"""详细报告：高保真主报告 + 原文对照栏目（编号原文+译文），长章节分段不丢内容。

新契约（相对旧「逐章 原文+模板笔记」的重构）：
- 主报告 detailed_report.md：高保真正文，涉及原话处以上标 [N] 引用，无模板小节。
- 原文对照 transcript.md：逐 chunk 编号条目（原文 + 译文），与主报告 [N] 对应。
- 长章节：主报告分段生成后合并；原文在 transcript 中完整不丢。
"""
import re
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


class FakeLLM:
    """可控 LLM：按 prompt 类型返回不同内容，并记录是否收到翻译请求。"""

    instances = []

    def __init__(self, *a, **k):
        FakeLLM.instances.append(self)
        self.translate_calls = 0

    def get_response(self, prompt, system_message=""):
        if "逐条翻译" in prompt:                       # 原文对照的逐段翻译
            self.translate_calls += 1
            nums = re.findall(r"\[(\d+)\]", prompt)
            return "\n".join(f"[{n}] 译文{n}" for n in nums)
        if "合并为一段连贯" in prompt:                  # 长章节高保真合并
            return "合并后的高保真正文。"
        return "高保真正文，涉及原话处以 [1][2] 上标引用。"


class DetailedReportTests(unittest.TestCase):
    def setUp(self):
        FakeLLM.instances = []

    def _run(self, chunks_per_chapter, dialogue=None, outline=OUTLINE):
        """跑 generate_dedetailed_report，返回 (临时目录, 主报告内容)。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "detailed_outline.md").write_text(outline, encoding="utf-8")
            if dialogue is None:
                dialogue = _dialogue(sum(len(v) for v in chunks_per_chapter.values()))
            matched = {h: chunks for h, chunks in chunks_per_chapter.items()}
            with patch.object(outline_handler, "_build_mindmap", return_value=None), \
                 patch("backend.algorithm.llm_handler.LLMHandler", FakeLLM):
                out = outline_handler.generate_detailed_report(
                    str(root / "detailed_outline.md"), td, "自由学习",
                    headings_with_level=[(1, "主题"), (2, "第一章"), (2, "第二章")],
                    matched_data=matched, dialogue=dialogue)
            report = Path(out).read_text(encoding="utf-8")
            transcript = (root / outline_handler.TRANSCRIPT_FILE)
            transcript_text = transcript.read_text(encoding="utf-8") if transcript.exists() else ""
            return td, report, transcript_text

    def test_original_text_complete_in_transcript(self):
        """所有原文完整落在原文对照栏目，且主报告不再内嵌逐句原文。"""
        chunks = {"第一章": _dialogue(6), "第二章": []}
        _, report, transcript = self._run(chunks)
        for c in chunks["第一章"]:
            self.assertIn(c["text"], transcript)       # 原文对照完整
        self.assertNotIn("已截取", transcript)
        self.assertNotIn("…（本章原文过长", transcript)

    def test_every_dialogue_chunk_appears_exactly_once(self):
        """每个原文 chunk 在原文对照中恰好出现一次（编号条目，不重复）。"""
        chunks = {"第一章": _dialogue(3), "第二章": _dialogue(7)[3:]}
        _, _, transcript = self._run(chunks)
        for c in _dialogue(7):
            self.assertEqual(transcript.count(c["text"]), 1)

    def test_report_is_highfidelity_with_citations_no_template(self):
        """主报告是高保真正文、含 [N] 上标、无旧模板小节。"""
        chunks = {"第一章": _dialogue(4), "第二章": []}
        _, report, _ = self._run(chunks)
        self.assertIn("[1]", report)                    # 有上标引用（FakeLLM 输出）
        for tpl in ("本段主旨", "内容翻译", "结构化解读", "关键要点"):
            self.assertNotIn(tpl, report)

    def test_long_chapter_split_merged_not_cut(self):
        """长章节：原文在原文对照中完整不丢；主报告分段后合并。"""
        long_chunks = _dialogue(400)  # 约 8800 字，超过单次上限
        _, report, transcript = self._run({"第一章": long_chunks, "第二章": []})
        for c in long_chunks:                          # 原文对照不丢任何一句
            self.assertIn(c["text"], transcript)
        self.assertIn("合并后的高保真正文", report)      # 分段被合并

    def test_chinese_dialogue_skips_translation(self):
        """中文原话：不发起翻译请求，原文对照无「译文」行。"""
        chinese = [{"speaker": "S", "text": f"第{i}句中文原话，用于确认中文视频跳过翻译。",
                    "start": i * 10.0, "end": i * 10.0 + 9.0} for i in range(4)]
        _, _, transcript = self._run({"第一章": chinese, "第二章": []}, dialogue=chinese)
        self.assertEqual(sum(i.translate_calls for i in FakeLLM.instances), 0)
        self.assertNotIn("译文", transcript)

    def test_non_chinese_dialogue_keeps_translation(self):
        """英文原话：发起翻译，原文对照含译文。"""
        english = [{"speaker": "S", "text": f"Sentence {i} explains the concept in English.",
                    "start": i * 10.0, "end": i * 10.0 + 9.0} for i in range(4)]
        _, _, transcript = self._run({"第一章": english, "第二章": []}, dialogue=english)
        self.assertGreater(sum(i.translate_calls for i in FakeLLM.instances), 0)
        self.assertIn("译文", transcript)

    def test_notes_for_chapter_passes_translate_flag_when_split(self):
        """长章节分段时 translate 必须传给每段生成与合并（中文视频=False 不应被丢弃）。"""
        long_raw = "\n".join(
            f"[{i // 60:02d}:{i % 60:02d}] 第{i}句中文原话，足够长以触发分段。" * 4
            for i in range(150))
        captured = {"generate": [], "merge": []}

        def notes_impl(llm, raw, heading, level, translate=True):
            captured["generate"].append(translate)
            return "笔记"

        def merge_impl(llm, partials, heading, translate=True):
            captured["merge"].append(translate)
            return "合并"

        with patch.object(outline_handler, "_generate_chapter_notes",
                          side_effect=notes_impl), \
             patch.object(outline_handler, "_merge_chapter_notes",
                          side_effect=merge_impl):
            result = outline_handler._notes_for_chapter(
                None, long_raw, "第一章", "", translate=False)

        self.assertGreater(len(captured["generate"]), 1)   # 确实触发了分段
        self.assertEqual(result, "合并")
        self.assertFalse(any(captured["generate"]))        # 每段都应收到 translate=False
        self.assertEqual(captured["merge"], [False])       # 合并也应收到 translate=False


if __name__ == "__main__":
    unittest.main()
