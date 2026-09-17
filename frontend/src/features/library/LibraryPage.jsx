import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Search,
  LayoutGrid,
  List,
  Download,
  Bookmark,
  PlaySquare,
  AlertCircle,
} from "lucide-react";
import { WorkspaceSelect } from "../../components/ui/Controls";
import MediaCover from "../../components/lake/MediaCover";
import { triggerDownload } from "../../utils/helpers";
import {
  Button,
  EmptyState,
  Segmented,
  Workspace,
} from "../../shared/ui/Workspace";
import { useLibrary } from "./useLibrary";

const scopes = [
  { value: "all", label: "全部" },
  { value: "outline", label: "图文大纲" },
  { value: "report", label: "精简报告" },
  { value: "detailed", label: "详细报告" },
];
function readBookmarks() {
  try {
    const value = JSON.parse(
      localStorage.getItem("videodevour-bookmarks") || "[]",
    );
    return Array.isArray(value)
      ? value.filter((item) => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}
const snippet = (value) =>
  (value || "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/[#*`>]/g, "")
    .trim();

export default function LibraryPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") || "");
  const [scope, setScope] = useState("all");
  const [view, setView] = useState("cards");
  const [sort, setSort] = useState("recent");
  const [bookmarks, setBookmarks] = useState(readBookmarks);
  const [storageError, setStorageError] = useState("");
  const { data, loading, error, reload } = useLibrary(query, scope);
  const searching = !!query.trim();
  const items = (data?.results || []).filter(
    (video) =>
      searching ||
      scope === "all" ||
      video.versions?.some((run) =>
        run.articles?.some((article) => article.scope === scope),
      ),
  );
  if (sort === "title")
    items.sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
  else if (!searching)
    items.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const toggleBookmark = (key) => {
    const next = bookmarks.includes(key)
      ? bookmarks.filter((item) => item !== key)
      : [...bookmarks, key];
    try {
      localStorage.setItem("videodevour-bookmarks", JSON.stringify(next));
      setBookmarks(next);
      setStorageError("");
    } catch {
      setStorageError("浏览器无法保存收藏标记，请检查存储权限。");
    }
  };
  const open = (item) => {
    const params = new URLSearchParams();
    const run = searching ? item.run_id : item.versions?.[0]?.run_id;
    if (run) params.set("run", run);
    if (searching || scope !== "all")
      params.set("scope", searching ? item.scope : scope);
    navigate(`/library/video/${encodeURIComponent(item.video_key)}?${params}`);
  };
  return (
    <Workspace
      className="vd-library"
      title="你的知识收藏"
      description="为每一次好奇，留一个位置。"
      actions={
        <label className="vd-search">
          <Search />
          <input
            aria-label="搜索知识库"
            placeholder="搜索标题、关键词或观点…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      }
      toolbar={
        <>
          <Segmented
            label="内容类型"
            variant="dark"
            options={scopes}
            value={scope}
            onChange={setScope}
          />
          <div className="vd-library-tools">
            <span>
              {searching
                ? `${data?.total || 0} 条结果`
                : `${items.length} 个视频`}
            </span>
            <WorkspaceSelect
              aria-label="知识库排序"
              value={sort}
              onChange={setSort}
              options={[
                { value: "recent", label: searching ? "相关度" : "最近整理" },
                { value: "title", label: "标题排序" },
              ]}
            />
            <Segmented
              label="知识库视图"
              variant="dark"
              value={view}
              onChange={setView}
              options={[
                {
                  value: "cards",
                  label: <LayoutGrid size={18} />,
                  ariaLabel: "卡片视图",
                },
                {
                  value: "list",
                  label: <List size={18} />,
                  ariaLabel: "列表视图",
                },
              ]}
            />
            <Button
              variant="quiet"
              onClick={() => triggerDownload("/api/library/export")}
              aria-label="整库导出 ZIP"
              title="整库导出 ZIP"
            >
              <Download />
            </Button>
          </div>
        </>
      }
    >
      {storageError && <p role="alert">{storageError}</p>}
      {loading ? (
        <EmptyState loading title="正在整理你的知识收藏" />
      ) : error ? (
        <EmptyState
          icon={AlertCircle}
          title="知识库读取失败"
          description={error}
          action={<Button onClick={reload}>重新加载</Button>}
        />
      ) : !items.length ? (
        <EmptyState
          title={searching ? "没有找到相关内容" : "你的知识收藏，从这里开始。"}
          description={
            searching
              ? "换一个关键词，或选择其他内容类型。"
              : "导入视频，提炼重点、梳理思考，让碎片的观看变成系统的知识积累。"
          }
          action={
            <Button variant="primary" onClick={() => navigate("/link")}>
              导入第一段视频
            </Button>
          }
        />
      ) : (
        <div className={`vd-library-grid is-${view}`}>
          {items.map((item, index) => {
            const key = searching
              ? `${item.doc_id}-${item.scope}`
              : item.video_key;
            const version = searching
              ? item.version_label
              : item.versions?.[0]?.version_label;
            return (
              <article
                className={`vd-knowledge-card ${searching ? "is-search-result" : ""}`}
                key={key}
              >
                <button
                  className="vd-knowledge-open"
                  onClick={() => open(item)}
                  aria-label={`阅读：${item.title}`}
                >
                  <MediaCover video={item} index={index} />
                  <div className="vd-knowledge-caption">
                    <h2>{item.title}</h2>
                    {(searching || view === "list") && (
                      <p className="vd-knowledge-snippet">
                        {snippet(item.snippet)}
                      </p>
                    )}
                    <div className="vd-knowledge-meta">
                      <PlaySquare size={17} />
                      <span>
                        {item.platform_label || "本地上传"} ·{" "}
                        {searching
                          ? item.label
                          : `${item.version_count || 1} 个版本`}
                      </span>
                      {version && <small>{version}</small>}
                    </div>
                  </div>
                </button>
                <button
                  className="vd-bookmark"
                  aria-label={`${bookmarks.includes(item.video_key) ? "取消" : "标记"}收藏：${item.title}`}
                  aria-pressed={bookmarks.includes(item.video_key)}
                  onClick={() => toggleBookmark(item.video_key)}
                >
                  <Bookmark
                    fill={
                      bookmarks.includes(item.video_key)
                        ? "currentColor"
                        : "none"
                    }
                  />
                </button>
              </article>
            );
          })}
        </div>
      )}
    </Workspace>
  );
}
