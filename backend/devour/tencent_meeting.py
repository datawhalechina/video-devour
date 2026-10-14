# -*- coding: utf-8 -*-
"""
腾讯会议数据源：通过本地 tmeet CLI（@tencentcloud/tmeet，OAuth 已授权）拉取
会议录制转写，供报告管线与字幕笔记消费。

前置条件：本机已 `npm install -g @tencentcloud/tmeet` 且 `tmeet auth login` 完成。

实测要点（2026-10 验证）：
- 分享短链（/crm/ /ctm/ 等）不能直接当 record_file_id 用；crm 云录制页（/cw/）
  的服务端渲染数据里内嵌 meeting_code 与 meeting_id，可直接抽取；
  /ct/（转写分享）在无权限时返回空数据，不可依赖。
- record list/search 只返回自己有权限的录制；周期会议必须走 meeting get
  （会议级查询）才能看到 records[] 与 permission_status。
- 云录制含多个子文件，通常仅一个有转写内容，其余报 70001/30003，需逐个容错。
"""

import json
import logging
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# CLI 位置：优先环境变量（桌面端打包场景），否则 PATH 查找
_CLI_PATH = None
_CLI_TIMEOUT = 60          # 单次 CLI 调用超时（秒）
_HTTP_TIMEOUT = 15         # 短链页面请求超时（秒）

_PAGE_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# meeting.tencent.com/crm|cw|ctm|ct|dm/{short_id}
_MEETING_URL_RE = re.compile(
    r"meeting\.tencent\.com/(crm|cw|ctm|ct|dm)/([A-Za-z0-9_-]+)", re.IGNORECASE
)
# 会议号：9-12 位数字（用户可从腾讯会议客户端复制，如 60669290755）
_MEETING_CODE_RE = re.compile(r"^\d{9,12}$")
# meeting_id：19 位数字
_MEETING_ID_RE = re.compile(r"^\d{19}$")

# cw 页面内联 RSC 数据中的会议标识（\x 转义形式出现在 HTML 属性里，两种都匹配）
_CODE_IN_PAGE_RE = re.compile(r"\\?\"meeting_code\\?\":\\?\"(\d{9,12})\\?\"")
_ID_IN_PAGE_RE = re.compile(r"\\?\"meeting_id\\?\":\\?\"(\d{16,22})\\?\"")


class TencentMeetingError(Exception):
    """面向用户的取数失败（文案可直接透出前端）。"""


# ---------------------------------------------------------------------------
# CLI 封装
# ---------------------------------------------------------------------------

def _cli_path() -> str:
    global _CLI_PATH
    if _CLI_PATH is None:
        import os
        _CLI_PATH = os.environ.get("TMEET_CLI_PATH") or shutil.which("tmeet") or "tmeet"
    return _CLI_PATH


def _run_tmeet(*args: str, timeout: int = None) -> Dict:
    """执行 tmeet 子命令并解析 JSON 输出；失败时抛 TencentMeetingError。"""
    cmd = [_cli_path(), *args, "--format", "json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout or _CLI_TIMEOUT,
        )
    except FileNotFoundError:
        raise TencentMeetingError(
            "未找到 tmeet 命令。请先在终端执行 `npm install -g @tencentcloud/tmeet` 安装腾讯会议 CLI"
        )
    except subprocess.TimeoutExpired:
        raise TencentMeetingError(f"腾讯会议 CLI 响应超时（{' '.join(args[:2])}…），请稍后重试")

    output = (proc.stdout or "").strip()
    if proc.returncode != 0 or not output:
        detail = (proc.stderr or output or "").strip()
        raise TencentMeetingError(_map_cli_error(detail))

    try:
        # CLI 输出偶发混入日志行，取第一个 JSON 对象（'{' 起）
        start = output.index("{")
        return json.loads(output[start:])
    except (ValueError, json.JSONDecodeError):
        raise TencentMeetingError(f"腾讯会议 CLI 输出无法解析：{output[:200]}")


