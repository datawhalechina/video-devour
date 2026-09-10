"""Markdown → PDF 渲染：中文可读、结构完整、图片可嵌入、Mermaid 转为要点。"""
import tempfile
import unittest
from pathlib import Path

from backend.algorithm import pdf_export


class PdfExportTests(unittest.TestCase):
    def _pdf(self, md, **kw):
        return pdf_export.markdown_to_pdf(md, **kw)

    def test_renders_chinese_headings_and_paragraph(self):
        pdf = self._pdf("# 中文标题\n\n这是正文段落，包含 English 术语与数字 150ms。\n")
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 800)

    def test_renders_lists_quote_table_and_code(self):
        md = (
            "# 报告\n\n## 章节\n\n> 引用说明\n\n"
            "- 要点一\n- 要点二\n  - 子要点\n\n"
            "| 方案 | 时延 |\n| --- | --- |\n| MicroVM | 150ms |\n\n"
            "```python\nprint('hi')\n```\n"
        )
        pdf = self._pdf(md)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_mermaid_mindmap_becomes_readable_bullets(self):
        md = (
            "# 报告\n\n## 内容思维导图\n\n```mermaid\n"
            "mindmap\n  root((主题))\n    分支A\n      要点1\n    分支B\n"
            "```\n"
        )
        pdf = self._pdf(md)
        self.assertTrue(pdf.startswith(b"%PDF"))
        # Mermaid 源码不应以原文形式出现：解析后转为要点
        bullets = pdf_export._mermaid_to_bullets("mindmap\n  root((主题))\n    分支A")
        self.assertEqual([label for _, label in bullets], ["主题", "分支A"])
        self.assertLess(bullets[0][0], bullets[1][0])   # 根节点层级浅于分支

    def test_image_is_embedded_when_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "keyframes").mkdir()
            # 用 reportlab 生成一张极小的 PNG
            from reportlab.lib.utils import ImageReader
            import io
            from PIL import Image
            img_path = root / "keyframes" / "01_图.png"
            Image.new("RGB", (80, 60), (120, 160, 110)).save(img_path)
            md = "# 报告\n\n![关键帧](keyframes/01_图.png)\n"
            pdf = self._pdf(md, base_dir=root)
            import re
            self.assertTrue(re.search(rb"/Subtype\s*/Image", pdf))

    def test_missing_image_does_not_break_rendering(self):
        pdf = self._pdf("# 报告\n\n![关键帧](keyframes/不存在.jpg)\n\n正文。\n")
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_safe_pdf_name_handles_chinese_and_symbols(self):
        name = pdf_export.safe_pdf_name("AI Agent沙箱？/与虚拟机:区别", "详细报告")
        self.assertTrue(name.endswith("_详细报告.pdf"))
        self.assertNotIn("/", name)
        self.assertNotIn(":", name)


if __name__ == "__main__":
    unittest.main()
