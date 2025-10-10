import { useState } from "react";
import { useNavigate } from "react-router-dom";
import DocumentEditor from "./Editor/DocumentEditor";
import { FiSave, FiDownload, FiRefreshCw, FiMenu, FiX, FiFileText, FiChevronLeft, FiChevronRight, FiArrowLeft, FiHome } from "react-icons/fi";
import { motion, AnimatePresence } from "framer-motion";

/**
 * 编辑器测试页面 - 文档编辑系统
 */
function EditorTestPage() {
  const navigate = useNavigate();
  
  // 文档列表
  const [documents, setDocuments] = useState([
    {
      id: 1,
      name: "功能测试文档",
      lastModified: new Date().toISOString(),
      content: getInitialTestData(),
    },
    {
      id: 2,
      name: "我的笔记",
      lastModified: new Date(Date.now() - 86400000).toISOString(),
      content: [
        {
          type: "heading",
          level: 1,
          children: [{ text: "📝 我的笔记" }],
        },
        {
          type: "paragraph",
          children: [{ text: "开始记录你的想法..." }],
        },
      ],
    },
    {
      id: 3,
      name: "会议记录",
      lastModified: new Date(Date.now() - 172800000).toISOString(),
      content: [
        {
          type: "heading",
          level: 1,
          children: [{ text: "📅 会议记录" }],
        },
        {
          type: "paragraph",
          children: [{ text: "记录重要的会议内容..." }],
        },
      ],
    },
  ]);

  const [currentDocId, setCurrentDocId] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // 获取当前文档
  const currentDoc = documents.find((doc) => doc.id === currentDocId);

  // 假数据 - 展示各种块类型
  function getInitialTestData() {
    return [
      {
        type: "heading",
        level: 1,
        children: [{ text: "🎉 富文本编辑器功能测试" }],
      },
      {
        type: "paragraph",
        children: [
          { text: "欢迎使用我们的富文本编辑器！这个页面展示了所有支持的功能。" },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "📝 文本格式" }],
      },
      {
        type: "paragraph",
        children: [
          { text: "这是 " },
          { text: "粗体文本", bold: true },
          { text: "，这是 " },
          { text: "斜体文本", italic: true },
          { text: "，这是 " },
          { text: "下划线文本", underline: true },
          { text: "，这是 " },
          { text: "删除线", strikethrough: true },
          { text: "，还有 " },
          { text: "行内代码", code: true },
          { text: "。" },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "📋 列表功能" }],
      },
      {
        type: "paragraph",
        children: [{ text: "无序列表示例：" }],
      },
      {
        type: "bulleted-list",
        children: [
          {
            type: "list-item",
            children: [{ text: "第一个列表项" }],
          },
          {
            type: "list-item",
            children: [{ text: "第二个列表项" }],
          },
          {
            type: "list-item",
            children: [{ text: "第三个列表项" }],
          },
        ],
      },
      {
        type: "paragraph",
        children: [{ text: "有序列表示例：" }],
      },
      {
        type: "numbered-list",
        children: [
          {
            type: "list-item",
            children: [{ text: "步骤一：准备材料" }],
          },
          {
            type: "list-item",
            children: [{ text: "步骤二：开始制作" }],
          },
          {
            type: "list-item",
            children: [{ text: "步骤三：完成" }],
          },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "🖼️ 图片" }],
      },
      {
        type: "paragraph",
        children: [{ text: "支持插入图片，可以设置描述和尺寸：" }],
      },
      {
        type: "image",
        url: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=400&fit=crop",
        alt: "美丽的山景",
        caption: "壮观的自然风光",
        children: [{ text: "" }],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "💬 引用块" }],
      },
      {
        type: "quote",
        children: [
          {
            text: "人生苦短，我用 Python。—— Tim Peters",
          },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "📢 提示框（Callout）" }],
      },
      {
        type: "callout",
        variant: "info",
        children: [
          {
            text: "💡 提示：这是一个信息提示框，可以用来展示重要信息。",
          },
        ],
      },
      {
        type: "callout",
        variant: "warning",
        children: [
          {
            text: "⚠️ 警告：这是一个警告提示框，用于提醒用户注意。",
          },
        ],
      },
      {
        type: "callout",
        variant: "success",
        children: [
          {
            text: "✅ 成功：这是一个成功提示框，用于显示操作成功的消息。",
          },
        ],
      },
      {
        type: "callout",
        variant: "error",
        children: [
          {
            text: "❌ 错误：这是一个错误提示框，用于显示错误信息。",
          },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "➗ 分割线" }],
      },
      {
        type: "paragraph",
        children: [{ text: "可以使用分割线来分隔内容：" }],
      },
      {
        type: "divider",
        children: [{ text: "" }],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "⌨️ 快捷键说明" }],
      },
      {
        type: "paragraph",
        children: [
          { text: "• " },
          { text: "Ctrl/Cmd + B", code: true },
          { text: " - 加粗" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• " },
          { text: "Ctrl/Cmd + I", code: true },
          { text: " - 斜体" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• " },
          { text: "Ctrl/Cmd + U", code: true },
          { text: " - 下划线" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• " },
          { text: "Ctrl/Cmd + `", code: true },
          { text: " - 行内代码" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• " },
          { text: "/", code: true },
          { text: " - 打开斜杠命令菜单" },
        ],
      },
      {
        type: "heading",
        level: 2,
        children: [{ text: "📝 Markdown 快捷输入" }],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: "#", code: true },
          { text: " + 空格 - 一级标题" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: "##", code: true },
          { text: " + 空格 - 二级标题" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: "-", code: true },
          { text: " + 空格 - 无序列表" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: "1.", code: true },
          { text: " + 空格 - 有序列表" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: ">", code: true },
          { text: " + 空格 - 引用块" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "• 输入 " },
          { text: "```", code: true },
          { text: " + 空格 - 代码块" },
        ],
      },
      {
        type: "divider",
        children: [{ text: "" }],
      },
      {
        type: "paragraph",
        children: [
          {
            text: "🎨 现在你可以自由编辑这个文档，测试所有功能！试试输入 / 来打开命令菜单。",
          },
        ],
      },
    ];
  }

  // 处理文档内容变化
  const handleEditorChange = (newContent) => {
    setDocuments(
      documents.map((doc) =>
        doc.id === currentDocId
          ? { ...doc, content: newContent, lastModified: new Date().toISOString() }
          : doc
      )
    );
  };

  // 切换文档
  const handleSelectDocument = (docId) => {
    setCurrentDocId(docId);
  };

  // 保存当前文档
  const handleSave = () => {
    alert("✅ 文档已自动保存！");
  };

  // 导出文档为 JSON
  const handleExport = () => {
    if (!currentDoc) return;
    const dataStr = JSON.stringify(currentDoc.content, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${currentDoc.name}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 格式化时间显示
  const formatTime = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString("zh-CN");
  };

  return (
    <div className="h-screen flex flex-col bg-white overflow-hidden">
      {/* 顶部导航栏 */}
      <div className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* 返回主页按钮 */}
              <button
                onClick={() => navigate('/')}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all group"
                title="返回主页"
              >
                <FiHome className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-medium">主页</span>
              </button>
              
              <div className="w-px h-6 bg-gray-300"></div>
              
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">📝</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">
                  文档编辑器
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <FiDownload className="w-4 h-4" />
                导出
              </button>
              <button
                onClick={handleSave}
                className="flex items-center gap-2 px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all"
              >
                <FiSave className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧文档列表 - 可折叠 */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-r border-gray-200 bg-gray-50 flex flex-col overflow-hidden"
            >
              {/* 文档列表头部 */}
              <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-800">文档</h2>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 hover:bg-gray-100 rounded transition-colors"
                  title="收起侧边栏"
                >
                  <FiChevronLeft className="w-4 h-4 text-gray-600" />
                </button>
              </div>

              {/* 文档列表 */}
              <div className="flex-1 overflow-y-auto p-2">
                {documents.map((doc) => (
                  <motion.button
                    key={doc.id}
                    onClick={() => handleSelectDocument(doc.id)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-all ${
                      doc.id === currentDocId
                        ? "bg-blue-100 border border-blue-200"
                        : "hover:bg-gray-100 border border-transparent"
                    }`}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="flex items-start gap-2">
                      <FiFileText
                        className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                          doc.id === currentDocId
                            ? "text-blue-600"
                            : "text-gray-500"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div
                          className={`text-sm font-medium truncate ${
                            doc.id === currentDocId
                              ? "text-blue-900"
                              : "text-gray-800"
                          }`}
                        >
                          {doc.name}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {formatTime(doc.lastModified)}
                        </div>
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 右侧编辑器区域 */}
        <div className="flex-1 flex flex-col bg-white overflow-hidden">
          {/* 编辑器头部 */}
          <div className="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50">
            <div className="flex items-center gap-3">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                  title="展开侧边栏"
                >
                  <FiChevronRight className="w-4 h-4 text-gray-600" />
                </button>
              )}
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <h3 className="text-sm font-semibold text-gray-800">
                  {currentDoc?.name || "未选择文档"}
                </h3>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>最后编辑：{currentDoc && formatTime(currentDoc.lastModified)}</span>
            </div>
          </div>

          {/* 功能提示条 */}
          <div className="px-6 py-2 bg-gradient-to-r from-blue-50 via-purple-50 to-green-50 border-b border-gray-200">
            <div className="flex items-center gap-6 text-xs text-gray-600">
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-gray-700">💡</span>
                <span>
                  输入 <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">/</code> 打开命令
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-gray-700">⌨️</span>
                <span>
                  <code className="bg-white px-1.5 py-0.5 rounded border border-gray-200">Ctrl+B/I/U</code> 格式化
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-medium text-gray-700">📝</span>
                <span>
                  支持 Markdown 快捷输入
                </span>
              </div>
            </div>
          </div>

          {/* 编辑器 */}
          <div className="flex-1 overflow-y-auto">
            {currentDoc ? (
              <DocumentEditor
                key={currentDoc.id}
                initialValue={currentDoc.content}
                onChange={handleEditorChange}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-400">
                  <FiFileText className="w-16 h-16 mx-auto mb-3 opacity-50" />
                  <p className="text-sm">请从左侧选择一个文档</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditorTestPage;