def _map_cli_error(detail: str) -> str:
    """把 CLI 错误映射为用户可理解的文案。"""
    if "auth" in detail.lower() or "登录" in detail or "token" in detail.lower():
        return "腾讯会议 CLI 未登录或授权已过期，请在终端运行 `tmeet auth login` 完成授权后重试"
    if "Invalid RecordFileId" in detail:
        return "腾讯会议录制文件 ID 无效，录制可能已被删除"
    if "会议号无效" in detail or "会议信息不存在" in detail:
        return "未找到该会议（可能无访问权限或会议号有误）"
    snippet = detail.splitlines()[0][:160] if detail else "未知错误"
    return f"腾讯会议 CLI 调用失败：{snippet}"


def check_auth() -> Dict:
    """检查 CLI 安装与登录状态，返回 {installed, logged_in, user_name, message}。

    `tmeet auth status` 输出人读文本（忽略 --format json），不走 _run_tmeet 的
    JSON 解析，直接子进程判读。
    """
    import subprocess
    try:
        proc = subprocess.run(
            [_cli_path(), "auth", "status"], capture_output=True, text=True,
            timeout=_CLI_TIMEOUT,
        )
    except FileNotFoundError:
        return {"installed": False, "logged_in": False, "user_name": "",
                "message": "未找到 tmeet 命令。请先在终端执行 "
                           "`npm install -g @tencentcloud/tmeet` 安装腾讯会议 CLI"}
    except subprocess.TimeoutExpired:
        return {"installed": True, "logged_in": False, "user_name": "",
                "message": "tmeet auth status 响应超时，请稍后重试"}
    text = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and "Logged in" in text:
        m = re.search(r"UserName:\s*(\S+)", text)
        user = m.group(1) if m else ""
        return {"installed": True, "logged_in": True, "user_name": user,
                "message": "tmeet 已安装并登录" + (f"（{user}）" if user else "")}
    if proc.returncode == 0:
        return {"installed": True, "logged_in": False, "user_name": "",
                "message": "tmeet 已安装但未登录，请在终端运行 `tmeet auth login` 完成授权"}
    return {"installed": True, "logged_in": False, "user_name": "",
            "message": f"tmeet auth status 异常：{text.strip()[:160]}"}


# ---------------------------------------------------------------------------
# 输入解析
# ---------------------------------------------------------------------------

def parse_meeting_ref(text: str) -> Optional[Dict]:
    """识别用户输入形态：url（分享短链）/ meeting_code / meeting_id。"""
    text = (text or "").strip()
    if not text:
        return None
    m = _MEETING_URL_RE.search(text)
    if m:
        return {"kind": "url", "path": m.group(1).lower(), "value": m.group(2)}
    if _MEETING_ID_RE.match(text):
        return {"kind": "meeting_id", "value": text}
    if _MEETING_CODE_RE.match(text):
        return {"kind": "meeting_code", "value": text}
    return None


def _resolve_short_link(short_id: str) -> Optional[Dict]:
    """
    请求分享短链页面，从服务端渲染数据中抽 meeting_code / meeting_id。

    /crm/ 页面是 JS 跳转壳（无数据），统一改请求 /cw/ 回放页；
    无权限或页面改版时返回 None，由调用方降级引导。
    """
    url = f"https://meeting.tencent.com/cw/{short_id}"
    try:
        resp = requests.get(
            url, headers={"User-Agent": _PAGE_UA}, timeout=_HTTP_TIMEOUT,
            allow_redirects=True,
        )
        html = resp.text or ""
    except requests.RequestException as e:
        logger.warning(f"请求腾讯会议分享页失败: {e}")
        return None

    code_m = _CODE_IN_PAGE_RE.search(html)
    id_m = _ID_IN_PAGE_RE.search(html)
    if not code_m and not id_m:
        return None
    return {
        "meeting_code": code_m.group(1) if code_m else "",
        "meeting_id": id_m.group(1) if id_m else "",
    }


# ---------------------------------------------------------------------------
# 会议定位与转写拉取
# ---------------------------------------------------------------------------

