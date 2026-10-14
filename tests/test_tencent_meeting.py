# -*- coding: utf-8 -*-
"""腾讯会议数据源：平台识别 / 输入解析 / 短链抽取 / 转写转换 / 录制筛选 / 极速模式跳帧。"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.devour import video_downloader as vd  # noqa: E402
from backend.devour import tencent_meeting as tm  # noqa: E402

# 昨天实测落地的真实转写（AI+X碰个头·第24期，236 段）
_REAL_FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "test-data", "tencent-meeting", "AI+X碰个头-24",
    "transcript_2109971748627333121.json",
)


def _mini_minutes():
    """内联的最小转写结构（与 transcript-get 的 data.minutes 同形）"""
    return {
        "lang": "zh",
        "keywords": ["测试"],
        "paragraphs": [
            {
                "start_time": "00:00", "end_time": "00:24",
                "speaker": {"user_name": "Allen"},
                "sentences": [{"words": [{"text": "牛马吧。"}]},
                              {"words": [{"text": "呃，我今天的选题是让ai写代码。"}]}],
            },
            {
                "start_time": "00:24", "end_time": "00:26",
                "speaker": {"user_name": "Datawhale"},
                "sentences": [{"words": [{"text": "好的，非常欢迎。"}]}],
            },
            {   # 无文本段落应被过滤
                "start_time": "00:26", "end_time": "00:27",
                "speaker": {"user_name": "X"},
                "sentences": [{"words": []}],
            },
        ],
    }


class DetectPlatformTests(unittest.TestCase):
    def test_detect_platform(self):
        for path in ("crm", "cw", "ctm", "ct"):
            self.assertEqual(
                vd.detect_platform(f"https://meeting.tencent.com/{path}/2MYYqPy94b"),
                "tencent_meeting", f"/{path}/ 短链应识别为 tencent_meeting")
        # 不与其它平台混淆
        self.assertEqual(vd.detect_platform("https://www.bilibili.com/video/BV1nuap67E4L"), "bilibili")
        self.assertEqual(vd.detect_platform("https://weixin.qq.com/sph/A2jF8l8Ac8"), "wechat")

    def test_extract_video_id(self):
        self.assertEqual(
            vd._extract_video_id("https://meeting.tencent.com/crm/2MYYqPy94b", "tencent_meeting"),
            "2MYYqPy94b")
        self.assertIsNone(vd._extract_video_id("https://meeting.tencent.com/", "tencent_meeting"))


class ParseRefTests(unittest.TestCase):
    def test_url_forms(self):
        ref = tm.parse_meeting_ref("https://meeting.tencent.com/crm/2MYYqPy94b")
        self.assertEqual(ref["kind"], "url")
        self.assertEqual(ref["value"], "2MYYqPy94b")

    def test_meeting_code(self):
        self.assertEqual(tm.parse_meeting_ref("60669290755"),
                         {"kind": "meeting_code", "value": "60669290755"})
        # 太短/太长不算会议号
        self.assertIsNone(tm.parse_meeting_ref("12345"))
        self.assertIsNone(tm.parse_meeting_ref("123456789012345678901"))

    def test_meeting_id(self):
        self.assertEqual(tm.parse_meeting_ref("3010812525270541781"),
                         {"kind": "meeting_id", "value": "3010812525270541781"})

    def test_invalid(self):
        self.assertIsNone(tm.parse_meeting_ref(""))
        self.assertIsNone(tm.parse_meeting_ref("随便一段文字"))


class ShortLinkResolveTests(unittest.TestCase):
    def test_extract_from_ssr_page(self):
        # cw 回放页 RSC 数据是 \x 转义引号形式
        html = ('<script>self.__next_f.push([1,"17:[\\"$\\",\\"$L18\\",null,{\\"data\\":'
                '{\\"meeting_code\\":\\"60669290755\\",\\"meeting_id\\":\\"3010812525270541781\\"}"])</script>')
        fake = mock.Mock(text=html)
        with mock.patch.object(tm.requests, "get", return_value=fake) as m:
            out = tm._resolve_short_link("2MYYqPy94b")
        self.assertEqual(out["meeting_code"], "60669290755")
        self.assertEqual(out["meeting_id"], "3010812525270541781")
        # 统一改请求 /cw/（crm 是 JS 跳转壳，无数据）
        self.assertIn("/cw/2MYYqPy94b", m.call_args.args[0])

    def test_plain_json_form(self):
        html = '<script id="__NEXT_DATA__">{"meeting_code":"60669290755","meeting_id":"3010812525270541781"}</script>'
        with mock.patch.object(tm.requests, "get", return_value=mock.Mock(text=html)):
            out = tm._resolve_short_link("xxx")
        self.assertEqual(out["meeting_code"], "60669290755")

    def test_no_data_returns_none(self):
        # 无权限的 ct 页：字段存在但为空 → 视为解析失败
        html = '{"meeting_code":"","meeting_id":""}'
        with mock.patch.object(tm.requests, "get", return_value=mock.Mock(text=html)):
            self.assertIsNone(tm._resolve_short_link("xxx"))

    def test_request_error_returns_none(self):
        with mock.patch.object(tm.requests, "get", side_effect=tm.requests.RequestException("boom")):
            self.assertIsNone(tm._resolve_short_link("xxx"))


class TranscriptConvertTests(unittest.TestCase):
    def test_ts_to_seconds(self):
        self.assertEqual(tm._ts_to_seconds("00:24"), 24.0)
        self.assertEqual(tm._ts_to_seconds("02:15:03"), 2 * 3600 + 15 * 60 + 3)
        self.assertEqual(tm._ts_to_seconds(""), 0.0)
        self.assertEqual(tm._ts_to_seconds("bad"), 0.0)

    def test_dialogue_shape(self):
        dialogue = tm.transcript_to_dialogue(_mini_minutes())
        self.assertEqual(len(dialogue), 2)  # 空文本段落被过滤
        self.assertEqual(dialogue[0]["start"], 0.0)
        self.assertEqual(dialogue[0]["end"], 24.0)
        # 形状对齐 ASRProcessor v2 产物：speaker 独立字段（实名），text 为纯内容
        self.assertEqual(dialogue[0]["speaker"], "Allen")
        self.assertIn("让ai写代码", dialogue[0]["text"])
        self.assertNotIn("Allen:", dialogue[0]["text"])
        self.assertEqual(dialogue[1]["speaker"], "Datawhale")

    def test_real_fixture_smoke(self):
        """真实转写 fixture（存在时才跑）：236 段全覆盖、末段时长正确"""
        if not os.path.exists(_REAL_FIXTURE):
            self.skipTest("真实转写 fixture 不存在")
        data = json.load(open(_REAL_FIXTURE, encoding="utf-8"))
        minutes = data["data"]["minutes"]
        dialogue = tm.transcript_to_dialogue(minutes)
        self.assertEqual(len(dialogue), len([p for p in minutes["paragraphs"]
                                             if "".join(w.get("text", "") for s in p.get("sentences", [])
                                                         for w in s.get("words", [])).strip()]))
        self.assertGreater(dialogue[-1]["end"], 2 * 3600)  # 02:15:03 结束


class PickRecordTests(unittest.TestCase):
    def _meta(self, records):
        return {"subject": "AI+X碰个头", "meeting_id": "3010812525270541781", "records": records}

    def test_filters_and_sorts(self):
        records = [
            {"meeting_record_id": "r1", "permission_status": "can_apply", "type": "文字转写",
             "record_file_id": "f1", "subject": "转写_1"},   # 无权限：剔除
            {"meeting_record_id": "r2", "permission_status": "can_view", "type": "文字转写",
             "record_file_id": "f2", "subject": "转写_2"},   # 直连：排前
            {"meeting_record_id": "r3", "permission_status": "can_view", "type": "云录制",
             "record_file_id": "", "subject": "第二十四期"},  # 需下钻：排后
        ]
        picked = tm._pick_record_file_ids(self._meta(records))
        self.assertEqual(picked[0]["record_file_id"], "f2")
        self.assertFalse(picked[0].get("need_address", False))
        self.assertEqual(picked[1]["meeting_record_id"], "r3")
        self.assertTrue(picked[1].get("need_address"))

    def test_no_viewable_raises(self):
        records = [{"meeting_record_id": "r1", "permission_status": "can_apply",
                    "type": "文字转写", "record_file_id": "f1", "subject": "s"}]
        with self.assertRaises(tm.TencentMeetingError) as ctx:
            tm._pick_record_file_ids(self._meta(records))
        self.assertIn("无查看权限", str(ctx.exception))

    def test_no_records_raises(self):
        with self.assertRaises(tm.TencentMeetingError):
            tm._pick_record_file_ids(self._meta([]))


class CliErrorMappingTests(unittest.TestCase):
    def test_not_installed_hint(self):
        with mock.patch.object(tm.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(tm.TencentMeetingError) as ctx:
                tm._run_tmeet("auth", "status")
            self.assertIn("npm install -g", str(ctx.exception))

    def test_auth_error_hint(self):
        proc = mock.Mock(returncode=1, stdout="", stderr="Error: please auth login first")
        with mock.patch.object(tm.subprocess, "run", return_value=proc):
            with self.assertRaises(tm.TencentMeetingError) as ctx:
                tm._run_tmeet("meeting", "get")
            self.assertIn("tmeet auth login", str(ctx.exception))


class SubtitlesBridgeTests(unittest.TestCase):
    def test_meeting_transcript_lines(self):
        from backend.devour.subtitles import fetch_meeting_transcript_text

        fake = {"dialogue": [{"start": 83.0, "end": 90.0, "speaker": "王熠明", "text": "分享开始"},
                             {"start": 125.0, "end": 130.0, "speaker": "Allen", "text": "谢谢"}],
                "subject": "AI+X碰个头", "speakers": ["王熠明", "Allen"]}
        with mock.patch.object(tm, "fetch_meeting_transcript", return_value=fake):
            meta = fetch_meeting_transcript_text("https://meeting.tencent.com/crm/x")
        self.assertEqual(meta["lang"], "zh")
        self.assertIn("2 位发言人", meta["title"])
        self.assertEqual(meta["transcript"].splitlines()[0], "[01:23] 王熠明: 分享开始")
        self.assertEqual(meta["transcript"].splitlines()[1], "[02:05] Allen: 谢谢")


class FastModePipelineTests(unittest.TestCase):
    """极速模式：skip_frames=True 时不触碰抽帧/VLM"""

    def _run_report_stages(self, skip_frames):
        from backend.algorithm import pipeline as pl

        dialogue = [{"start": 0.0, "end": 5.0, "text": "张三: 你好"}]
        with mock.patch.object(pl, "_generate_and_match_outline",
                               return_value=(["m"], [("h1", 1)], ["h1"], "outline")), \
             mock.patch.object(pl.timing, "track", lambda name: mock.MagicMock()), \
             mock.patch.object(pl.outline_handler, "generate_detailed_outline",
                               return_value="/tmp/detailed.md"), \
             mock.patch.object(pl.outline_handler, "generate_final_report") as gf, \
             mock.patch.object(pl.outline_handler, "generate_detailed_report") as gd, \
             mock.patch.object(pl.video_handler, "extract_frames_by_headings") as gef, \
             mock.patch.object(pl.image_processor, "process_all_frames") as paf, \
             mock.patch.object(pl.image_processor, "select_keyframes_with_vlm") as svlm:
            stages = []
            pl._run_report_stages(
                dialogue, "/tmp/out", "高中",
                progress=lambda pct, msg, stage: stages.append(stage),
                skip_frames=skip_frames, skip_label="极速模式",
                video_path="/tmp/fake.mp4", prepared={"duration": 100})
        return gef, paf, svlm, gf, gd, stages

    def test_fast_mode_skips_frame_stages(self):
        gef, paf, svlm, gf, gd, stages = self._run_report_stages(skip_frames=True)
        gef.assert_not_called()
        paf.assert_not_called()
        svlm.assert_not_called()
        gf.assert_called_once()
        gd.assert_called_once()
        self.assertIn("generating_report", stages)

    def test_normal_mode_runs_frame_stages(self):
        gef, paf, svlm, gf, gd, stages = self._run_report_stages(skip_frames=False)
        gef.assert_called_once()
        paf.assert_called_once()
        svlm.assert_called_once()


if __name__ == "__main__":
    unittest.main()
