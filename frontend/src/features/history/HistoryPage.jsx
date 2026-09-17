import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { App, Dropdown, Pagination } from "antd";
import {
  Plus,
  Search,
  Check,
  AlertCircle,
  MoreHorizontal,
  Trash2,
} from "lucide-react";
import MediaCover from "../../components/lake/MediaCover";
import {
  Button,
  EmptyState,
  Segmented,
  Workspace,
} from "../../shared/ui/Workspace";
import { useHistory } from "./useHistory";
import { groupHistory, historySamples, STATUS_OPTIONS } from "./model";

export default function HistoryPage({
  onViewReport,
  onBack,
  currentTask,
  onBackToProcessing,
}) {
  const { modal, message } = App.useApp();
  const navigate = useNavigate();
  const { search } = useLocation();
  const preview =
    ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname) &&
    new URLSearchParams(search).get("preview") === "states";
  const { records, loading, error, refresh, remove } = useHistory();
  const [dismissed, setDismissed] = useState([]);
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const all = preview
    ? [
        ...historySamples.filter((item) => !dismissed.includes(item.id)),
        ...records,
      ]
    : records;
  const filtered = all
    .filter(
      (item) =>
        (status === "all" || item.status === status) &&
        `${item.videoName} ${item.platform || ""}`
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
    )
    .sort(
      (a, b) => (Date.parse(b.createdAt) || 0) - (Date.parse(a.createdAt) || 0),
    );
  const current = Math.min(page, Math.max(1, Math.ceil(filtered.length / 6)));
  const groups = groupHistory(filtered.slice((current - 1) * 6, current * 6));
  const confirmDelete = (item) =>
    modal.confirm({
      title: "删除这条记录？",
      content: item.preview
        ? "仅移除当前示例。"
        : "将删除任务及生成的报告，无法撤销。",
      okText: "删除",
      cancelText: "保留",
      okButtonProps: { danger: true },
      onOk: async () => {
        if (item.preview) {
          setDismissed((ids) => [...ids, item.id]);
          return;
        }
        try {
          await remove(item.id);
          if (currentTask === item.id) {
            localStorage.removeItem("videodevour_current_task");
            onBackToProcessing?.();
          }
        } catch (e) {
          message.error(e.message);
          throw e;
        }
      },
    });
  const toolbar = (
    <>
      <Segmented
        label="处理状态"
        value={status}
        onChange={(value) => {
          setStatus(value);
          setPage(1);
        }}
        options={STATUS_OPTIONS.map(([value, label]) => ({
          value,
          label,
          count:
            value === "all"
              ? all.length
              : all.filter((item) => item.status === value).length,
        }))}
      />
      <label className="vd-search">
        <Search />
        <input
          aria-label="搜索处理记录"
          placeholder="搜索处理记录…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(1);
          }}
        />
      </label>
    </>
  );
  return (
    <Workspace
      className="vd-history"
      title="每一次探索，都在这里。"
      description="查看整理进度，继续未完成的思考。"
      actions={
        <Button variant="primary" onClick={onBack}>
          <Plus />
          添加视频
        </Button>
      }
      toolbar={toolbar}
      footer={
        <>
          <span>共 {filtered.length} 条记录</span>
          <Pagination
            current={current}
            total={filtered.length}
            pageSize={6}
            showSizeChanger={false}
            onChange={setPage}
          />
        </>
      }
    >
      {preview && (
        <div className="vd-notice">
          样式预览 · 进度与失败记录为示例
          <Button
            variant="quiet"
            onClick={() => navigate("/history", { replace: true })}
          >
            退出预览
          </Button>
        </div>
      )}
      {loading ? (
        <EmptyState loading title="正在读取处理记录" />
      ) : error ? (
        <EmptyState
          icon={AlertCircle}
          title="读取失败"
          description={error}
          action={<Button onClick={refresh}>重新加载</Button>}
        />
      ) : !filtered.length ? (
        <EmptyState
          title={
            query || status !== "all"
              ? "没有符合条件的记录"
              : "每一次探索，从这里开始。"
          }
          action={
            <Button variant="primary" onClick={onBack}>
              导入视频
            </Button>
          }
        />
      ) : (
        groups.map((group) => (
          <section className="vd-history-group" key={group.key}>
            <h2>
              {group.label}
              <small>{group.items.length}</small>
              <span />
            </h2>
            {group.items.map((item, index) => (
              <article className="vd-history-row" key={item.id}>
                <div className="vd-history-cover">
                  <MediaCover video={item} index={index} />
                  {item.duration && <span>{item.duration}</span>}
                </div>
                <div className="vd-history-info">
                  <h3 title={item.videoName}>
                    {item.videoName?.replace(/\.(mp4|mov|mkv|webm)$/i, "")}
                    {item.preview && <small>示例</small>}
                  </h3>
                  <p>
                    {new Date(item.createdAt).toLocaleDateString("zh-CN")}
                    <span>·</span>
                    {item.platform || "本地上传"}
                  </p>
                </div>
                <div className={`vd-history-status is-${item.status}`}>
                  {item.status === "processing" ? (
                    <div>
                      <p>
                        <strong>处理中</strong>{" "}
                        {Math.max(0, Math.min(100, item.progress || 0))}%
                      </p>
                      <div
                        className="vd-progress"
                        role="progressbar"
                        aria-label="处理进度"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.max(
                          0,
                          Math.min(100, item.progress || 0),
                        )}
                      >
                        <i
                          style={{
                            width: `${Math.max(0, Math.min(100, item.progress || 0))}%`,
                          }}
                        />
                      </div>
                      <small title={item.message}>
                        {item.message || "正在整理…"}
                      </small>
                    </div>
                  ) : (
                    <>
                      <span className="vd-status-icon">
                        {item.status === "completed" ? (
                          <Check />
                        ) : (
                          <AlertCircle />
                        )}
                      </span>
                      <div>
                        <strong>
                          {item.status === "completed" ? "已完成" : "处理失败"}
                        </strong>
                        <small title={item.message}>
                          {item.status === "completed"
                            ? "报告已就绪"
                            : item.message || "请检查设置后重新导入"}
                        </small>
                      </div>
                    </>
                  )}
                </div>
                <Button
                  className="vd-history-action"
                  variant={item.status === "failed" ? "danger" : "secondary"}
                  onClick={() =>
                    item.preview
                      ? message.info("这是样式预览示例，未运行真实任务。")
                      : item.status === "completed"
                        ? onViewReport(item)
                        : item.status === "processing"
                          ? navigate(`/processing/${item.id}`)
                          : navigate("/link")
                  }
                >
                  {item.status === "completed"
                    ? "查看报告"
                    : item.status === "processing"
                      ? "查看进度"
                      : "重新导入"}
                </Button>
                <Dropdown
                  trigger={["click"]}
                  menu={{
                    items: [
                      {
                        key: "delete",
                        label: "删除记录",
                        icon: <Trash2 size={16} />,
                        danger: true,
                        onClick: () => confirmDelete(item),
                      },
                    ],
                  }}
                >
                  <button
                    className="vd-history-more"
                    aria-label={`更多操作：${item.videoName}`}
                  >
                    <MoreHorizontal />
                  </button>
                </Dropdown>
              </article>
            ))}
          </section>
        ))
      )}
    </Workspace>
  );
}
