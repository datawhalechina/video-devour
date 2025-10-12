import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { FiHome, FiSave, FiX, FiArrowLeft } from 'react-icons/fi';
import { SplitViewEditor } from './Editor';
import { motion } from 'framer-motion';

/**
 * 独立的编辑器页面组件
 * 用于编辑报告文件（详细大纲或精简报告）
 */
function EditorPage() {
  const { taskId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const fileType = searchParams.get('file'); // 'detailed' 或 'final'
  const fileName = searchParams.get('name'); // 文件名
  
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  // 获取文件标题
  const getFileTitle = () => {
    if (fileType === 'detailed') return '详细大纲';
    if (fileType === 'final') return '精简报告';
    return '文档';
  };

  // 加载文件内容
  useEffect(() => {
    const loadContent = async () => {
      if (!taskId || !fileType) {
        setError('缺少必要参数');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const response = await fetch(`/api/reports/${taskId}/${fileType}`);
        
        if (!response.ok) {
          throw new Error(`加载失败: ${response.status}`);
        }
        
        const data = await response.json();
        // 后端返回的是 {content: "..."} 格式
        setContent(data.content || '');
      } catch (err) {
        console.error('加载文件内容失败:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [taskId, fileType]);

  // 保存文件
  const handleSave = async (markdown) => {
    if (!taskId || !fileType) return;

    try {
      setIsSaving(true);
      const response = await fetch(`/api/reports/${taskId}/${fileType}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: markdown }),
      });

      if (!response.ok) {
        throw new Error(`保存失败: ${response.status}`);
      }

      alert('保存成功！');
      // 保存后返回报告页面
      window.location.href = `/report/${taskId}`;
    } catch (err) {
      console.error('保存文件失败:', err);
      alert(`保存失败: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // 取消编辑
  const handleCancel = () => {
    // 返回到报告页面
    window.location.href = `/report/${taskId}`;
  };

  // 返回主页
  const handleGoHome = () => {
    navigate('/', { replace: true });
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={handleCancel}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            返回报告页面
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-white overflow-hidden">
      {/* 顶部导航栏 */}
      <motion.div 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white border-b border-gray-200 flex-shrink-0 shadow-sm"
      >
        <div className="px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* 返回按钮 */}
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all group"
                title="返回报告页面"
              >
                <FiArrowLeft className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-medium">返回</span>
              </button>
              
              <div className="w-px h-6 bg-gray-300"></div>
              
              {/* 主页按钮 */}
              <button
                onClick={handleGoHome}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all group"
                title="返回主页"
              >
                <FiHome className="w-5 h-5 group-hover:scale-110 transition-transform" />
                <span className="text-sm font-medium">主页</span>
              </button>
              
              <div className="w-px h-6 bg-gray-300"></div>
              
              {/* 标题区域 */}
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-lg">📝</span>
                </div>
                <div>
                  <h1 className="text-lg font-bold text-gray-900">
                    编辑 {getFileTitle()}
                  </h1>
                  {fileName && (
                    <p className="text-sm text-gray-500">{fileName}</p>
                  )}
                </div>
              </div>
            </div>

            {/* 右侧操作按钮 */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
                title="取消编辑"
              >
                <FiX className="w-4 h-4" />
                <span className="text-sm font-medium">取消</span>
              </button>
              
              <button
                onClick={() => handleSave(content)}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                title="保存文档"
              >
                <FiSave className={`w-4 h-4 ${isSaving ? 'animate-spin' : ''}`} />
                <span className="text-sm font-medium">
                  {isSaving ? '保存中...' : '保存'}
                </span>
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* 编辑器区域 */}
      <div className="flex-1 overflow-hidden">
        <SplitViewEditor
          initialMarkdown={content}
          onSave={handleSave}
          onCancel={handleCancel}
          showToolbar={false} // 隐藏内置工具栏，使用顶部导航栏
        />
      </div>
    </div>
  );
}

export default EditorPage;