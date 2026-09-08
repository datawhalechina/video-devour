import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, FileText, Image, Download, Edit3, LayoutGrid, FileDown,
  Timer, Share2, Network } from "lucide-react";
import { generateCard, generateMindmap, generateKnowledgeGraph } from "../api/settingsService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SplitViewEditor from './Editor/SplitViewEditor';

const ReportViewer = ({ report, onBack }) => {
  const [activeTab, setActiveTab] = useState("outline");
  const [isEditing, setIsEditing] = useState(false);
  const [editingContent, setEditingContent] = useState("");
  const [editingType, setEditingType] = useState(""); // "outline" or "report"
  const [cardHtml, setCardHtml] = useState("");
  const [cardLoading, setCardLoading] = useState(false)
  const [timing, setTiming] = useState(null)
  const [timingLoading, setTimingLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState({});

  // 通用：调用生成接口并在新窗口打开（思维导图 / 知识图谱）。
  // 注意：window.open 必须在点击手势内同步调用（await 之后调用会被弹窗拦截
  // 且 win 为 null 静默失败），生成完成后再将窗口定向到静态缓存地址。
  const openWindowNow = (kind, fileName) => {
    const win = window.open("", "_blank");
    if (win && report.output_dir) {
      win.document.write(
        `<html><head><meta charset="utf-8"><style>body{font:16px/2 -apple-system,"PingFang SC",sans-serif;color:#334155;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}</style></head><body><p>⏳ 正在生成${fileName}，请稍候（约 10-30 秒）…</p></body></html>`
      );
    }
    return win;
  };

  const finalizeWindow = (win, kind, fileName, cachedPath) => {
    if (!win || win.closed) {
      alert(
        `${fileName}已生成完成！\n\n但浏览器拦截了新窗口，请点击报告页的按钮重试，` +
        `或直接访问：\n/static/${report.output_dir}/${cachedPath}`
      );
      return;
    }
    win.location.href = `/static/${report.output_dir}/${cachedPath}`;
  };

  const handleOpenHtml = async (kind) => {
    if (htmlLoading[kind]) return;
    const fileName = kind === "mindmap" ? "思维导图" : "知识图谱";
    const cachedPath = kind === "mindmap" ? "mindmap.html" : "knowledge_graph.html";
    const win = openWindowNow(kind, fileName);
    setHtmlLoading(prev => ({ ...prev, [kind]: true }));
    try {
      const fn = kind === "mindmap" ? generateMindmap : generateKnowledgeGraph;
      await fn(report.task_id);
      finalizeWindow(win, kind, fileName, cachedPath);
    } catch (err) {
      if (win && !win.closed) win.close();
      alert(`${fileName}生成失败: ${err.message}`);
    } finally {
      setHtmlLoading(prev => ({ ...prev, [kind]: false }));
    }
  };

  // 生成学习卡片（移植自 light 版），在新窗口预览
  const handleGenerateCard = async () => {
    if (cardLoading) return;
    const win = window.open("", "_blank");
    if (win && report.output_dir) {
      win.document.write(
        `<html><head><meta charset="utf-8"><style>body{font:16px/2 -apple-system,"PingFang SC",sans-serif;color:#334155;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}</style></head><body><p>⏳ 正在生成学习卡片，请稍候（约 10-30 秒）…</p></body></html>`
      );
    }
    setCardLoading(true);
    try {
      await generateCard(report.task_id);
      if (!win || win.closed) {
        alert(`学习卡片已生成完成！\n\n但浏览器拦截了新窗口，请重试或直接访问：\n/static/${report.output_dir}/learning_card.html`);
        return;
      }
      win.location.href = `/static/${report.output_dir}/learning_card.html`;
    } catch (err) {
      if (win && !win.closed) win.close();
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

  const handleExportMarkdown = (type = "all") => {
    window.open(`/api/export/${report.task_id}?type=${type}`, "_blank");
  };

  // 动态更新页面标题
  useEffect(() => {
    if (report && report.video_name) {
      document.title = `${report.video_name} - 分析报告 | VideoDevour`;
    } else {
      document.title = "视频分析报告 | VideoDevour";
    }
    
    // 组件卸载时恢复默认标题
    return () => {
      document.title = "🍽️ VideoDevour | 智能视频分析工具";
    };
  }, [report]);

  if (!report) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-gray-500">暂无报告数据</div>
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
    const content = type === "outline" ? report.detailed_outline : report.final_report;
    const taskId = report.task_id;
    const fileName = type === "outline" ? "detailed_outline.md" : "final_report.md";
    
    // 在当前页面跳转到编辑器
    const editorUrl = `/editor/${taskId}?file=${type}&name=${encodeURIComponent(fileName)}`;
    window.location.href = editorUrl;
  };

  // 保存编辑
  const handleSave = async (markdown) => {
    try {
      // 这里可以添加保存到后端的逻辑
      console.log("保存内容:", markdown);
      
      // 更新本地状态（实际项目中应该调用API更新后端数据）
      if (editingType === "outline") {
        report.detailed_outline = markdown;
      } else {
        report.final_report = markdown;
      }
      
      setIsEditing(false);
      setEditingContent("");
      setEditingType("");
    } catch (error) {
      console.error("保存失败:", error);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    setIsEditing(false);
    setEditingContent("");
    setEditingType("");
  };

  // 如果正在编辑，显示编辑器
  if (isEditing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <SplitViewEditor
          initialMarkdown={editingContent}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow"
          >
            <ArrowLeft className="w-4 h-4" />
            返回
          </button>
          <h1 className="text-2xl font-bold text-gray-800">
            {report.video_name ? `${report.video_name} - 分析报告` : "视频分析报告"}
          </h1>
          <div className="w-20"></div> {/* 占位符保持居中 */}
        </div>

        {/* 视频信息卡片 */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-xl shadow-lg p-6 mb-8"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">
                {report.video_name || report.fileName || "未知视频"}
              </h2>
              <div className="flex items-center gap-4 text-gray-600">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>时长: {formatDuration(report.duration)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  <span>处理时间: {report.created_at ? new Date(report.created_at).toLocaleString() : "未知"}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleGenerateCard}
                disabled={cardLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-primary-600 to-purple-600 text-white text-sm font-medium shadow-md hover:shadow-lg transition-shadow disabled:opacity-60"
              >
                <LayoutGrid className="w-4 h-4" />
                {cardLoading ? "生成中..." : "生成学习卡片"}
              </button>
              <button
                onClick={() => handleOpenHtml("mindmap")}
                disabled={htmlLoading.mindmap}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white text-sm font-medium shadow-md hover:shadow-lg transition-shadow disabled:opacity-60"
              >
                <Share2 className="w-4 h-4" />
                {htmlLoading.mindmap ? "生成中..." : "思维导图"}
              </button>
              <button
                onClick={() => handleOpenHtml("graph")}
                disabled={htmlLoading.graph}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-medium shadow-md hover:shadow-lg transition-shadow disabled:opacity-60"
              >
                <Network className="w-4 h-4" />
                {htmlLoading.graph ? "生成中..." : "知识图谱"}
              </button>
              <button
                onClick={handleShowTiming}
                disabled={timingLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition disabled:opacity-60"
              >
                <Timer className="w-4 h-4" />
                {timingLoading ? "加载中..." : "耗时分析"}
              </button>
              <button
                onClick={() => handleExportMarkdown("outline")}
                title="导出图文大纲（含关键帧图片，图片内嵌）"
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition"
              >
                <FileDown className="w-4 h-4" />
                导出图文大纲
              </button>
              <button
                onClick={() => handleExportMarkdown("report")}
                title="导出精简报告（含关键帧图片，图片内嵌）"
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition"
              >
                <FileDown className="w-4 h-4" />
                导出精简报告
              </button>
            </div>
          </div>
        </motion.div>

        {/* 耗时分析面板 */}
        {timing && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="mt-4 bg-white rounded-xl shadow-lg p-6"
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
                      <div className="h-full bg-gradient-to-r from-primary-500 to-purple-500 rounded-full"
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

        {/* 标签页 */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab("outline")}
              className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                activeTab === "outline"
                  ? "bg-blue-500 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <Image className="w-4 h-4" />
                图文大纲
              </div>
            </button>
            <button
              onClick={() => setActiveTab("report")}
              className={`flex-1 px-6 py-4 text-center font-medium transition-colors ${
                activeTab === "report"
                  ? "bg-blue-500 text-white"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              <div className="flex items-center justify-center gap-2">
                <FileText className="w-4 h-4" />
                精简报告
              </div>
            </button>
          </div>

          {/* 内容区域 */}
          <div className="p-6 max-h-96 overflow-y-auto">
            {activeTab === "outline" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="prose max-w-none"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">图文大纲</h3>
                  <button
                    onClick={() => handleEdit("outline")}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                  >
                    <Edit3 className="w-4 h-4" />
                    编辑报告
                  </button>
                </div>
                <div className="markdown-content">
                  {renderMarkdown(report.detailed_outline)}
                </div>
              </motion.div>
            )}

            {activeTab === "report" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="prose max-w-none"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">精简报告</h3>
                  <button
                    onClick={() => handleEdit("report")}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                  >
                    <Edit3 className="w-4 h-4" />
                    编辑报告
                  </button>
                </div>
                <div className="markdown-content">
                  {renderMarkdown(report.final_report)}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;

