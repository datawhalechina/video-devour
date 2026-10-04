# -*- coding: utf-8 -*-
"""HTML 速读页（speedread）离线测试：草稿解析 / 组件渲染 / 外层围栏剥离 / 导出。"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.devour import html_export
from backend.devour.html_speedread import parse_draft, render_sheet

# style_articles → llm_handler 依赖 config 模块：先由 settings_store 引导
# （config.py 缺失时注册内置默认模块，详见 settings_store.apply_to_config）
from backend.algorithm import settings_store as _settings_store
_settings_store.apply_to_config()


DRAFT = """---
title: 测试速读页
subtitle: 副标题
cols: 3
source: 某UP主 · B站
---
导语：一句核心结论。

## A 核心结论 {span=2 meta="v1"}
```callout ok 结论
设备不是门槛，**持续输出**才是。
```

## B 脉络
```timeline v
00:00 | 开场 | 引入问题
03:20 | 方法 | *关键一步*
```

## C 数字 {bare}
```limits
月更 | 4 / 20 | 条
```

## D 路径
```flow
(开始) -> 拍摄: 先完成
拍摄 -> {数据好?}
```

## E 分类
```tree
`1` 口播 | 观点密度
`2` 记录 | 门槛低
```

## F 元信息 {bare}
```kv
UP主: 某人
* 一句话: 先拍起来
```

## G 对比
| 维度 | 快 | 慢 |
|---|---|---|
| 启动 | ok 立刻 | no 拖延 |
"""


class ParseTests(unittest.TestCase):
    def test_frontmatter_and_intro(self):
        doc = parse_draft(DRAFT)
        self.assertEqual(doc["title"], "测试速读页")
        self.assertEqual(doc["subtitle"], "副标题")
        self.assertEqual(doc["cols"], 3)
        self.assertEqual(doc["meta"]["source"], "某UP主 · B站")
        self.assertEqual(doc["intro"], "导语：一句核心结论。")

    def test_panel_attrs(self):
        doc = parse_draft(DRAFT)
        first = doc["panels"][0]
        self.assertEqual((first["id"], first["span"], first["meta"]), ("A", 2, "v1"))
        bare = [p for p in doc["panels"] if p["title"] == "数字"]
        self.assertTrue(bare and bare[0]["bare"])

    def test_english_title_not_eaten_as_id(self):
        doc = parse_draft("## CPU 的发展\n- x")
        self.assertEqual(doc["panels"][0]["id"], "A")
        self.assertEqual(doc["panels"][0]["title"], "CPU 的发展")

    def test_explicit_id(self):
        doc = parse_draft("## B 显式\n- x")
        self.assertEqual((doc["panels"][0]["id"], doc["panels"][0]["title"]),
                         ("B", "显式"))


class RenderTests(unittest.TestCase):
    html = render_sheet(DRAFT)

    def test_page_shell(self):
        self.assertIn("<title>测试速读页</title>", self.html)
        self.assertIn('data-mode="auto"', self.html)
        self.assertIn("am-sheet", self.html)
        self.assertIn("am-ruler", self.html)

    def test_components_rendered(self):
        for token in ("am-callout am-callout--ok", "am-timeline--v",
                      "am-tl-item--hi", "am-lim-fill", "am-fnode--pill",
                      "am-fnode--diamond", "am-tree-tag", "am-kv-cell--wide",
                      "am-status--ok", "am-status--no"):
            self.assertIn(token, self.html, token)

    def test_span_and_bold(self):
        self.assertIn("grid-column: span 2", self.html)
        self.assertIn("<strong>持续输出</strong>", self.html)

    def test_image_embedded_as_data_uri(self):
        from PIL import Image
        import io
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            img_dir = tmp / "keyframes"
            img_dir.mkdir()
            Image.new("RGB", (1200, 800), "steelblue").save(img_dir / "f1.jpg", "JPEG")
            draft = "## A 配图\n![第一帧](keyframes/f1.jpg)\n"
            html = render_sheet(draft, output_dir=tmp)
            self.assertIn("data:image/jpeg;base64,", html)
            self.assertNotIn('src="keyframes/', html)

    def test_missing_local_image_rendered_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = render_sheet("## A 配图\n![缺图](keyframes/nope.jpg)\n",
                                output_dir=Path(tmp))
            self.assertNotIn("<img", html)     # 本地缺图不渲染，防裂图


class StyleIntegrationTests(unittest.TestCase):
    """generate_speedread_html：mock LLM，验证草稿→HTML 落盘与外层围栏剥离。"""

    def test_generate_speedread_html(self):
        from backend.algorithm import style_articles
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "final_report.md").write_text(
                "# 测试视频\n\n## 结论\n- 要点一\n\n![关键帧](keyframes/f1.jpg)\n",
                encoding="utf-8")
            fake_draft = (
                "```markdown\n---\ntitle: 围栏包裹的稿\n---\n## A 结论\n"
                "```callout ok 结论\n内容。\n```\n```\n")
            with patch.object(style_articles.LLMHandler, "get_response",
                              return_value=fake_draft):
                out = style_articles.generate_speedread_html(tmp)
            self.assertTrue(out.exists())
            html = out.read_text(encoding="utf-8")
            # 外层 ```markdown 剥掉，但组件围栏渲染成 callout 而非纯文本
            self.assertIn("<title>围栏包裹的稿</title>", html)
            self.assertIn("am-callout am-callout--ok", html)
            self.assertNotIn("```callout", html)
            # 草稿同步落盘，便于排查
            self.assertTrue((tmp / "speedread_draft.md").exists())

    def test_draft_without_panels_rejected(self):
        from backend.algorithm import style_articles
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "final_report.md").write_text("# t\n正文", encoding="utf-8")
            with patch.object(style_articles.LLMHandler, "get_response",
                              return_value="没有任何面板的输出"):
                with self.assertRaises(ValueError):
                    style_articles.generate_speedread_html(tmp)


class ExportTests(unittest.TestCase):
    def test_find_browser_returns_path_or_none(self):
        result = html_export.find_browser()
        self.assertTrue(result is None or Path(result).exists())

    def test_export_png_and_pdf(self):
        browser = html_export.find_browser()
        if not browser:
            self.skipTest("本机无 Chrome/Chromium，跳过导出测试")
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            page.write_text(render_sheet("## A 结论\n- 要点\n"), encoding="utf-8")
            png = html_export.export_png(page, Path(tmp) / "p.png")
            pdf = html_export.export_pdf(page, Path(tmp) / "p.pdf")
            self.assertGreater(Path(png).stat().st_size, 10_000)
            self.assertGreater(Path(pdf).stat().st_size, 5_000)


if __name__ == "__main__":
    unittest.main()
