import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, FileText, Image, Edit3, LayoutGrid, FileDown, ChevronDown, ArrowUpRight, Check,
  Timer, Share2, Network, BookOpen, Link2 } from "lucide-react";

const PLATFORM_LABELS = {
  bilibili: "B站",
  youtube: "YouTube",
  wechat: "微信视频号",
};
import { generateCard, generateMindmap, generateKnowledgeGraph } from "../api/settingsService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';


const ReportViewer = ({ report, onBack, error, onRetry }) => {
  const [activeTab, setActiveTab] = useState("outline");
  const [cardLoading, setCardLoading] = useState(false)
  const [timing, setTiming] = useState(null)
  const [timingLoading, setTimingLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState({});

  // 思维导图 / 知识图谱 / 学习卡片：统一用页面内模态预览。
  // 不用 window.open——应用内浏览器/弹窗拦截会导致静默失败（用户只看到 alert）。
  const [preview, setPreview] = useState(null)   // { title, url }

  const handleOpenHtml = async (kind) => {
    if (htmlLoading[kind]) return;
    const fileName = kind === "mindmap" ? "思维导图" : "知识图谱";
    const cachedPath = kind === "mindmap" ? "mindmap.html" : "knowledge_graph.html";
    setHtmlLoading(prev => ({ ...prev, [kind]: true }));
    try {
      const fn = kind === "mindmap" ? generateMindmap : generateKnowledgeGraph;
      await fn(report.task_id);
      setPreview({
        title: fileName,
        url: `/static/${report.output_dir}/${cachedPath}`,
      });
    } catch (err) {
      alert(`${fileName}生成失败: ${err.message}`);
    } finally {
      setHtmlLoading(prev => ({ ...prev, [kind]: false }));
    }
  };

  // 生成学习卡片（移植自 light 版），页面内模态预览
  const handleGenerateCard = async () => {
    if (cardLoading) return;
    setCardLoading(true);
    try {
      await generateCard(report.task_id);
      setPreview({
        title: "学习卡片",
        url: `/static/${report.output_dir}/learning_card.html`,
      });
    } catch (err) {
      alert(`学习卡片生成失败: ${err.message}`);
    } finally {
      setCardLoading(false);
    }
  };

  // 导出大纲+报告为单个 Markdown 文件（移植自 light 版）
  const handleShowTiming = async () => {
    if (timingLoading) return
    setTimingLoading(true)
    try {
      const res = await fetch(`/api/task/${report.task_id}/timing`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '获取失败')
      setTiming(data)
    } catch (err) {
      alert(`耗时报告获取失败: ${err.message}`)
    } finally {
      setTimingLoading(false)
    }
  }

  const [exportMenu, setExportMenu] = useState(null)   // 当前展开的导出类型

  const doExport = (type, mode) => {
    window.open(`/api/export/${report.task_id}?type=${type}&mode=${mode}`, "_blank");
    setExportMenu(null);
  };

  const exportRef = useRef(null);
  useEffect(() => {
    if (!exportMenu) return;
    const closeOutside = (event) => {
      if (!exportRef.current?.contains(event.target)) setExportMenu(null);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setExportMenu(null);
        exportRef.current?.querySelector('button')?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [exportMenu]);

  // 动态更新页面标题
  useEffect(() => {
    if (report && report.video_name) {
      document.title = `${report.video_name} - 分析报告 | VideoDevour`;
    } else {
      document.title = "视频分析报告 | VideoDevour";
    }
    
    // 组件卸载时恢复默认标题
    return () => {
      document.title = "VideoDevour · 视频知识工作台";
    };
  }, [report]);

  if (error) {
    return <div className="report-empty" role="alert"><FileText size={28} /><h2>暂时无法加载报告</h2><p>{error}</p><button className="report-primary-button mt-5" onClick={onRetry}>重新加载</button></div>;
  }

  if (!report) {
    return (
      <div className="report-loading" role="status" aria-live="polite">
        <div className="eyebrow">VIDEO NOTES</div>
        <p>正在加载视频报告…</p>
        <div className="report-skeleton" /><div className="report-skeleton short" />
      </div>
    );
  }

  // 格式化视频时长 - 后端已返回格式化字符串，直接使用
  const formatDuration = (duration) => {
    // 如果是数字，按秒数格式化
    if (typeof duration === 'number' && !isNaN(duration)) {
      const hours = Math.floor(duration / 3600);
      const minutes = Math.floor((duration % 3600) / 60);
      const secs = Math.floor(duration % 60);
      
      if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
      }
    }
    // 如果是字符串格式（后端已格式化），直接返回
    return duration || "未知";
  };

  const handleImageError = (e, originalSrc) => {
    const img = e.target;
    const currentAttempt = parseInt(img.dataset.attempt || '0');

    // 外部图片（可能是LLM误加的占位链接）加载失败直接隐藏，不做无意义重试
    if (/^https?:/i.test(originalSrc)) {
      img.style.display = 'none';
      return;
    }

    if (currentAttempt >= 1 || !report.output_dir || originalSrc.startsWith('/static/')) {
      // 首选路径已失败，无更多可用候选，直接隐藏
      img.style.display = 'none';
      return;
    }

    img.dataset.attempt = '1';
    img.src = `/static/${report.output_dir}/${originalSrc}`;
  };

  // 渲染Markdown内容
  const renderMarkdown = (content) => {
    if (!content) return <div className="text-gray-500">暂无内容</div>;
    
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        className="prose prose-slate max-w-none"
        components={{
          img: ({ src, alt, ...props }) => {
            // 相对路径 -> 后端静态目录。
            // 注意：react-markdown v9 会对 URL 做一次百分号编码，这里必须先解码还原，
            // 再交给浏览器自动编码；若手动 encodeURIComponent 会造成双重编码 404。
            let imageSrc = src;
            if (!/^https?:/i.test(src) && !src.startsWith('/')) {
              let clean = src;
              try { clean = decodeURIComponent(src); } catch (e) { /* 保持原样 */ }
              const prefix = report.output_dir
                ? `/static/${report.output_dir}/`
                : '/static/';
              imageSrc = `${prefix}${clean}`;
            }

            return (
              <img
                src={imageSrc}
                alt={alt}
                {...props}
                onError={(e) => handleImageError(e, imageSrc)}
                className="max-w-full h-auto rounded-lg shadow-sm"
                loading="lazy"
              />
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

  // 开始编辑
  const handleEdit = (type) => {
    // 前端标签名 → 后端 file_type 映射（后端只认 detailed / final / detailed_report）
    const map = {
      outline: ["detailed", "detailed_outline.md"],
      report: ["final", "final_report.md"],
      detailed: ["detailed_report", "detailed_report.md"],
    };
    const [fileType, fileName] = map[type] || map.outline;
    const editorUrl = `/editor/${report.task_id}?file=${fileType}&name=${encodeURIComponent(fileName)}`;
    window.location.href = editorUrl;
  };

  const tabs = [
    { key: "outline", label: "图文大纲", icon: Image, content: report.detailed_outline, description: "沿着核心观点，快速回顾视频内容。" },
    { key: "report", label: "精简报告", icon: FileText, content: report.final_report, description: "提炼重点，留下值得记住的内容。" },
    { key: "detailed", label: "详细报告", icon: BookOpen, content: report.detailed_report, description: "对照视频原文与整理笔记，深入理解每一个观点。" },
  ];
  const currentTab = tabs.find(tab => tab.key === activeTab);
  const sourceTitle = report.video_name || report.fileName || "视频分析报告";
  const topicTags = [...sourceTitle.matchAll(/(?:^|\s)(#[^\s#]+)/g)].map(match => match[1]);
  const displayTitle = sourceTitle.replace(/(?:^|\s)#[^\s#]+/g, '').trim() || sourceTitle;

  return (
    <div className="report-page">
      <div className="report-navigation">
        <button onClick={onBack} className="report-back"><ArrowLeft size={16} /> 返回处理记录</button>
        <span className="report-complete"><Check size={13} /> 已完成解析</span>
      </div>

      <header className="report-heading">
        <div className="eyebrow">VIDEO NOTES / 视频报告</div>
        <h1>{displayTitle}</h1>
        {topicTags.length > 0 && <div className="report-title-tags">{topicTags.map((tag, index) => <span key={`${tag}-${index}`}>{tag}</span>)}</div>}
        <div className="report-metadata">
          <span className="report-platform">{PLATFORM_LABELS[report.platform] || "本地视频"}</span>
          <span><Clock size={14} /> {formatDuration(report.duration)}</span>
          <span><FileText size={14} /> {report.created_at ? new Date(report.created_at).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : "时间未知"}</span>
          {report.source_url && (
            <a href={report.source_url} target="_blank" rel="noreferrer" title={report.source_url}>
              <Link2 size={14} /> 查看原视频 <ArrowUpRight size={12} />
            </a>
          )}
        </div>
      </header>

      <section className="report-tools" aria-label="报告工具">
        <div className="report-tool-group">
          <span className="report-tool-label">拓展学习</span>
          <button onClick={handleGenerateCard} disabled={cardLoading} className="report-tool-button">
            <LayoutGrid size={16} /> {cardLoading ? "生成中…" : "学习卡片"}
          </button>
          <button onClick={() => handleOpenHtml("mindmap")} disabled={htmlLoading.mindmap} className="report-tool-button">
            <Share2 size={16} /> {htmlLoading.mindmap ? "生成中…" : "思维导图"}
          </button>
          <button onClick={() => handleOpenHtml("graph")} disabled={htmlLoading.graph} className="report-tool-button">
            <Network size={16} /> {htmlLoading.graph ? "生成中…" : "知识图谱"}
          </button>
        </div>
        <div className="report-tool-group report-file-tools">
          <button onClick={handleShowTiming} disabled={timingLoading} className="report-tool-button report-timing-button">
            <Timer size={16} /> {timingLoading ? "加载中…" : "耗时分析"}
          </button>
          <div className="report-export" ref={exportRef}>
            <button onClick={() => setExportMenu(exportMenu ? null : activeTab)} aria-expanded={!!exportMenu} aria-controls="report-export-options" className="report-primary-button">
              <FileDown size={16} /> 导出报告 <ChevronDown size={14} />
            </button>
            {exportMenu && (
              <div id="report-export-options" className="report-export-panel">
                <label htmlFor="export-document-type">选择导出内容</label>
                <select id="export-document-type" value={exportMenu} onChange={event => setExportMenu(event.target.value)}>
                  {tabs.map(tab => <option key={tab.key} value={tab.key}>{tab.label}</option>)}
                </select>
                <button onClick={() => doExport(exportMenu, "inline")}>
                  <FileText size={18} /><span><strong>Markdown 单文件</strong><small>内嵌图片，便于分享与阅读</small></span><ArrowUpRight size={14} />
                </button>
                <button onClick={() => doExport(exportMenu, "zip")}>
                  <FileDown size={18} /><span><strong>ZIP 原图打包</strong><small>Markdown 与原始图片一并保存</small></span><ArrowUpRight size={14} />
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

        {/* 内嵌预览模态（思维导图 / 知识图谱 / 学习卡片） */}
        {preview && (
          <div className="fixed inset-0 z-[200] bg-black/60 flex items-center justify-center p-4"
               onClick={() => setPreview(null)}>
            <div className="bg-white rounded-xl shadow-2xl w-full h-full max-w-[95vw] max-h-[92vh] flex flex-col overflow-hidden"
                 onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200 flex-shrink-0">
                <h3 className="text-base font-bold text-gray-900">{preview.title}</h3>
                <div className="flex items-center gap-2">
                  <a href={preview.url} target="_blank" rel="noreferrer"
                     className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50">
                    浏览器打开
                  </a>
                  <button onClick={() => setPreview(null)}
                          className="px-3 py-1.5 rounded-lg bg-gray-800 text-white text-xs font-medium hover:bg-gray-900">
                    关闭
                  </button>
                </div>
              </div>
              <iframe
                key={preview.url}
                src={preview.url}
                title={preview.title}
                className="flex-1 w-full border-0 bg-white"
              />
            </div>
          </div>
        )}

        {/* 耗时分析面板 */}
        {timing && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="report-timing-panel bg-white rounded-xl border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <Timer className="w-5 h-5 text-primary-600" />
                耗时分析
                <span className="text-xs font-normal text-gray-400">
                  总耗时 {timing.summary?.total_elapsed}s
                </span>
              </h3>
              <div className="flex items-center gap-2">
                <a href={timing.timing_url} target="_blank" rel="noreferrer"
                   className="text-xs text-primary-600 hover:underline">查看完整报告</a>
                <button onClick={() => setTiming(null)}
                        className="text-xs text-gray-400 hover:text-gray-600">关闭</button>
              </div>
            </div>
            <div className="space-y-2">
              {(timing.top_slowest || []).map((p, i) => {
                const maxTotal = timing.top_slowest[0]?.total || 1
                return (
                  <div key={i}>
                    <div className="flex items-center justify-between text-xs mb-0.5">
                      <span className="text-gray-700">
                        {p.name}
                        <span className="ml-2 text-gray-400">{p.category}</span>
                        {p.count > 1 && <span className="ml-2 text-gray-400">×{p.count}</span>}
                      </span>
                      <span className="text-gray-600 font-medium">
                        {p.total.toFixed(2)}s
                        {p.count > 1 && <span className="text-gray-400 ml-1">(avg {p.avg.toFixed(2)}s)</span>}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-primary-600 rounded-full"
                           style={{ width: `${Math.max(2, (p.total / maxTotal) * 100)}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="mt-4 text-xs text-gray-400">
              报告同时落盘在任务目录：timing_report.json（明细）/ timing_summary.txt（摘要）
            </p>
          </motion.div>
        )}

      <section className="report-reader">
        <div className="report-reader-toolbar">
          <div className="report-tabs" role="tablist" aria-label="报告内容" onKeyDown={event => {
            const directions = { ArrowRight: 1, ArrowLeft: -1 };
            let index = tabs.findIndex(tab => tab.key === activeTab);
            if (event.key in directions) index = (index + directions[event.key] + tabs.length) % tabs.length;
            else if (event.key === 'Home') index = 0;
            else if (event.key === 'End') index = tabs.length - 1;
            else return;
            event.preventDefault();
            setActiveTab(tabs[index].key);
            setExportMenu(null);
            event.currentTarget.querySelectorAll('[role="tab"]')[index].focus();
          }}>
            {tabs.map(({ key, label, icon: Icon }) => (
              <button key={key} id={`report-tab-${key}`} role="tab" aria-selected={activeTab === key}
                aria-controls="report-content" tabIndex={activeTab === key ? 0 : -1}
                onClick={() => { setActiveTab(key); setExportMenu(null); }}>
                <Icon size={16} /><span>{label}</span>
              </button>
            ))}
          </div>
          <button onClick={() => handleEdit(activeTab)} className="report-edit-button"><Edit3 size={15} /> 编辑报告</button>
        </div>
        <div id="report-content" role="tabpanel" aria-labelledby={`report-tab-${activeTab}`} tabIndex={0} className="report-content">
          <p className="report-reading-note"><BookOpen size={14} /> {currentTab.description}</p>
          <article className="report-prose">
            {currentTab.content ? renderMarkdown(currentTab.content) : (
              <div className="report-empty"><FileText size={28} /><h2>暂时没有{currentTab.label}</h2><p>该任务尚未生成这份内容，可以先查看其他报告。</p></div>
            )}
          </article>
          <footer className="report-reading-footer"><span>VideoDevour</span><span>从视频中汲取知识，让思考持续生长。</span></footer>
        </div>
      </section>
    </div>
  );
};

export default ReportViewer;
