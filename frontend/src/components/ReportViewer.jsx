import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, FileText, Image, Download, Edit3 } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import SplitViewEditor from './Editor/SplitViewEditor';

const ReportViewer = ({ report, onBack }) => {
  const [activeTab, setActiveTab] = useState("outline");
  const [isEditing, setIsEditing] = useState(false);
  const [editingContent, setEditingContent] = useState("");
  const [editingType, setEditingType] = useState(""); // "outline" or "report"

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
    
    if (currentAttempt >= 3) {
      img.style.display = 'none';
      return;
    }
    
    img.dataset.attempt = (currentAttempt + 1).toString();
    
    let newSrc;
    if (currentAttempt === 0 && report.output_dir) {
      // 第一次重试：使用后端提供的output_dir，并进行URL编码
      const encodedSrc = encodeURIComponent(originalSrc);
      newSrc = `/static/${report.output_dir}/${encodedSrc}`;
    } else if (currentAttempt === 1) {
      // 第二次重试：尝试keyframes路径
      const imageName = originalSrc.split('/').pop();
      const encodedImageName = encodeURIComponent(imageName);
      newSrc = `/static/frames_${report.task_id}_*/keyframes/${encodedImageName}`;
    } else if (currentAttempt === 2) {
      // 第三次重试：尝试直接路径
      const encodedSrc = encodeURIComponent(originalSrc);
      newSrc = `/static/${encodedSrc}`;
    }
    
    if (newSrc) {
      img.src = newSrc;
    }
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
            // 如果是相对路径，转换为静态文件路径
            let imageSrc = src;
            
            // 如果是相对路径，需要构建正确的静态文件路径
            if (!src.startsWith('http') && !src.startsWith('/')) {
              // 构建初始图片URL，只对文件名部分进行URL编码
              if (report.output_dir) {
                // 分离路径和文件名，只对文件名进行编码
                const pathParts = src.split('/');
                const fileName = pathParts.pop();
                const pathPrefix = pathParts.length > 0 ? pathParts.join('/') + '/' : '';
                const encodedFileName = encodeURIComponent(fileName);
                imageSrc = `/static/${report.output_dir}/${pathPrefix}${encodedFileName}`;
              } else {
                // 分离路径和文件名，只对文件名进行编码
                const pathParts = src.split('/');
                const fileName = pathParts.pop();
                const pathPrefix = pathParts.length > 0 ? pathParts.join('/') + '/' : '';
                const encodedFileName = encodeURIComponent(fileName);
                imageSrc = `/static/${pathPrefix}${encodedFileName}`;
              }
            }
            
            return (
              <img 
                src={imageSrc} 
                alt={alt} 
                {...props}
                onError={(e) => handleImageError(e, src)}
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
          </div>
        </motion.div>

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