def resolve_meeting(text: str) -> Dict:
    """
    输入（短链/会议号/meeting_id）→ 会议元信息（tmeet meeting get）。

    Returns: {meeting_id, meeting_code, subject, meeting_type, join_url, records[]}
    """
    ref = parse_meeting_ref(text)
    if not ref:
        raise TencentMeetingError(
            "无法识别的腾讯会议输入：请粘贴 meeting.tencent.com 分享链接，或 9-12 位会议号"
        )

    if ref["kind"] == "url":
        resolved = _resolve_short_link(ref["value"])
        if not resolved:
            raise TencentMeetingError(
                "分享链接解析失败（可能无查看权限或链接已失效）。"
                "可改为粘贴 9-12 位会议号（腾讯会议客户端「会议号」处可复制）"
            )
        meeting_id, meeting_code = resolved["meeting_id"], resolved["meeting_code"]
    elif ref["kind"] == "meeting_id":
        meeting_id, meeting_code = ref["value"], ""
    else:
        meeting_id, meeting_code = "", ref["value"]

    if meeting_id:
        out = _run_tmeet("meeting", "get", "--meeting-id", meeting_id)
    else:
        out = _run_tmeet("meeting", "get", "--meeting-code", meeting_code)

    infos = (out.get("data") or {}).get("meeting_info_list") or []
    if not infos:
        raise TencentMeetingError("未找到该会议（可能无访问权限或已过期）")
    info = infos[0]
    return {
        "meeting_id": info.get("meeting_id", ""),
        "meeting_code": info.get("meeting_code", ""),
        "subject": info.get("subject", "腾讯会议录制"),
        "meeting_type": info.get("meeting_type", ""),
        "join_url": info.get("join_url", ""),
        "records": info.get("records") or [],
    }


def _pick_record_file_ids(meta: Dict) -> List[Dict]:
    """
    从会议 records[] 中筛出可拉转写的录制，返回 [{record_file_id, meeting_record_id, subject}]。

    优先级：permission_status=can_view 的「文字转写」（record_file_id 现成）>
    can_view 的「云录制」（需下钻 record address 拿子文件）。
    """
    candidates = []
    for rec in meta.get("records", []):
        if rec.get("permission_status") != "can_view":
            continue
        rtype = rec.get("type", "")
        entry = {
            "meeting_record_id": rec.get("meeting_record_id", ""),
            "subject": rec.get("subject") or meta.get("subject", "腾讯会议录制"),
            "record_file_id": rec.get("record_file_id", ""),
            "type": rtype,
        }
        candidates.append(entry)
        if "云录制" in rtype and not entry["record_file_id"]:
            entry["need_address"] = True

    if not candidates:
        has_any = bool(meta.get("records"))
        raise TencentMeetingError(
            "该会议的录制无查看权限（可申请）或没有录制文件"
            if has_any else "该会议没有录制文件"
        )

    # 文字转写直连优先（免下钻），云录制其次
    candidates.sort(key=lambda e: (e.get("need_address", False)))
    return candidates


