# -*- coding: utf-8 -*-
"""学习测试习题：生成 / 判题 / 学习评估（与主流水线解耦）。

设计目标：本模块自包含，只依赖任务输出目录里的报告文件与 LLMHandler——
不 import pipeline / API，后续升级（题库、错题本、间隔重复）只改这里。

产物（都落在任务输出目录，随任务走）：
- quiz.json          题目与标准答案（答案只留在服务端，前端拿不到）
- quiz_attempts.json 历次作答记录（含每次评估与可选的 LLM 学习建议）

判题完全在本地进行（不调 LLM）：单选/判断全对得分；多选全对满分、
漏选得一半、选错不得分。学习建议按需由 LLM 生成并缓存进作答记录。
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from backend.algorithm.llm_handler import LLMHandler

QUIZ_FILE = "quiz.json"
ATTEMPTS_FILE = "quiz_attempts.json"

QUESTION_TYPES = {"single": "单选题", "multiple": "多选题", "boolean": "判断题"}
BOOLEAN_OPTIONS = ["正确", "错误"]
LETTERS = "ABCDEFGH"

# 多选漏选得分比例（全对 1.0、漏选 0.5、错选 0）
MULTIPLE_PARTIAL_CREDIT = 0.5

# 取材优先级：精简报告信息密度最高；没有时依次回退
_SOURCE_FILES = ("final_report.md", "detailed_outline.md", "detailed_report.md")

_SYSTEM_PROMPT = (
    "你是严谨的中文出题专家，擅长依据给定材料出高质量测试题。"
    "只输出符合要求的 JSON，不要任何解释或 Markdown 代码块。"
)


def _read_source(output_dir: Path):
    """读取出题材料：返回 (报告全文, 章节标题列表)。"""
    for name in _SOURCE_FILES:
        f = Path(output_dir) / name
        if f.exists() and f.stat().st_size > 0:
            text = f.read_text(encoding="utf-8")
            return text, _extract_chapters(text)
    raise ValueError("任务目录没有可用的报告文件（final_report.md 等），请先完成处理")


def _extract_chapters(text: str):
    """从报告标题里取章节名（二级优先），用于给题目归章与按章评估。"""
    chapters = re.findall(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if not chapters:
        chapters = re.findall(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    return [c.strip() for c in chapters if c.strip()]


def _build_prompt(report: str, chapters, count: int, education_level: str) -> str:
    chapter_note = (
        "材料章节（题目 chapter 字段必须从中选择最相关的一个，原文照抄）：\n"
        + "\n".join(f"- {c}" for c in chapters)
        if chapters else "（材料没有明确章节时，chapter 填 \"综合\"）"
    )
    return f"""请依据下面的视频学习报告出 {count} 道中文测试题，用于检验学习者对视频内容的掌握程度。

【题型与数量】共 {count} 道，三种题型都必须出现：
- 单选题（type=single）约占 40%：4 个选项，恰好 1 个正确
- 多选题（type=multiple）约占 30%：4 个选项，恰好 2 或 3 个正确
- 判断题（type=boolean）：陈述一个明确可判定对错的命题

【出题要求】
1. 所有考点必须来自报告内容，禁止编造；优先考核心概念、机制、数字、因果与易混点。
2. 干扰项要有迷惑性（是常见误解或相邻概念），不要明显荒谬。
3. 判断题避免"决不""所有"这类送分表述，要有区分度。
4. 难度分布：约 40% 基础、40% 理解、20% 综合；适配「{education_level}」学习阶段。
5. 每题的 explanation 用 1-3 句话说明为什么对/错，依据报告原文表述。
6. 题目之间不重复考点。

{chapter_note}

【输出格式】只输出一个 JSON 对象，结构如下（answer 用选项字母，不要用序号）：
{{
  "title": "测试卷标题（不超过 20 字）",
  "questions": [
    {{
      "type": "single",
      "chapter": "章节名",
      "question": "题干",
      "options": ["选项A内容", "选项B内容", "选项C内容", "选项D内容"],
      "answer": ["A"],
      "explanation": "解析"
    }},
    {{
      "type": "multiple",
      "chapter": "章节名",
      "question": "题干",
      "options": ["...", "...", "...", "..."],
      "answer": ["A", "C"],
      "explanation": "解析"
    }},
    {{
      "type": "boolean",
      "chapter": "章节名",
      "question": "一个可判定对错的陈述句",
      "options": ["正确", "错误"],
      "answer": ["B"],
      "explanation": "解析"
    }}
  ]
}}

