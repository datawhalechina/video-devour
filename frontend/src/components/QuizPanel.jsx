import { useEffect, useState } from "react";
import { ClipboardCheck, RotateCcw, Sparkles, X } from "lucide-react";
import { useConfigGate } from "./ConfigGateProvider";

// 学习测试面板：出题（单选/多选/判断）→ 作答 → 服务端判题 → 学习评估。
// 独立组件：只依赖 task_id 与四个 REST 端点，便于后续升级或复用。
const TYPE_LABEL = { single: "单选题", multiple: "多选题", boolean: "判断题" };
const LETTERS = "ABCDEFGH";
const VERDICT_STYLE = {
  correct: { label: "答对", cls: "bg-emerald-100 text-emerald-700" },
  partial: { label: "半对", cls: "bg-amber-100 text-amber-700" },
  wrong: { label: "答错", cls: "bg-rose-100 text-rose-700" },
};

export default function QuizPanel({ taskId, onClose }) {
  const { guardConfig } = useConfigGate();
  const [phase, setPhase] = useState("loading");   // loading | quiz | result | error
  const [error, setError] = useState("");
  const [quiz, setQuiz] = useState(null);          // 公开试卷（无答案）+ attempts
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // 已有试卷直接复用（服务端缓存）；需要新出题时才检查 LLM 配置
  const load = async (force = false) => {
    if (force && !(await guardConfig(["llm"]))) return;
    try {
      if (!force) {
        const cached = await fetch(`/api/task/${taskId}/quiz`);
        if (cached.ok) {
          setQuiz(await cached.json());
          setPhase("quiz");
          return;
        }
      }
      // 尚未生成或要求重新出题：调用生成端点（需要 LLM）
      if (!(await guardConfig(["llm"]))) { setPhase("error"); setError("请先在偏好设置中配置 LLM"); return; }
      const res = await fetch(`/api/task/${taskId}/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "生成失败");
      setQuiz(data);
      setAnswers({});
      setResult(null);
      setAdvice(null);
      setPhase("quiz");
    } catch (e) {
      setError(e.message);
      setPhase("error");
    }
  };

  // 首次打开：已有试卷直接复用（服务端缓存），否则生成
  useEffect(() => { load(false); }, [taskId]);   // eslint-disable-line react-hooks/exhaustive-deps

  const answeredCount = Object.values(answers).filter(v => v.length > 0).length;

  const pick = (qid, idx, type) => {
    setAnswers(prev => {
      const cur = prev[qid] || [];
      if (type === "multiple") {
        const next = cur.includes(idx) ? cur.filter(i => i !== idx) : [...cur, idx].sort((a, b) => a - b);
        return { ...prev, [qid]: next };
      }
      return { ...prev, [qid]: [idx] };
    });
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`/api/task/${taskId}/quiz/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "判题失败");
      setResult(data);
      setPhase("result");
    } catch (e) {
      alert(`判题失败: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const fetchAdvice = async () => {
    if (!result || adviceLoading) return;
    setAdviceLoading(true);
    try {
      const res = await fetch(`/api/task/${taskId}/quiz/advice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attempt_id: result.attempt_id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "生成失败");
      setAdvice(data.advice);
    } catch (e) {
      alert(`学习建议生成失败: ${e.message}`);
    } finally {
      setAdviceLoading(false);
    }
  };

  const retake = () => {
    setAnswers({});
    setResult(null);
    setAdvice(null);
    setPhase("quiz");
  };

  const scoreTone = result ? (result.score >= 80 ? "text-emerald-600" : result.score >= 60 ? "text-amber-600" : "text-rose-600") : "";

  return (
    <div className="fixed inset-0 z-[200] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* 头部 */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 flex-shrink-0">
          <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
            <ClipboardCheck size={18} className="text-primary-600" />
            {phase === "result" ? "测试结果与学习评估" : (quiz?.title || "学习测试")}
          </h3>
          <div className="flex items-center gap-2">
            {phase === "quiz" && quiz && (
              <button
                onClick={() => { setRegenerating(true); load(true).finally(() => setRegenerating(false)); }}
                disabled={regenerating}
                className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                title="丢弃当前试卷，重新出一套题">
                <RotateCcw size={13} className="inline mr-1" />{regenerating ? "出题中…" : "重新出题"}
              </button>
            )}
            <button onClick={onClose}
                    className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100"><X size={16} /></button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="overflow-y-auto px-5 py-4 flex-1">
          {phase === "loading" && (
            <div className="py-16 text-center text-gray-500">
              <ClipboardCheck size={36} className="mx-auto mb-3 text-primary-400 animate-pulse" />
              正在依据报告出题（约 10-30 秒）…
            </div>
          )}
          {phase === "error" && (
            <div className="py-12 text-center">
              <p className="text-rose-600 mb-3">出题失败：{error}</p>
              <button onClick={() => load(true)}
                      className="px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700">重试</button>
            </div>
          )}

          {phase === "quiz" && quiz && (
            <>
              <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 mb-4">
                <span className="px-2 py-0.5 rounded-full bg-gray-100">{quiz.question_count} 题</span>
                {Object.entries(quiz.type_stats).map(([label, n]) => (
                  <span key={label} className="px-2 py-0.5 rounded-full bg-gray-100">{label} {n}</span>
                ))}
                {quiz.attempts?.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-primary-50 text-primary-700">
                    历史最好 {Math.max(...quiz.attempts.map(a => a.score))} 分
                  </span>
                )}
              </div>

              {quiz.questions.map((q, i) => (
                <div key={q.id} className="mb-5 pb-5 border-b border-gray-100 last:border-0">
                  <div className="flex items-start gap-2 mb-2.5">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-50 text-primary-700 text-xs font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
                    <div className="flex-1">
                      <span className="text-[11px] text-gray-400 mr-2">{TYPE_LABEL[q.type]} · {q.chapter}</span>
                      <p className="text-sm text-gray-900 font-medium leading-relaxed">{q.question}</p>
                    </div>
                  </div>
                  <div className="pl-8 grid gap-1.5">
                    {q.options.map((opt, idx) => {
                      const selected = (answers[q.id] || []).includes(idx);
                      return (
                        <button key={idx}
                                onClick={() => pick(q.id, idx, q.type)}
                                className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left text-sm transition ${
                                  selected
                                    ? "border-primary-500 bg-primary-50 text-primary-900"
                                    : "border-gray-200 text-gray-700 hover:border-gray-300 hover:bg-gray-50"}`}>
                          <span className={`flex-shrink-0 w-5 h-5 flex items-center justify-center text-xs font-bold ${
                            selected ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-500"} ${
                            q.type === "multiple" ? "rounded-md" : "rounded-full"}`}>
                            {LETTERS[idx]}
                          </span>
                          <span>{opt}</span>
                        </button>
                      );
                    })}
                    {q.type === "multiple" && (
                      <p className="text-[11px] text-gray-400 mt-0.5">多选题：全对满分，漏选得一半，错选不得分</p>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}

          {phase === "result" && result && (
            <>
              {/* 总分与评估 */}
              <div className="flex items-center gap-5 mb-5 p-4 rounded-xl bg-gray-50">
                <div className="text-center">
                  <div className={`text-4xl font-black ${scoreTone}`}>{result.score}</div>
                  <div className="text-xs text-gray-400 mt-0.5">总分</div>
                </div>
                <div className="flex-1 text-sm">
                  <p className="text-gray-800 mb-1.5">
                    全对 <strong>{result.correct_count}</strong> / {result.question_count} 题
                    {result.score >= 80 ? " · 掌握扎实" : result.score >= 60 ? " · 基本掌握，仍有薄弱点" : " · 需要重点复习"}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(result.per_type).map(([label, s]) => (
                      <span key={label} className="px-2 py-0.5 rounded-full bg-white border border-gray-200 text-xs text-gray-600">
                        {label} {s.correct}/{s.count}
                      </span>
                    ))}
                  </div>
                </div>
                <button onClick={retake}
                        className="px-3 py-2 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50 flex-shrink-0">
                  <RotateCcw size={13} className="inline mr-1" />重做
                </button>
              </div>

              {/* 按章掌握度 */}
              {result.per_chapter.length > 0 && (
                <div className="mb-5">
                  <h4 className="text-sm font-bold text-gray-800 mb-2">分章掌握度</h4>
                  <div className="grid gap-2">
                    {result.per_chapter.map(c => (
                      <div key={c.chapter} className="flex items-center gap-3">
                        <span className="text-xs text-gray-600 w-40 truncate flex-shrink-0" title={c.chapter}>{c.chapter}</span>
                        <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                          <div className={`h-full rounded-full ${c.score >= 80 ? "bg-emerald-500" : c.score >= 50 ? "bg-amber-400" : "bg-rose-400"}`}
                               style={{ width: `${c.score}%` }} />
                        </div>
                        <span className="text-xs text-gray-500 w-14 text-right flex-shrink-0">{c.correct}/{c.count} · {c.score}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 逐题回顾 */}
              <h4 className="text-sm font-bold text-gray-800 mb-2">逐题回顾</h4>
              {result.questions.map((q) => {
                const v = VERDICT_STYLE[q.verdict];
                return (
                  <div key={q.id} className="mb-4 pb-4 border-b border-gray-100 last:border-0">
                    <div className="flex items-start gap-2 mb-1.5">
                      <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[11px] font-bold mt-0.5 ${v.cls}`}>{v.label}</span>
                      <div>
                        <span className="text-[11px] text-gray-400 mr-2">{TYPE_LABEL[q.type]} · {q.chapter}</span>
                        <p className="text-sm text-gray-900 font-medium">{q.question}</p>
                      </div>
                    </div>
                    <div className="pl-1 text-xs space-y-0.5">
                      <p className="text-gray-600">
                        你的答案：
                        {q.your_answer.length ? q.your_answer.map(idx => LETTERS[idx]).join("、") : "未答"}
                        {q.your_answer.length > 0 && <span className="text-gray-400">（{q.your_answer.map(idx => q.options[idx]).join("；")}）</span>}
                      </p>
                      {q.verdict !== "correct" && (
                        <p className="text-emerald-700">
                          正确答案：{q.answer.map(idx => LETTERS[idx]).join("、")}
                          <span className="text-gray-400">（{q.answer.map(idx => q.options[idx]).join("；")}）</span>
                        </p>
                      )}
                      <p className="text-gray-500">解析：{q.explanation}</p>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* 底部操作条 */}
        {phase === "quiz" && quiz && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-200 flex-shrink-0">
            <span className="text-xs text-gray-500">已答 {answeredCount} / {quiz.question_count} 题（可不答完直接交卷）</span>
            <button onClick={submit} disabled={submitting || answeredCount === 0}
                    className="px-5 py-2 rounded-lg bg-primary-600 text-white text-sm font-bold hover:bg-primary-700 disabled:opacity-50">
              {submitting ? "判题中…" : "提交判题"}
            </button>
          </div>
        )}
        {phase === "result" && !advice && (
          <div className="px-5 py-3 border-t border-gray-200 flex-shrink-0">
            <button onClick={fetchAdvice} disabled={adviceLoading}
                    className="w-full py-2 rounded-lg border border-primary-300 text-primary-700 text-sm font-medium hover:bg-primary-50 disabled:opacity-50 flex items-center justify-center gap-1.5">
              <Sparkles size={14} />{adviceLoading ? "正在分析错题、生成学习建议…" : "生成学习建议（基于本次错题）"}
            </button>
          </div>
        )}
        {advice && (
          <div className="px-5 py-4 border-t border-gray-200 bg-primary-50/50">
            <h4 className="text-sm font-bold text-gray-800 mb-1.5 flex items-center gap-1.5"><Sparkles size={14} className="text-primary-600" />学习建议</h4>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{advice}</p>
          </div>
        )}
      </div>
    </div>
  );
}
