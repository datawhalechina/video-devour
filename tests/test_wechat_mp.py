# -*- coding: utf-8 -*-
"""微信公众号发布：token 缓存/错误映射/Markdown 转换/封面生成/草稿链路。"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.publisher import wechat_mp as mp  # noqa: E402


def _credentials(appid="wx123", secret="s3cret"):
    """_get_credentials 的返回形状（非 settings.json 原始形状）"""
    return {"appid": appid, "secret": secret}


class TokenTests(unittest.TestCase):
    def setUp(self):
        mp._token_cache.clear()

    def _mock_token(self, resp):
        return mock.patch.object(mp.requests, "get",
                                  return_value=mock.Mock(json=mock.Mock(return_value=resp)))

    def test_token_cached(self):
        with self._mock_token({"access_token": "T1", "expires_in": 7200}):
            self.assertEqual(mp.get_access_token(), "T1")
        # 第二次命中缓存：不再发请求（get 抛异常即证明未调用）
        with mock.patch.object(mp.requests, "get", side_effect=AssertionError("不应再次请求")):
            self.assertEqual(mp.get_access_token(), "T1")

    def test_ip_whitelist_error(self):
        resp = {"errcode": 40164, "errmsg": "invalid ip 1.2.3.4 ipv6 x, not in whitelist rid x"}
        with self._mock_token(resp), \
             mock.patch.object(mp, "_get_credentials", return_value=_credentials()):
            with self.assertRaises(mp.WechatMpError) as ctx:
                mp.get_access_token()
            self.assertIn("IP 白名单", str(ctx.exception))
            self.assertIn("1.2.3.4", str(ctx.exception))

    def test_invalid_secret_error(self):
        with self._mock_token({"errcode": 40125, "errmsg": "invalid secret"}), \
             mock.patch.object(mp, "_get_credentials", return_value=_credentials()):
            with self.assertRaises(mp.WechatMpError) as ctx:
                mp.get_access_token()
            self.assertIn("AppSecret", str(ctx.exception))

    def test_missing_credentials_hint(self):
        with mock.patch.object(mp, "_get_credentials", side_effect=mp.WechatMpError("未配置")):
            with self.assertRaises(mp.WechatMpError) as ctx:
                mp.get_access_token()
            self.assertIn("未配置", str(ctx.exception))


class ApiCallTests(unittest.TestCase):
    def setUp(self):
        mp._token_cache.clear()

    def test_token_expired_retry_once(self):
        """40001 失效 → 强刷 token 重试成功"""
        mp._token_cache.update({"token": "OLD", "expires_at": 9999999999})
        responses = [
            mock.Mock(json=mock.Mock(return_value={"errcode": 40001})),   # 业务调用失败
            mock.Mock(json=mock.Mock(return_value={"errcode": 0, "total_count": 5})),             # 重试成功
        ]
        token_refresh = mock.Mock(json=mock.Mock(
            return_value={"access_token": "NEW", "expires_in": 7200}))
        with mock.patch.object(mp.requests, "request", side_effect=responses), \
             mock.patch.object(mp.requests, "get", return_value=token_refresh), \
             mock.patch.object(mp, "_get_credentials", return_value=_credentials()):
            self.assertEqual(mp.draft_count(), 5)

    def test_business_error_raised(self):
        mp._token_cache.update({"token": "T", "expires_at": 9999999999})
        bad = mock.Mock(json=mock.Mock(return_value={"errcode": 45002, "errmsg": "content size out of limit"}))
        with mock.patch.object(mp.requests, "request", return_value=bad):
            with self.assertRaises(mp.WechatMpError) as ctx:
                mp._api_call("POST", "/draft/add", json_body={})
            self.assertIn("精简", str(ctx.exception))


class MarkdownConvertTests(unittest.TestCase):
    def test_basic_conversion_inline_styles(self):
        html = mp.markdown_to_wechat_html(
            "# 标题\n\n> 引用一句\n\n正文 **加粗** 一段。\n\n## 小节\n\n- 要点一\n- 要点二\n")
        self.assertIn("<h1", html)
        self.assertIn("font-size:22px", html)
        self.assertIn("blockquote", html)
        self.assertIn("border-left:4px solid #1d4ed8", html)   # h2 样式
        self.assertIn("<section", html)                         # 根容器

    def test_mermaid_dropped(self):
        html = mp.markdown_to_wechat_html("文字\n\n```mermaid\ngraph TD; A-->B\n```\n\n更多")
        self.assertNotIn("mermaid", html)
        self.assertIn("更多", html)

    def test_images_resolved_and_missing_dropped(self):
        md = "![好图](frames_x/a.jpg)\n\n![缺图](frames_x/none.jpg)\n\n![外链](https://cdn.example.com/b.jpg)\n"
        html = mp.markdown_to_wechat_html(
            md, image_resolver=lambda p: "https://mmbiz.qpic.cn/A" if "a.jpg" in p else None)
        self.assertIn("https://mmbiz.qpic.cn/A", html)
        self.assertNotIn("none.jpg", html)
        self.assertNotIn("cdn.example.com", html)
        self.assertNotIn("__VD_IMG_", html)   # 占位符必须全部处理干净

    def test_content_over_limit_detected_in_publish(self):
        with mock.patch.object(mp, "upload_content_image"), \
             mock.patch.object(mp, "markdown_to_wechat_html",
                               return_value="x" * (mp._CONTENT_MAX_CHARS + 1)), \
             mock.patch.object(mp, "upload_thumb_material", return_value="THUMB"):
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
                f.write("# t\n\n内容")
                path = f.name
            try:
                with self.assertRaises(mp.WechatMpError) as ctx:
                    mp.publish_report_to_draft(path, title="超长")
                self.assertIn("超出", str(ctx.exception))
            finally:
                os.unlink(path)


class PublishFlowTests(unittest.TestCase):
    def _report(self, tmpdir):
        p = os.path.join(tmpdir, "final_report.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("# 会议纪要\n\n> 摘要行\n\n## 章节\n\nAllen 分享了架构经验。\n")
        return p

    def test_full_draft_flow(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            report = self._report(tmpdir)
            captured = {}

            def fake_cover(title, out_path):
                # 落一个真实文件（upload_thumb_material 会检查存在性）
                from PIL import Image
                Image.new("RGB", mp._THUMB_SIZE, "#2563eb").save(str(out_path), "JPEG")
                return str(out_path)

            def fake_api(method, path, **kw):
                captured[path] = (method, kw)
                if path == "/media/uploadimg":
                    return {"url": "https://mmbiz.qpic.cn/uploaded"}
                if path == "/material/add_material":
                    return {"thumb_media_id": "THUMB_1"}
                if path == "/draft/add":
                    return {"media_id": "DRAFT_9"}
                return {}

            mp._token_cache.update({"token": "T", "expires_at": 9999999999})
            with mock.patch.object(mp, "_api_call", side_effect=fake_api), \
                 mock.patch.object(mp, "generate_title_cover", side_effect=fake_cover):
                out = mp.publish_report_to_draft(report, title="测试会议纪要")
            self.assertEqual(out["media_id"], "DRAFT_9")
            method, kw = captured["/draft/add"]
            article = kw["json_body"]["articles"][0]
            self.assertEqual(article["title"], "测试会议纪要")
            self.assertEqual(article["thumb_media_id"], "THUMB_1")
            self.assertIn("<h1", article["content"])


class CoverGenerationTests(unittest.TestCase):
    def test_title_cover_generated(self):
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "cover.jpg")
            mp.generate_title_cover("AI+X碰个头·第二十四期", out)
            img = Image.open(out)
            self.assertEqual(img.size, mp._THUMB_SIZE)
            self.assertGreater(os.path.getsize(out), 5000)


if __name__ == "__main__":
    unittest.main()