材料如下：
-------------------
{report}
-------------------"""


def _extract_json(raw: str):
    """提取 LLM 输出中的 JSON 对象：优先剥代码围栏，再取首个平衡的花括号块。"""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    start = raw.find("{")
    if start < 0:
        raise ValueError("LLM 未返回 JSON")
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])
    raise ValueError("LLM 返回的 JSON 不完整")


def _normalize_questions(payload, chapters, count):
    """校验并规范化 LLM 题目：字母答案转下标、修边界、剔除不合格题目。"""
    questions = []
    seen = set()
    for item in (payload.get("questions") or []):
        try:
            qtype = item["type"]
            if qtype not in QUESTION_TYPES:
                continue
            question = str(item.get("question", "")).strip()
            options = [str(o).strip() for o in (item.get("options") or [])]
            letters = [str(a).strip().upper() for a in (item.get("answer") or [])]

            if qtype == "boolean":
                options = list(BOOLEAN_OPTIONS)
            else:
                options = [o for o in options if o]
                if not 3 <= len(options) <= 5:
                    continue

            indices = sorted({LETTERS.index(a) for a in letters if a in LETTERS[:len(options)]})
            if qtype == "multiple":
                if len(indices) < 2 or len(indices) >= len(options):
                    continue
            else:
                if len(indices) != 1:
                    continue

            if not question or question in seen:
                continue
            seen.add(question)

            chapter = str(item.get("chapter", "")).strip()
            if chapters and chapter not in chapters:
                chapter = next((c for c in chapters if c in question), chapter or "综合")

            questions.append({
                "id": f"q{len(questions) + 1}",
                "type": qtype,
                "chapter": chapter or "综合",
                "question": question,
                "options": options,
                "answer": indices,
                "explanation": str(item.get("explanation", "")).strip() or "依据报告对应章节。",
            })
            if len(questions) >= count:
                break
        except (KeyError, ValueError, TypeError):
            continue

    # 三种题型至少各 1 道，否则视为生成质量不合格
    if len(questions) < 3 or len({q["type"] for q in questions}) < 3:
        raise ValueError(f"题目生成质量不合格（有效 {len(questions)} 道），请重试")
    return questions


def generate_quiz(output_dir, education_level: str = None, count: int = 10,
                  force: bool = False) -> dict:
    """生成测试题并落盘 quiz.json；已存在则直接复用（force=True 重新出题）。

    返回完整数据（含答案），供服务端使用；对外暴露请走 quiz_public()。
    """
    out_dir = Path(output_dir)
    quiz_path = out_dir / QUIZ_FILE
    if quiz_path.exists() and not force:
        return json.loads(quiz_path.read_text(encoding="utf-8"))

    count = max(3, min(int(count), 30))
    report, chapters = _read_source(out_dir)
    level = education_level or "自由学习"

    llm = LLMHandler(education_level=level)
    raw = llm.get_response(
        _build_prompt(report, chapters, count, level),
        system_message=_SYSTEM_PROMPT,
    )
    payload = _extract_json(raw)
    questions = _normalize_questions(payload, chapters, count)

    quiz = {
        "version": 1,
        "title": str(payload.get("title", "")).strip() or "视频学习测试",
        "education_level": level,
        "generated_at": datetime.now().isoformat(),
        "question_count": len(questions),
        "questions": questions,
    }
    quiz_path.write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info(f"学习测试已生成: {quiz_path}（{len(questions)} 题）")
    return quiz


def load_quiz(output_dir):
    """读取已生成的测试卷；未生成为 None。"""
    path = Path(output_dir) / QUIZ_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"quiz.json 读取失败: {e}")
        return None


def quiz_public(quiz: dict) -> dict:
    """发往客户端的视图：去掉答案与解析（判题后才返回）。"""
    questions = [
        {k: q[k] for k in ("id", "type", "chapter", "question", "options")}
        for q in quiz.get("questions", [])
    ]
    return {
        "title": quiz.get("title", "视频学习测试"),
        "education_level": quiz.get("education_level", ""),
        "generated_at": quiz.get("generated_at", ""),
        "question_count": quiz.get("question_count", len(questions)),
        "type_stats": _type_stats(quiz.get("questions", [])),
        "questions": questions,
    }


def _type_stats(questions):
    stats = {}
    for q in questions:
        label = QUESTION_TYPES[q["type"]]
        stats[label] = stats.get(label, 0) + 1
    return stats


# ---------------------------------------------------------------------------
# 判题与评估（纯本地计算）
# ---------------------------------------------------------------------------

def _score_question(question, picked):
    """单题得分：单选/判断全对 1 分；多选全对 1、漏选 0.5、错选 0。未答 0。"""
    correct = set(question["answer"])
    picked = set(picked or [])
    if not picked:
        return 0.0
    if picked == correct:
        return 1.0
    if question["type"] == "multiple" and picked < correct:
        return MULTIPLE_PARTIAL_CREDIT
    return 0.0


def _load_attempts(output_dir: Path):
    path = output_dir / ATTEMPTS_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_attempts(output_dir: Path, attempts):
    path = output_dir / ATTEMPTS_FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(attempts, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def grade_quiz(output_dir, answers: dict) -> dict:
    """判题并落盘作答记录，返回逐题结果与整体评估。

    answers: {题目 id: [选项下标...]}，多套未答题目的键可缺省。
    """
    quiz = load_quiz(output_dir)
    if not quiz:
        raise ValueError("测试卷尚未生成，请先生成")

    answers = answers or {}
    questions, per_type, per_chapter = [], {}, {}
    earned, total = 0.0, 0

    for q in quiz["questions"]:
        total += 1
        raw = answers.get(q["id"])
        picked = sorted({int(i) for i in raw}) if isinstance(raw, (list, tuple)) else []
        picked = [i for i in picked if 0 <= i < len(q["options"])]
        points = _score_question(q, picked)
        earned += points
        correct = points == 1.0

        label = QUESTION_TYPES[q["type"]]
        t = per_type.setdefault(label, {"count": 0, "correct": 0, "partial": 0})
        t["count"] += 1
        if correct:
            t["correct"] += 1
        elif points > 0:
            t["partial"] += 1

        c = per_chapter.setdefault(q["chapter"], {"count": 0, "correct": 0})
        c["count"] += 1
        if correct:
            c["correct"] += 1

        questions.append({
            **{k: q[k] for k in ("id", "type", "chapter", "question", "options")},
            "your_answer": picked,
            "answer": q["answer"],           # 判题后才下发答案与解析
            "explanation": q["explanation"],
            "points": points,
            "verdict": "correct" if correct else ("partial" if points > 0 else "wrong"),
        })

    score = round(earned / total * 100, 1) if total else 0.0
    result = {
        "attempt_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "at": datetime.now().isoformat(),
        "score": score,
        "correct_count": sum(1 for q in questions if q["verdict"] == "correct"),
        "question_count": total,
        "per_type": per_type,
        "per_chapter": [
            {"chapter": name, **stats, "score": round(stats["correct"] / stats["count"] * 100, 1)}
            for name, stats in per_chapter.items()
        ],
        "questions": questions,
        "advice": None,
    }

    attempts = _load_attempts(Path(output_dir))
    attempts.append({
        "attempt_id": result["attempt_id"],
        "at": result["at"],
        "score": score,
        "correct_count": result["correct_count"],
        "question_count": total,
        "per_chapter": result["per_chapter"],
        "answers": answers,
        "advice": None,
    })
    _save_attempts(Path(output_dir), attempts)
    logging.info(f"测试判题完成: 得分 {score}（{result['correct_count']}/{total}）")
    return result


def attempts_summary(output_dir) -> list:
    """历次作答概览（不含题目与答案明细），按时间倒序。"""
    attempts = _load_attempts(Path(output_dir))
    return [
        {k: a[k] for k in ("attempt_id", "at", "score", "correct_count", "question_count")}
        for a in reversed(attempts)
    ]


# ---------------------------------------------------------------------------
# 学习建议（可选的 LLM 增强，按需生成并缓存进作答记录）
# ---------------------------------------------------------------------------

def quiz_advice(output_dir, attempt_id: str) -> dict:
    """基于某次作答生成学习建议（只生成一次，缓存进 quiz_attempts.json）。"""
    out_dir = Path(output_dir)
    attempts = _load_attempts(out_dir)
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if attempt is None:
        raise ValueError(f"作答记录不存在: {attempt_id}")
    if attempt.get("advice"):
        return {"attempt_id": attempt_id, "advice": attempt["advice"]}

    quiz = load_quiz(out_dir) or {"questions": []}
    by_id = {q["id"]: q for q in quiz.get("questions", [])}
    wrong_lines = []
    for qid, picked in (attempt.get("answers") or {}).items():
        q = by_id.get(qid)
        if q and _score_question(q, picked) < 1.0:
            correct_text = "、".join(q["options"][i] for i in q["answer"])
            qtype_label = QUESTION_TYPES[q["type"]]
            wrong_lines.append(
                f"- [{qtype_label}]（{q['chapter']}）{q['question']}\n"
                f"  正确答案: {correct_text}；解析: {q['explanation']}"
            )
    chapter_lines = [
        f"- {c['chapter']}: {c['correct']}/{c['count']}"
        for c in attempt.get("per_chapter", [])
    ]

    prompt = f"""学习者刚完成一份视频学习测试（得分 {attempt['score']}，{attempt['correct_count']}/{attempt['question_count']} 全对）。
请基于错题与各章得分，给出针对这个视频的学习建议。

各章正确率：
{chr(10).join(chapter_lines) or "-（无）"}

错题与正确答案：
{chr(10).join(wrong_lines) or "-（全部正确，无错题）"}

请输出（简体中文，直接给内容，不要客套）：
1. 一句总评（掌握情况定性，20 字内）
2. 薄弱章节与薄弱知识点（来自上面错题，具体到概念）
3. 3-5 条可执行的学习建议（回到视频哪个部分、怎么补，不要空话）"""

    llm = LLMHandler(education_level=quiz.get("education_level"))
    advice = llm.get_response(prompt, system_message="你是善于诊断学习短板的中文辅导老师。只输出版本内容本身。").strip()
    advice = re.sub(r"^```(?:markdown|md)?\s*|```$", "", advice, flags=re.MULTILINE).strip()

    attempt["advice"] = advice
    _save_attempts(out_dir, attempts)
    return {"attempt_id": attempt_id, "advice": advice}
