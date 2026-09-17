import { SiBilibili, SiYoutube, SiTiktok } from "react-icons/si";
import { PageHeader } from "../../shared/ui/Workspace";
import { App as AntApp } from "antd";
import { Input, Radio as ChoiceRadio } from "antd";
import { WorkspaceSelect } from "../../components/ui/Controls";
import ImportTabs from "../../components/lake/ImportTabs";
import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Link2,
  Search,
  Download,
  Loader2,
  Play,
  AlertCircle,
  MessageCircle,
  KeyRound,
  NotebookPen,
} from "lucide-react";
import {
  getLinkInfo,
  searchLinkVideos,
  processLink,
  generateSubtitleNotes,
} from "../../api/videoService";
import ExtrasPicker, { getSelectedExtras } from "../../components/ExtrasPicker";
import { useConfigGate } from "../../components/ConfigGateProvider";

const PLATFORM_TABS = [
  {
    key: "bilibili",
    label: "B站",
    embed: (id) =>
      `https://player.bilibili.com/player.html?bvid=${id}&autoplay=0`,
  },
  {
    key: "youtube",
    label: "YouTube",
    embed: (id) => `https://www.youtube.com/embed/${id}`,
  },
  { key: "douyin", label: "抖音", embed: null }, // 抖音无可公开内嵌播放器
];

const PLATFORM_LABELS = {
  bilibili: "B站",
  youtube: "YouTube",
  wechat: "微信视频号",
  douyin: "抖音",
};

