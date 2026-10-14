"""HTML 速读页：草稿解析容错与页头渲染（frontmatter 漏 ---、URL 缩短、图片块级）。"""
import unittest

from backend.algorithm import settings_store  # noqa: F401  引导 sys.path，使 config 可导入
from backend.devour import html_speedread


DRAFT_NO_OPEN_FENCE = """title: 测试**视频**速读
subtitle: 一页看懂
cols: 3

导语：核心结论一句话。

## A 核心结论

- 要点一
"""


class ParseDraftTests(unittest.TestCase):
    def test_frontmatter_without_leading_fence(self):
        """LLM 漏写开头 --- 时，frontmatter 仍应被识别，不能漏进导语。"""
        doc = html_speedread.parse_draft(DRAFT_NO_OPEN_FENCE)
        self.assertEqual(doc["title"], "测试视频速读")   # ** 强调符已剥离
        self.assertEqual(doc["subtitle"], "一页看懂")
        self.assertEqual(doc["cols"], 3)
        self.assertNotIn("title:", doc["intro"])
        self.assertNotIn("cols:", doc["intro"])
        self.assertNotIn("导语：", doc["intro"])          # 标签本身不露出
        self.assertEqual(doc["intro"], "核心结论一句话。")
        self.assertEqual(len(doc["panels"]), 1)

    def test_frontmatter_with_fence_still_works(self):
        draft = "---\ntitle: 标题\ncols: 4\n---\n\n## A 面板\n\n正文\n"
        doc = html_speedread.parse_draft(draft)
        self.assertEqual(doc["title"], "标题")
        self.assertEqual(doc["cols"], 4)
        self.assertEqual(doc["panels"][0]["id"], "A")

    def test_leading_kv_without_frontmatter_keys_not_swallowed(self):
        """开头恰好是「单词:」的普通文本（无 title/subtitle/cols）不应被当 frontmatter 吃掉。"""
        draft = "Note: 这是一段正文。\n\n## A 面板\n\n内容\n"
        doc = html_speedread.parse_draft(draft)
        self.assertEqual(doc["title"], "视频速读")
        self.assertIn("Note:", doc["intro"])


class RenderSheetTests(unittest.TestCase):
    def test_head_shortens_url_and_wraps_subtitle(self):
        draft = ("---\ntitle: 标题\nsubtitle: 副标题\nsource: 某UP主 · B站\n---\n\n"
                 "导语：一句话。\n\n## A 面板\n\n正文\n")
        html = html_speedread.render_sheet(
            draft, meta={"来源": "https://www.bilibili.com/video/BV1xx/?buvid=abc&mid=xyz"})
        self.assertIn('class="am-sub"', html)
        # 完整 URL（含跟踪参数）只保留在 href；显示文本是去参短链
        self.assertIn('href="https://www.bilibili.com/video/BV1xx/?buvid=abc&amp;mid=xyz"', html)
        self.assertIn(">https://www.bilibili.com/video/BV1xx</a>", html)
        self.assertIn('target="_blank"', html)

    def test_standalone_image_not_nested_in_paragraph(self):
        draft = ("---\ntitle: t\n---\n\n## A 面板\n\n前置段落\n\n"
                 "![说明](keyframes/01_a.jpg)\n\n后置段落\n")
        html = html_speedread.render_sheet(draft)
        self.assertNotIn("<p><figure", html)
        self.assertIn("前置段落", html)

    def test_theme_is_rounded_not_blueprint(self):
        """主题换装后：不再输出蓝图风的 0 圆角 / 标尺。"""
        html = html_speedread.render_sheet("---\ntitle: t\n---\n\n## A 面板\n\n正文\n")
        self.assertIn("--radius: 14px", html)
        self.assertIn(".am-ruler { display: none; }", html)

    def test_first_panel_is_full_width_lead(self):
        """阅读动线：第一个面板固定全宽导览区（绿白主题核心结构）。"""
        draft = ("---\ntitle: t\n---\n\n## 核心结论\n\n结论\n\n"
                 "## B 细节\n\n细节\n\n## C 其他\n\n其他\n")
        html = html_speedread.render_sheet(draft)
        self.assertIn('class="am-panel am-panel--lead" style="grid-column: 1 / -1;"', html)
        self.assertIn("--accent: #1d7a46", html)          # 绿白配色（浅色）
        self.assertNotIn("🌙", html)                        # 图标用 SVG，不用 emoji
        self.assertIn("<svg", html)


if __name__ == "__main__":
    unittest.main()