def fetch_meeting_transcript(text: str) -> Dict:
    """
    主入口：输入任意形态（短链/会议号/meeting_id）→ 拉到有内容的转写。

    Returns: {
        meeting_id, meeting_code, subject, record_file_id,
        minutes,            # transcript-get 的 data.minutes 原始结构
        dialogue,           # [{start, end, text(带说话人前缀)}]（秒）
        duration_seconds, keywords, speakers,
    }
    """
    meta = resolve_meeting(text)
    candidates = _pick_record_file_ids(meta)
    meeting_id = meta["meeting_id"]

    # 展开云录制的子文件
    expanded: List[Dict] = []
    for entry in candidates:
        if entry.pop("need_address", False):
            try:
                out = _run_tmeet("record", "address",
                                 "--meeting-record-id", entry["meeting_record_id"])
                files = (out.get("data") or {}).get("record_files") or []
                for f in files:
                    if f.get("record_file_id"):
                        expanded.append({**entry, "record_file_id": f["record_file_id"]})
            except TencentMeetingError as e:
                logger.warning(f"获取录制子文件列表失败: {e}")
        elif entry["record_file_id"]:
            expanded.append(entry)

    if not expanded:
        raise TencentMeetingError("该会议录制没有可访问的转写文件")

    # 逐个尝试，取第一个有段落的（多子文件通常仅一个有转写，其余 70001/30003 容错跳过）
    last_error = ""
    for entry in expanded:
        fid = entry["record_file_id"]
        try:
            out = _run_tmeet("record", "transcript-get",
                             "--record-file-id", fid, "--meeting-id", meeting_id)
        except TencentMeetingError as e:
            last_error = str(e)
            logger.info(f"子文件 {fid} 无转写（跳过）: {e}")
            continue
        minutes = (out.get("data") or {}).get("minutes") or {}
        paragraphs = minutes.get("paragraphs") or []
        if not paragraphs:
            continue
        dialogue = transcript_to_dialogue(minutes)
        if not dialogue:
            continue
        speakers = sorted({
            p.get("speaker", {}).get("user_name", "")
            for p in paragraphs if p.get("speaker", {}).get("user_name")
        })
        duration = dialogue[-1]["end"] if dialogue else 0.0
        return {
            "meeting_id": meeting_id,
            "meeting_code": meta["meeting_code"],
            "subject": entry.get("subject") or meta["subject"],
            "record_file_id": fid,
            "minutes": minutes,
            "dialogue": dialogue,
            "duration_seconds": round(duration, 2),
            "keywords": minutes.get("keywords") or [],
            "speakers": speakers,
        }

    raise TencentMeetingError(
        f"所有录制子文件均无转写内容{f'（{last_error}）' if last_error else ''}；"
        "转写可能仍在生成中，请稍后重试"
    )


# ---------------------------------------------------------------------------
# 转写结构转换
# ---------------------------------------------------------------------------

def _ts_to_seconds(ts: str) -> float:
    """'MM:SS' / 'HH:MM:SS' → 秒。解析失败返回 0。"""
    if not ts:
        return 0.0
    parts = str(ts).split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return 0.0
    seconds = 0.0
    for n in nums:
        seconds = seconds * 60 + n
    return seconds


def transcript_to_dialogue(minutes: Dict) -> List[Dict]:
    """
    tmeet 转写结构 → 管线 processed_dialogue：[{speaker, start, end, text}]（秒）。

    形状对齐 ASRProcessor 的 v2 产物（speaker 为独立字段、text 为纯内容），
    但 speaker 直接用会议实名（报告里「谁说了什么」是会议场景的关键信息）。
    """
    dialogue = []
    for p in minutes.get("paragraphs") or []:
        text = "".join(
            w.get("text", "")
            for s in p.get("sentences") or []
            for w in s.get("words") or []
        ).strip()
        if not text:
            continue
        speaker = (p.get("speaker") or {}).get("user_name", "").strip() or "未知发言人"
        dialogue.append({
            "speaker": speaker,
            "start": _ts_to_seconds(p.get("start_time")),
            "end": _ts_to_seconds(p.get("end_time")),
            "text": text,
        })
    return dialogue


def build_probe_info(text: str) -> Dict:
    """
    生成与 probe_video_info 统一形状的预览信息（不发 transcript-get，快速）。
    """
    meta = resolve_meeting(text)
    records = meta.get("records", [])
    viewable = [r for r in records if r.get("permission_status") == "can_view"]
    last_record = viewable[-1] if viewable else (records[-1] if records else {})
    duration_text = last_record.get("duration", "")
    duration = 0
    if duration_text:
        duration = int(_ts_to_seconds(duration_text))
    return {
        "id": meta["meeting_id"],
        "title": meta["subject"],
        "uploader": "腾讯会议",
        "duration": duration,
        "duration_string": duration_text,
        "thumbnail": "",
        "platform": "tencent_meeting",
        # 原样回传用户输入（短链/会议号）：预览卡「生成图文报告」会用它重新建任务
        "webpage_url": text,
        "video_id": meta.get("meeting_code") or meta["meeting_id"],
        "description": (
            f"会议类型：{meta.get('meeting_type', '未知')}；"
            f"可查看录制 {len(viewable)}/{len(records)} 条"
        ),
        "published_at": "",
        "stats": {},
        "meeting_extra": {
            "meeting_code": meta.get("meeting_code", ""),
            "records_total": len(records),
            "viewable_records": len(viewable),
        },
    }


def meeting_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
