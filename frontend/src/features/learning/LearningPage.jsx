import ContentNavigation from "../../shared/reader/ContentNavigation";
import { LEARNING_KEYS } from "../../shared/reader/contentOptions";
import { isLearningPreview } from "./preview";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, RefreshCw, Download } from "lucide-react";
import { App } from "antd";
import { Workspace, Button, EmptyState } from "../../shared/ui/Workspace";
import { useConfigGate } from "../../components/ConfigGateProvider";
import { learningRequest } from "./api";
import {
  cachedGraph,
  cachedMindmap,
  markdownGraph,
  reportSections,
  learningKinds,
} from "./model";
import MapCanvas from "./MapCanvas";
import MindmapEditor from "../mindmap/MindmapEditor";
import Flashcards from "./Flashcards";
import QuizWorkspace from "./QuizWorkspace";
import { triggerDownload } from "../../utils/helpers";

export default function LearningPage() {
  const { taskId, kind = "mindmap" } = useParams();
  const { state } = useLocation();
  const reader = state?.reader || { path: `/report/${taskId}` };
  const openContent = (key) => {
    if (LEARNING_KEYS.includes(key))
      navigate(`/learn/${taskId}/${key}`, { state: { reader } });
    else {
      const params = new URLSearchParams({ scope: key });
      if (reader.run) params.set("run", reader.run);
      navigate(`${reader.path}?${params}`);
    }
  };
  const navigate = useNavigate(),
    { message } = App.useApp(),
    { guardConfig } = useConfigGate();
  const [report, setReport] = useState(null),
    [cached, setCached] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setReport(null);
    setCached(null);
    Promise.all([
      learningRequest(taskId, "report"),
      kind === "mindmap" || kind === "graph"
        ? learningRequest(taskId, kind === "graph" ? "knowledge-graph" : kind)
        : Promise.resolve(null),
    ])
      .then(([data, artifact]) => {
        if (active) {
          setReport(data);
          setCached(artifact);
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [taskId, kind]);
  const markdown =
    report?.final_report ||
    report?.detailed_outline ||
    report?.detailed_report ||
    "";
  const parsed = useMemo(() => reportSections(markdown), [markdown]);
  const title = parsed.title || report?.video_name || "视频知识";
  const graph = useMemo(
    () =>
      kind === "graph"
        ? cachedGraph(cached?.html)
        : markdownGraph(cachedMindmap(cached?.html) || markdown, title),
    [kind, cached, markdown, title],
  );
  const generate = async () => {
    if (isLearningPreview(taskId)) {
      message.info("这是本地样式预览，不会调用模型服务。");
      return;
    }
    if (!(await guardConfig(["llm"]))) return;
    setBusy(true);
    try {
      const endpoint =
        kind === "graph"
          ? "knowledge-graph"
          : kind === "cards"
            ? "card"
            : "mindmap";
      await learningRequest(taskId, endpoint, {});
      if (kind === "cards") {
        triggerDownload(`/static/${report.output_dir}/learning_card.html`);
      } else {
        setCached(await learningRequest(taskId, endpoint));
      }
      message.success(
        kind === "mindmap"
          ? "生成内容已就绪，可在导图工具栏导入；当前编辑已保留"
          : "已读取生成内容",
      );
    } catch (e) {
      message.error(e.message);
    } finally {
      setBusy(false);
    }
  };
  if (!learningKinds.includes(kind))
    return (
      <EmptyState
        title="找不到这个学习页面"
        action={
          <Button onClick={() => navigate(`/learn/${taskId}/mindmap`)}>
            进入学习
          </Button>
        }
      />
    );
  const headline =
    kind === "cards"
      ? "温故，让知识留下来。"
      : kind === "quiz"
        ? "看看你，真正记住了多少。"
        : title;
  const description =
    kind === "cards"
      ? "回顾关键内容，让看过的知识成为长期记忆。"
      : kind === "quiz"
        ? "通过练习检验学习效果，加深理解。"
        : kind === "graph"
          ? "连接概念，发现知识之间的关联。"
          : "从内容中梳理脉络，让思路清晰可见。";
  return (
    <Workspace
      className={`vd-learning ${kind === "mindmap" || kind === "graph" ? "vd-learning-map" : ""}`}
      title={headline}
      description={description}
      actions={
        <Button
          variant="quiet"
          onClick={() =>
            navigate(
              isLearningPreview(taskId)
                ? "/library"
                : `${reader.path}${reader.run ? `?run=${encodeURIComponent(reader.run)}` : ""}`,
            )
          }
        >
          <ArrowLeft />
          返回报告
        </Button>
      }
      toolbar={
        <>
          <ContentNavigation value={kind} onChange={openContent} />
          {kind !== "quiz" && (
            <Button disabled={busy || !report} onClick={generate}>
              {kind === "cards" ? <Download /> : <RefreshCw />}
              {busy
                ? "生成中…"
                : kind === "cards"
                  ? "下载生成版卡片"
                  : cached
                    ? "读取生成版本"
                    : "生成学习内容"}
            </Button>
          )}
        </>
      }
    >
      {isLearningPreview(taskId) && (
        <p className="vd-notice">
          本地样式预览 · 示例知识与练习，不属于真实任务
        </p>
      )}
      {loading ? (
        <EmptyState loading title="正在读取学习内容" />
      ) : error ? (
        <EmptyState
          title="读取失败"
          description={error}
          action={
            <Button
              onClick={() =>
                navigate(
                  isLearningPreview(taskId)
                    ? "/library"
                    : `${reader.path}${reader.run ? `?run=${encodeURIComponent(reader.run)}` : ""}`,
                )
              }
            >
              返回报告
            </Button>
          }
        />
      ) : kind === "cards" ? (
        <Flashcards
          key={taskId}
          taskId={taskId}
          title={title}
          sections={parsed.sections}
        />
      ) : kind === "quiz" ? (
        <QuizWorkspace key={taskId} taskId={taskId} report={report} />
      ) : (
        <>
          <p className="vd-learning-source">
            {cached
              ? "已生成的学习内容"
              : kind === "graph"
                ? "生成知识图谱，查看概念之间的关系。"
                : "当前展示报告章节结构，可生成进一步提炼的思维导图。"}
          </p>
          {kind === "mindmap" && !isLearningPreview(taskId) ? (
            <MindmapEditor taskId={taskId} graph={graph} run={reader.run} />
          ) : (
            <MapCanvas key={`${taskId}-${kind}`} graph={graph} />
          )}
        </>
      )}
    </Workspace>
  );
}
