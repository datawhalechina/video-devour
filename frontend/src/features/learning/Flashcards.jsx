import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  RotateCcw,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button, EmptyState } from "../../shared/ui/Workspace";

export default function Flashcards({ taskId, title, sections }) {
  const key = `videodevour-review-${taskId}`;
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [error, setError] = useState("");
  const [mastered, setMastered] = useState(() => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(value)
        ? value.filter((item) => typeof item === "string")
        : [];
    } catch {
      return [];
    }
  });
  const current = sections[index];
  const masteredCount = sections.filter((section) =>
    mastered.includes(`${section.id}:${section.content}`),
  ).length;
  const mark = (value) => {
    const id = `${current.id}:${current.content}`;
    const next = value
      ? [...new Set([...mastered, id])]
      : mastered.filter((item) => item !== id);
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setMastered(next);
      setError("");
    } catch {
      setError("无法保存复习进度，请检查浏览器存储权限。");
    }
  };
  const go = (i) => {
    setIndex(i);
    setFlipped(false);
  };
  if (!current)
    return (
      <EmptyState title="没有可复习的章节" description="请先生成视频报告。" />
    );
  return (
    <div className="vd-study-layout vd-flashcards">
      <div className="vd-flashcard-column">
        <div className={`vd-flashcard ${flipped ? "is-flipped" : ""}`}>
          <div className="vd-flashcard-inner">
            <button
              className="vd-flashcard-face vd-flashcard-front"
              onClick={() => setFlipped(true)}
              aria-label="翻看答案"
              aria-hidden={flipped}
              inert={flipped ? "" : undefined}
            >
              <div className="vd-flashcard-meta">
                <span>{title}</span>
                <small>{String(index + 1).padStart(2, "0")} / {sections.length}</small>
              </div>
              <div className="vd-flashcard-question">
                <h2>{current.title}</h2>
                <p>回想这一节的关键内容，点击查看答案。</p>
                <RotateCcw />
              </div>
            </button>
            <section
              className="vd-flashcard-face vd-flashcard-back"
              aria-label="卡片答案"
              aria-hidden={!flipped}
              inert={!flipped ? "" : undefined}
            >
              <div className="vd-flashcard-meta">
                <span>{current.title}</span>
                <small>{String(index + 1).padStart(2, "0")} / {sections.length}</small>
              </div>
              <div className="vd-flashcard-answer" role="region" aria-label="答案原文" tabIndex={flipped ? 0 : -1}>
                <ReactMarkdown components={{ img: () => null }}>{current.content}</ReactMarkdown>
              </div>
              <div className="vd-modal-actions">
                <Button onClick={() => mark(false)}><RotateCcw />需要巩固</Button>
                <Button onClick={() => mark(true)}><CheckCircle />已掌握</Button>
              </div>
              {error && <p role="alert">{error}</p>}
            </section>
          </div>
        </div>

      </div>
      <aside className="vd-panel vd-study-sidebar">
        <h2>本次复习</h2>
        <div className="vd-review-counts">
          <div>
            已掌握<strong>{masteredCount}</strong>
          </div>
          <div>
            待巩固<strong>{sections.length - masteredCount}</strong>
          </div>
        </div>
        <div className="vd-progress">
          <i style={{ width: `${(masteredCount / sections.length) * 100}%` }} />
        </div>
        <p className="vd-muted">
          {sections.length} 张卡片 ·{" "}
          {Math.round((masteredCount / sections.length) * 100)}%
        </p>
        <h3>本组卡片</h3>
        <nav aria-label="复习卡片目录">
          {sections.map((section, i) => (
            <button
              key={section.id}
              aria-current={index === i ? "step" : undefined}
              onClick={() => go(i)}
            >
              {section.title}
              {mastered.includes(`${section.id}:${section.content}`) && (
                <CheckCircle size={14} />
              )}
            </button>
          ))}
        </nav>
      </aside>
        <div className="vd-card-controls">
          <Button disabled={index === 0} onClick={() => go(index - 1)}>
            <ArrowLeft />
            上一张
          </Button>
          <Button
            variant="primary"
            onClick={() => setFlipped((value) => !value)}
          >
            <RotateCcw />
            翻转卡片
          </Button>
          <Button
            disabled={index === sections.length - 1}
            onClick={() => go(index + 1)}
          >
            下一张
            <ArrowRight />
          </Button>
        </div>

    </div>
  );
}
