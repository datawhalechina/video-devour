import { isLearningPreview } from "./preview";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { Button, EmptyState } from "../../shared/ui/Workspace";
import { useConfigGate } from "../../components/ConfigGateProvider";
import MediaCover from "../../components/lake/MediaCover";
import { learningRequest } from "./api";

export default function QuizWorkspace({ taskId, report }) {
  const { guardConfig } = useConfigGate();
  const [quiz, setQuiz] = useState(null),
    [answers, setAnswers] = useState({}),
    [result, setResult] = useState(null);
  const [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [index, setIndex] = useState(0),
    [advice, setAdvice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    learningRequest(taskId, "quiz", undefined, controller.signal)
      .then(setQuiz)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [taskId]);
  const generate = async () => {
    if (!isLearningPreview(taskId) && !(await guardConfig(["llm"]))) return;
    setBusy(true);
    setError("");
    try {
      setQuiz(await learningRequest(taskId, "quiz", { force: !!quiz }));
      setAnswers({});
      setResult(null);
      setIndex(0);
      setAdvice("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      setResult(await learningRequest(taskId, "quiz/submit", { answers }));
      setIndex(0);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const askAdvice = async () => {
    if (!isLearningPreview(taskId) && !(await guardConfig(["llm"]))) return;
    setBusy(true);
    try {
      const data = await learningRequest(taskId, "quiz/advice", {
        attempt_id: result.attempt_id,
      });
      setAdvice(data.advice);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const count = Object.values(answers).filter((value) => value.length).length;
  if (busy && !quiz) return <EmptyState loading title="正在准备习题" />;
  if (!quiz)
    return (
      <EmptyState
        title="用一次练习，检验你的理解。"
        description={error || "根据这段视频的报告生成单选、多选和判断题。"}
        action={
          <Button variant="primary" onClick={generate}>
            生成习题
          </Button>
        }
      />
    );
  const questions = result?.questions || quiz.questions || [],
    question = questions[index];
  if (!question)
    return (
      <EmptyState
        title="暂无可用题目"
        action={<Button onClick={generate}>重新生成</Button>}
      />
    );
  const choose = (option) => {
    if (result) return;
    setAnswers((old) => {
      const selected = old[question.id] || [];
      return {
        ...old,
        [question.id]:
          question.type === "multiple"
            ? selected.includes(option)
              ? selected.filter((value) => value !== option)
              : [...selected, option]
            : [option],
      };
    });
  };
  const selected = answers[question.id] || [];
  return (
    <div className="vd-study-layout">
      <section className="vd-panel vd-quiz-main">
        <div className="vd-quiz-heading">
          <h2>
            {result ? "回顾" : "练习"} {String(index + 1).padStart(2, "0")}{" "}
            <span>/ {questions.length}</span>
          </h2>
          <Button variant="quiet" disabled={busy} onClick={generate}>
            <RotateCcw />
            重新出题
          </Button>
        </div>
        <div className="vd-progress">
          <i style={{ width: `${((index + 1) / questions.length) * 100}%` }} />
        </div>
        <p className="vd-muted">
          {
            { single: "单选题", multiple: "多选题", boolean: "判断题" }[
              question.type
            ]
          }{" "}
          · {question.chapter}
        </p>
        <h3>{question.question}</h3>
        <div className="vd-quiz-options">
          {question.options.map((option, i) => {
            const picked = selected.includes(i);
            const correct = result && question.answer?.includes(i);
            return (
              <button
                key={i}
                aria-pressed={picked}
                disabled={!!result}
                className={`${picked ? "is-selected" : ""} ${correct ? "is-correct" : ""}`}
                onClick={() => choose(i)}
              >
                <span>
                  {picked || correct ? <CheckCircle size={20} /> : <i />}
                </span>
                <b>{String.fromCharCode(65 + i)}.</b>
                {option}
              </button>
            );
          })}
        </div>
        {result && (
          <section
            className={`vd-quiz-verdict ${question.verdict === "correct" ? "is-correct" : "is-wrong"}`}
          >
            <strong>
              {question.verdict === "correct"
                ? "回答正确"
                : question.verdict === "partial"
                  ? "部分正确"
                  : "还需要再巩固"}
            </strong>
            <p>{question.explanation}</p>
          </section>
        )}
        {error && (
          <p role="alert" className="vd-error">
            {error}
          </p>
        )}
        <div className="vd-quiz-navigation">
          <Button
            disabled={!index || busy}
            onClick={() => setIndex((i) => i - 1)}
          >
            <ArrowLeft />
            上一题
          </Button>
          {index < questions.length - 1 ? (
            <Button
              variant="primary"
              disabled={busy}
              onClick={() => setIndex((i) => i + 1)}
            >
              下一题
              <ArrowRight />
            </Button>
          ) : !result ? (
            <Button
              variant="primary"
              disabled={busy || !count}
              onClick={submit}
            >
              {busy ? "判题中…" : "提交判题"}
            </Button>
          ) : (
            <Button
              onClick={() => {
                setResult(null);
                setAnswers({});
                setIndex(0);
                setAdvice("");
              }}
            >
              重新练习
            </Button>
          )}
        </div>
      </section>
      <aside className="vd-panel vd-study-sidebar">
        <h2>
          {result ? `本次得分 ${result.score}` : "答题进度"}{" "}
          <small>
            {count} / {questions.length}
          </small>
        </h2>
        <nav className="vd-question-index" aria-label="题目目录">
          {questions.map((q, i) => (
            <button
              key={q.id}
              aria-label={`第 ${i + 1} 题`}
              aria-current={i === index ? "step" : undefined}
              className={answers[q.id]?.length ? "is-answered" : ""}
              onClick={() => setIndex(i)}
            >
              {result && q.verdict === "correct" ? (
                <CheckCircle size={18} />
              ) : (
                i + 1
              )}
            </button>
          ))}
        </nav>
        <h3>题目来源</h3>
        <div className="vd-quiz-cover">
          <MediaCover video={report} />
        </div>
        <strong>{quiz.title || report.video_name}</strong>
        <p className="vd-muted">{question.chapter || "视频报告"}</p>
        <Button
          onClick={() =>
            location.assign(
              isLearningPreview(taskId) ? "/library" : `/report/${taskId}`,
            )
          }
        >
          回看报告
        </Button>
        <p className="vd-muted">本题选自视频报告，建议结合原文巩固理解。</p>
        {result && (
          <Button disabled={busy} onClick={askAdvice}>
            <Sparkles />
            学习建议
          </Button>
        )}
        {advice && (
          <p>{typeof advice === "string" ? advice : JSON.stringify(advice)}</p>
        )}
      </aside>
    </div>
  );
}