function formatDuration(seconds) {
  if (!seconds) return "未知";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

function LinkProcess() {
  const { message } = AntApp.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const { guardConfig } = useConfigGate();
  const [url, setUrl] = useState(location.state?.url || "");
  const [query, setQuery] = useState("");
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [platform, setPlatform] = useState("bilibili");
  const [educationLevel, setEducationLevel] = useState("自由学习");
  const [outputMode, setOutputMode] = useState("report");
  const [results, setResults] = useState([]);
  const [preview, setPreview] = useState(null); // 预览窗视频信息
  const [previewLoading, setPreviewLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [notesLoading, setNotesLoading] = useState(false);
  const [notesResult, setNotesResult] = useState(null);
  const [error, setError] = useState(null);

  const embedUrl = (item) => {
    const tab = PLATFORM_TABS.find((t) => t.key === item.platform);
    // embed 可能为 null（如抖音无可公开内嵌播放器），必须判可调用，
    // 否则空调用会让整个页面崩溃白屏
    return tab && typeof tab.embed === "function" && item.video_id
      ? tab.embed(item.video_id)
      : null;
  };

  const showError = (msg) => setError(msg);

  const handleProbe = async () => {
    const link = url.trim();
    if (!link) return;
    setPreviewLoading(true);
    setError(null);
    try {
      const info = await getLinkInfo(link);
      setPreview(info);
      setResults([]);
    } catch (err) {
      showError(`获取视频信息失败: ${err.message}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSearch = async (kw) => {
    const keyword = (kw ?? query).trim();
    if (!keyword) return;
    setSearchLoading(true);
    setError(null);
    try {
      const data = await searchLinkVideos(keyword, platform, 8);
      setResults(data.results || []);
      setPreview(null);
    } catch (err) {
      showError(`搜索失败: ${err.message}`);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleProcess = async (link) => {
    if (processing) return;
    // 未配置 LLM/VLM/ASR 时先引导去设置，避免点完只看到报错
    if (!(await guardConfig(["llm", "vlm", "asr"]))) return;
    setProcessing(true);
    setError(null);
    try {
      const result = await processLink(
        link,
        educationLevel,
        getSelectedExtras(),
      );
      navigate(`/processing/${result.task_id}`);
    } catch (err) {
      showError(`创建任务失败: ${err.message}`);
      setProcessing(false);
    }
  };

  const handleNotes = async () => {
    const link = url.trim();
    if (!link || notesLoading) return;
    // 字幕速记不下载视频、不走 ASR，但需要 LLM 整理要点
    if (!(await guardConfig(["llm"]))) return;
    setNotesLoading(true);
    setError(null);
    setNotesResult(null);
    try {
      const result = await generateSubtitleNotes(link);
      setNotesResult(result);
      document
        .getElementById("workspace-content")
        ?.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      showError(`字幕笔记生成失败: ${err.message}`);
    } finally {
      setNotesLoading(false);
    }
  };

  // 字幕笔记：渲染 Markdown（含 Mermaid 关系图）
  const notesRef = useRef(null);
  useEffect(() => {
    const el = notesRef.current;
    if (!el || !notesResult?.notes) return;
    let cancelled = false;
    const render = async () => {
      const { marked } = await import("marked");
      let html = marked.parse(notesResult.notes);
      // 把 mermaid 代码块转成 <div class="mermaid">，其余保留
      html = html.replace(
        /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,
        (_, code) =>
          `<div class="mermaid">${code.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")}</div>`,
      );
      if (cancelled) return;
      el.innerHTML = html;
      if (html.includes('class="mermaid"')) {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "neutral",
          securityLevel: "loose",
        });
        await mermaid.run({ nodes: el.querySelectorAll(".mermaid") });
      }
    };
    render().catch((err) => console.error("笔记渲染失败:", err));
    return () => {
      cancelled = true;
    };
  }, [notesResult]);

  // 新窗口打开：桌面客户端内 window.open 不可用（WebView 返回 null），
  // 改走原生桥写临时文件后用系统浏览器打开；纯浏览器仍用 Blob URL
  //（用 Blob 而非静态路径，避免中文/特殊字符编码导致打不开）
  const buildNotesHtml =
    () => `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>${notesResult.title}</title>
<style>body{max-width:51.25rem;margin:2rem auto;padding:0 1.25rem;font:0.9375rem/1.8 -apple-system,"PingFang SC",sans-serif;color:#1f2937}
pre{background:#f6f8fa;padding:0.75rem;border-radius:0.5rem;overflow:auto}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
h1,h2,h3{line-height:1.35}</style>
</head><body><pre style="white-space:pre-wrap;font-family:inherit;background:none;padding:0">${notesResult.notes.replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c])}</pre></body></html>`;

  const handleOpenNotesWindow = async () => {
    const html = buildNotesHtml();
    const bridge = window.pywebview?.api;
    if (bridge?.open_html) {
      try {
        await bridge.open_html(html, `字幕笔记-${notesResult.title || ""}`);
        return;
      } catch {
        /* 桥失败时退回窗口方式 */
      }
    }
    const win = window.open("", "_blank");
    if (!win) {
      message.error("浏览器拦截了新窗口，请允许弹窗后重试");
      return;
    }
    win.document.write(html);
    win.document.close();
  };

  const InfoMeta = ({ item }) => (
    <div className="text-sm text-gray-600 space-y-1">
      <p className="font-semibold text-gray-900">{item.title}</p>
      <p className="flex items-center gap-3 text-xs">
        {item.uploader && <span>UP: {item.uploader}</span>}
        {item.duration && <span>时长: {formatDuration(item.duration)}</span>}
        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">
          {PLATFORM_LABELS[item.platform] || "网页"}
        </span>
      </p>
    </div>
  );

  return (
    <div className="vd-page vd-import">
      {/* 顶部导航 */}

      <>
        <PageHeader
          title="整理一段新视频"
          description="从一段视频开始，把灵感留下。"
        />
        <div className="vd-import-layout">
          <div className="vd-import-source">
            <ImportTabs />
            {/* 链接输入 + 搜索区 */}
            <section className="vd-import-inputs">
              <div className="vd-link-input">
                <Link2 className="import-link-icon" aria-hidden="true" />
                <Input
                  allowClear
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleProbe()}
                  aria-label="视频链接或分享文案"
                  placeholder="粘贴视频链接或分享文案…"
                  className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
                />
                <button
                  onClick={handleProbe}
                  disabled={previewLoading || !url.trim()}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
                >
                  {previewLoading && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  <span>预览</span>
                </button>
              </div>

              <p className="import-supported">
                支持 B站、YouTube、抖音 等视频链接
              </p>
              <div className="import-platforms" aria-label="视频平台">
                {PLATFORM_TABS.map((t) => {
                  const Icon = {
                    bilibili: SiBilibili,
                    youtube: SiYoutube,
                    douyin: SiTiktok,
                  }[t.key];
                  return (
                    <button
                      key={t.key}
                      type="button"
                      aria-expanded={searchExpanded && platform === t.key}
                      aria-controls="platform-search-panel"
                      onClick={() => {
                        setPlatform(t.key);
                        setSearchExpanded((open) =>
                          platform === t.key ? !open : true,
                        );
                      }}
                    >
                      <Icon
                        className={`platform-${t.key}`}
                        aria-hidden="true"
                      />
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>
              {searchExpanded && (
                <div
                  id="platform-search-panel"
                  className="import-platform-search"
                >
                  <div className="flex items-center space-x-3">
                    <Input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                      placeholder={`在${{ bilibili: "B站", youtube: "YouTube", douyin: "抖音" }[platform] || ""}搜索视频关键词...`}
                      className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
                    />
                    <button
                      onClick={() => handleSearch()}
                      disabled={searchLoading || !query.trim()}
                      className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
                    >
                      {searchLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                      <span>搜索</span>
                    </button>
                    {platform === "douyin" && (
                      <a
                        href={`https://www.douyin.com/search/${encodeURIComponent(query || "")}`}
                        target="_blank"
                        rel="noreferrer"
                        title="服务端搜索受限，改为浏览器检索（你已登录），找到后复制链接粘贴到上方"
                        className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
                      >
                        <Search className="w-4 h-4" />
                        <span>浏览器搜索</span>
                      </a>
                    )}
                  </div>
                  {platform === "douyin" && (
                    <p className="mt-2 text-xs text-gray-500 leading-relaxed">
                      抖音搜索接口有浏览器签名校验（反爬），服务端无法直接检索。请用右侧「浏览器搜索」打开抖音搜索，
                      找到视频后复制链接粘贴到上方输入框即可处理（你浏览器的登录态天然可用）。
                    </p>
                  )}
                </div>
              )}

              {/* 预览窗口 */}
              {(preview || previewLoading) && (
                <section className="vd-video-preview">
                  {previewLoading ? (
                    <div className="h-[26.25rem] flex items-center justify-center text-gray-400">
                      <Loader2 className="w-8 h-8 animate-spin" />
                    </div>
                  ) : (
                    preview && (
                      <div className="import-video-detail">
                        <div className="vd-video-frame">
                          {embedUrl(preview) ? (
                            <iframe
                              key={preview.webpage_url}
                              src={embedUrl(preview)}
                              className="w-full h-[26.25rem]"
                              frameBorder="0"
                              allowFullScreen
                              allow="encrypted-media; fullscreen"
                              title={preview.title}
                            />
                          ) : preview.platform === "wechat" ||
                            preview.platform === "douyin" ? (
                            <div className="w-full h-[26.25rem] flex flex-col items-center justify-center gap-3 text-gray-400 px-8 text-center">
                              <MessageCircle className="w-12 h-12" />
                              <p className="text-sm font-medium text-gray-300">
                                {preview.platform === "douyin"
                                  ? "抖音内容不支持网页内嵌预览"
                                  : "微信视频号内容不支持网页内嵌预览"}
                              </p>
                              <p className="text-xs text-gray-500 leading-relaxed">
                                {preview.platform === "douyin"
                                  ? "点击右侧「开始整理」将直接下载并处理；抖音下载需要登录态 Cookie，可在设置页「抖音 cookies」配置（桌面客户端可用「应用内登录读取」，或从浏览器读取/手动粘贴）"
                                  : "点击右侧「开始整理」将调用解析服务下载；若解析失败（链接过期/服务限流），请用本地工具下载后到「上传视频」页上传处理"}
                              </p>
                            </div>
                          ) : (
                            preview.thumbnail && (
                              <img
                                src={preview.thumbnail}
                                alt={preview.title}
                                referrerPolicy="no-referrer"
                                className="w-full h-[26.25rem] object-contain"
                              />
                            )
                          )}
                        </div>
                        <div className="vd-video-meta">
                          <InfoMeta item={preview} />
                          {preview.description && (
                            <p className="mt-3 text-xs text-gray-500 leading-relaxed line-clamp-6">
                              {preview.description}
                            </p>
                          )}
                          <p className="mt-4 text-xs text-gray-400">
                            链接：{preview.webpage_url}
                          </p>
                        </div>
                      </div>
                    )
                  )}
                </section>
              )}
            </section>

            {error && (
              <div className="flex items-center space-x-2 p-4 bg-red-50 border-l-4 border-red-500 rounded-xl text-red-700 text-sm">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="flex-1">{error}</span>
                {/Cookie/.test(error) && (
                  <button
                    onClick={() => navigate("/settings")}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold flex-shrink-0 transition"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>去配置 Cookie</span>
                  </button>
                )}
                {platform === "douyin" && (
                  <a
                    href={`https://www.douyin.com/search/${encodeURIComponent(query || "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold flex-shrink-0 transition"
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>打开抖音搜索</span>
                  </a>
                )}
              </div>
            )}

            {/* 字幕笔记结果 */}
            {notesResult && (
              <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="p-5 border-b border-gray-100 flex items-center justify-between">
                  <h2 className="text-base font-bold text-gray-900 flex items-center space-x-2">
                    <NotebookPen className="w-5 h-5 text-primary-600" />
                    <span>字幕笔记：{notesResult.title}</span>
                  </h2>
                  <div className="flex items-center gap-2">
                    <a
                      href={notesResult.md_url}
                      className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700"
                    >
                      下载 Markdown
                    </a>
                    <a
                      href={notesResult.txt_url}
                      className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                    >
                      下载 .txt
                    </a>
                    {notesResult.pdf_url && (
                      <a
                        href={notesResult.pdf_url}
                        className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700"
                      >
                        下载 PDF
                      </a>
                    )}
                    <button
                      onClick={handleOpenNotesWindow}
                      className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                    >
                      新窗口打开
                    </button>
                  </div>
                </div>
                <div className="p-5">
                  <p className="text-xs text-gray-400 mb-3">
                    来源：
                    {notesResult.platform === "bilibili" ? "B站" : "YouTube"}{" "}
                    字幕（{notesResult.lang}）· Markdown 笔记（含概念关系图）
                  </p>
                  <div
                    className="markdown-body text-sm text-gray-800 leading-relaxed"
                    ref={notesRef}
                  />
                </div>
              </section>
            )}

            {/* 搜索结果卡片 */}
            {results.length > 0 && (
              <section className="space-y-3">
                <h2 className="text-base font-bold text-gray-900">搜索结果</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {results.map((item, idx) => (
                    <motion.div
                      key={item.webpage_url || idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex hover:shadow-md transition-shadow"
                    >
                      <div
                        className="relative w-44 flex-shrink-0 cursor-pointer bg-gray-100"
                        onClick={() => {
                          setPreview(item);
                          setUrl(item.webpage_url || "");
                          document
                            .querySelector(".vd-import-source")
                            ?.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                      >
                        {item.thumbnail ? (
                          <img
                            src={item.thumbnail}
                            alt={item.title}
                            referrerPolicy="no-referrer"
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              e.target.style.display = "none";
                            }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-300">
                            <Play className="w-8 h-8" />
                          </div>
                        )}
                        {item.duration && (
                          <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs">
                            {formatDuration(item.duration)}
                          </span>
                        )}
                      </div>
                      <div className="p-4 flex flex-col justify-between flex-1">
                        <InfoMeta item={item} />
                        <div className="flex items-center gap-2 mt-3">
                          <button
                            onClick={() => {
                              setPreview(item);
                              setUrl(item.webpage_url || "");
                              document
                                .querySelector(".vd-import-source")
                                ?.scrollTo({ top: 0, behavior: "smooth" });
                            }}
                            className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                          >
                            预览
                          </button>
                          <button
                            onClick={() => handleProcess(item.webpage_url)}
                            disabled={processing}
                            className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700 disabled:opacity-50 flex items-center gap-1"
                          >
                            <Download className="w-3.5 h-3.5" />
                            下载处理
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </section>
            )}

            {!preview && !previewLoading && !notesResult && !results.length && (
              <div className="vd-import-empty">
                <Play size={26} />
                <strong>视频预览</strong>
                <span>粘贴链接后，在这里查看视频画面与信息。</span>
              </div>
            )}
          </div>
          <aside className="vd-import-preferences">
            <h2>处理偏好</h2>
            <p>选择你想要的整理方式，AI 将按你的偏好生成内容。</p>
            <fieldset>
              <legend className="sr-only">输出形式</legend>
              <ChoiceRadio.Group
                className="lake-mode-options"
                value={outputMode}
                onChange={(event) => setOutputMode(event.target.value)}
                options={[
                  {
                    value: "report",
                    label: (
                      <span>
                        <NotebookPen size={23} />
                        <strong>图文报告</strong>
                        <small>提炼重点，结构化呈现</small>
                      </span>
                    ),
                  },
                  {
                    value: "notes",
                    label: (
                      <span>
                        <MessageCircle size={23} />
                        <strong>字幕速记</strong>
                        <small>快速整理，保留原话</small>
                      </span>
                    ),
                  },
                ]}
              />
            </fieldset>
            {outputMode === "report" && (
              <>
                <label
                  className="lake-field-label"
                  htmlFor="link-education-level"
                >
                  学习阶段
                </label>
                <p>不同阶段将影响内容的深度与表达方式。</p>
                <WorkspaceSelect
                  id="link-education-level"
                  value={educationLevel}
                  onChange={setEducationLevel}
                  options={[
                    "自由学习",
                    "小学",
                    "初中",
                    "高中",
                    "大学",
                    "硕士",
                    "博士",
                    "深入研究",
                    "垂直领域研究",
                  ].map((value) => ({ value, label: value }))}
                />
                <fieldset>
                  <legend>输出内容（可多选）</legend>
                  <ExtrasPicker />
                </fieldset>
              </>
            )}
            {outputMode === "notes" && (
              <p>字幕速记支持 B站与 YouTube，需要视频包含可用字幕。</p>
            )}
            <button
              className="lake-primary"
              disabled={processing || notesLoading || !url.trim()}
              onClick={() =>
                outputMode === "notes"
                  ? handleNotes()
                  : handleProcess(url.trim())
              }
            >
              {processing || notesLoading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <Play size={18} />
              )}
              {processing || notesLoading ? "正在整理…" : "开始整理"}
            </button>
            <p className="lake-import-hint">
              {outputMode === "notes"
                ? "提取可用字幕，整理后可下载并继续阅读。"
                : "图文报告会提取语音和关键画面，整理为可以阅读、编辑与导出的笔记。"}
            </p>
          </aside>
        </div>
        <p className="vd-import-legal">
          请确保对所处理的视频内容拥有相应权利或已获得授权，仅用于个人学习用途
        </p>
      </>
    </div>
  );
}

export default LinkProcess;
