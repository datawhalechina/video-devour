import { PageHeader } from "../shared/ui/Workspace";
import { useLibrary } from "../features/library/useLibrary";
import { useTheme } from "../theme/themeContext";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Link2,
  Upload,
  BookOpen,
  RefreshCw,
  LayoutGrid,
  List,
  PlaySquare,
  ChevronRight,
  ChevronDown,
  Plus,
} from "lucide-react";
import MediaCover from "./lake/MediaCover";

const destination = (video) =>
  `/library/video/${encodeURIComponent(video.video_key)}`;
const dateLabel = (value) =>
  value
    ? new Date(value).toLocaleDateString("zh-CN", {
        month: "short",
        day: "numeric",
      })
    : "";
export default function LandingPage() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const { data, loading, error, reload } = useLibrary("", "all");
  const documents = data?.results || [];
  const [view, setView] = useState("cards");
  const [collectionOpen, setCollectionOpen] = useState(true);
  const [recentOpen, setRecentOpen] = useState(true);
  const start = (event) => {
    event.preventDefault();
    if (url.trim()) navigate("/link", { state: { url: url.trim() } });
  };
  return (
    <main className="vd-page vd-home">
      <section className="vd-home-welcome">
        <PageHeader
          title={
            theme === "coast"
              ? "让每一次观看，都有所收获。"
              : "把好奇心，变成知识。"
          }
        />
        <div className="vd-home-quick-import">
          <form onSubmit={start} className="vd-home-url-composer">
            <Link2 size={22} aria-hidden="true" />
            <input
              aria-label="视频链接或分享文案"
              placeholder="粘贴视频链接，开始整理"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button
              disabled={!url.trim()}
              aria-label="开始整理"
              title="开始整理"
            >
              <ArrowRight size={23} />
            </button>
          </form>
          <span className="vd-home-import-divider" />
          <Link to="/upload" className="vd-home-upload-link">
            <Upload size={21} />
            上传视频
          </Link>
        </div>
        <p
          className="vd-home-import-description"
          title="从一段视频开始，提炼重点、梳理思考，让每一次观看，都成为你的知识积累。"
        >
          从一段视频开始，提炼重点、梳理思考，让每一次观看，都成为你的知识积累。
        </p>
      </section>
      <div className="vd-home-panels">
        <section
          data-expanded={collectionOpen}
          className="vd-home-collection"
          aria-labelledby="collection-title"
        >
          <div className="vd-home-section-heading">
            <h2 id="collection-title">
              <button
                className="vd-home-section-toggle"
                aria-expanded={collectionOpen}
                aria-controls="home-collection-body"
                onClick={() => setCollectionOpen((open) => !open)}
              >
                你的知识收藏
                <ChevronDown aria-hidden="true" />
              </button>
            </h2>
            {theme === "coast" ? (
              <Link to="/library">
                查看全部
                <ChevronRight size={15} />
              </Link>
            ) : (
              <div className="vd-home-view-switch" aria-label="收藏视图">
                <button
                  aria-label="卡片视图"
                  aria-pressed={view === "cards"}
                  onClick={() => setView("cards")}
                >
                  <LayoutGrid size={16} />
                  <span>卡片视图</span>
                </button>
                <button
                  aria-label="列表视图"
                  aria-pressed={view === "list"}
                  onClick={() => setView("list")}
                >
                  <List size={16} />
                  <span>列表视图</span>
                </button>
              </div>
            )}
          </div>
          <div
            id="home-collection-body"
            className="vd-home-panel-body"
            hidden={!collectionOpen}
            tabIndex={collectionOpen ? 0 : -1}
            aria-label="知识收藏内容"
          >
            {loading ? (
              <div className="vd-home-loading" role="status">
                正在打开你的知识空间…
              </div>
            ) : error ? (
              <div className="vd-home-empty" role="alert">
                <BookOpen size={30} />
                <h3>暂时无法加载知识笔记</h3>
                <p>请检查服务连接，或稍后重试。</p>
                <button className="vd-button" onClick={() => reload()}>
                  <RefreshCw size={16} />
                  重新加载
                </button>
              </div>
            ) : documents.length ? (
              <div
                className={`vd-home-featured ${view === "list" ? "is-list" : ""} ${documents.length === 1 ? "has-one" : ""} ${documents.length === 2 ? "has-two" : ""}`}
              >
                {documents.slice(0, 3).map((video, i) => (
                  <Link
                    to={destination(video)}
                    key={video.video_key}
                    className="vd-home-feature-card"
                  >
                    <MediaCover video={video} index={i} />
                    <div className="vd-home-feature-caption">
                      <h3>{video.title}</h3>
                      <div>
                        <PlaySquare size={15} />
                        <span>
                          {video.platform_label} · {video.version_count} 个版本
                        </span>
                        <ChevronRight size={18} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="vd-home-empty vd-home-first-note">
                <BookOpen size={34} />
                <h3>你的知识收藏，从第一段视频开始</h3>
                <p>添加视频后，图文大纲和学习笔记会收录在这里。</p>
                <Link to="/link" className="vd-button vd-button--primary">
                  <Plus size={17} />
                  整理第一段视频
                </Link>
              </div>
            )}
          </div>
        </section>
        <section
          data-expanded={recentOpen}
          className="vd-home-recent"
          aria-labelledby="recent-title"
        >
          <div className="vd-home-section-heading">
            <h2 id="recent-title">
              <button
                className="vd-home-section-toggle"
                aria-expanded={recentOpen}
                aria-controls="home-recent-body"
                onClick={() => setRecentOpen((open) => !open)}
              >
                最近整理
                <ChevronDown aria-hidden="true" />
              </button>
            </h2>
            <Link to="/history">
              查看全部
              <ChevronRight size={15} />
            </Link>
          </div>
          <div
            id="home-recent-body"
            className="vd-home-panel-body"
            hidden={!recentOpen}
            tabIndex={recentOpen ? 0 : -1}
            aria-label="最近整理内容"
          >
            <div className="vd-home-recent-grid">
              {documents.slice(0, 3).map((video, i) => (
                <Link
                  key={video.video_key}
                  to={destination(video)}
                  className="vd-home-recent-item"
                >
                  <MediaCover video={video} index={i} />
                  <div>
                    <h3>{video.title}</h3>
                    <p>
                      {dateLabel(video.created_at)} · {video.platform_label}
                    </p>
                  </div>
                </Link>
              ))}
              {!loading && !documents.length && (
                <p className="vd-home-muted">
                  每一份新的笔记，都会在这里留下记录。
                </p>
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
