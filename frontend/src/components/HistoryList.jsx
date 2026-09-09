import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowRight,
  Plus,
  Calendar, 
  Clock, 
  FileText,
  Loader2,
  Trash2,
  AlertCircle
} from 'lucide-react'
import { getHistory, deleteReport } from '../api/videoService'

function HistoryList({ onViewReport, onBack, onBackToProcessing, currentTask }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [])

  // 存在处理中任务时每 5 秒自动刷新，全部完成后停止
  useEffect(() => {
    const hasActive = history.some(item => item.status === 'processing')
    if (!hasActive) return
    const timer = setInterval(() => {
      getHistory().then(data => setHistory(data)).catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [history])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getHistory()
      setHistory(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (taskId) => {
    // 乐观删除：先从UI中移除
    const originalHistory = [...history];
    const updatedHistory = history.filter(item => item.id !== taskId);
    setHistory(updatedHistory);
    
    try {
      // 异步删除后端数据
      await deleteReport(taskId);
      
      // 如果删除的是当前正在处理的任务，需要通知父组件清理状态
      if (currentTask === taskId) {
        // 清理localStorage中的任务状态
        localStorage.removeItem('videodevour_current_task');
        // 如果有回调函数，调用它来清理状态
        if (onBackToProcessing) {
          onBackToProcessing();
        }
      }
    } catch (error) {
      console.error('删除失败:', error);
      // 删除失败，恢复原始数据
      setHistory(originalHistory);
      alert('删除失败，请重试');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '未知时间';
    
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return '未知时间';
      }
      
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      console.error('日期格式化错误:', error);
      return '未知时间';
    }
  }

  return (
    <div className="history-page">
      <div className="history-heading">
        <div className="page-intro"><div className="eyebrow">YOUR VIDEO JOURNEY</div><h1>每一次探索，都在这里。</h1><p>查看视频处理进度，或回到已经整理好的知识。</p></div>
        <button onClick={onBack} className="report-primary-button"><Plus size={16} /> 添加视频</button>
      </div>
      {!loading && !error && history.length > 0 && (
        <div className="history-summary"><h2>处理记录 <span>{history.length}</span></h2><div><span className="history-status-dot" /> {history.filter(item => item.status === 'completed').length} 份报告已完成</div></div>
      )}

      {/* 内容 */}
      {loading ? (
        <div className="history-empty">
          <Loader2 className="history-empty-icon animate-spin" />
          <p>加载中…</p>
        </div>
      ) : error ? (
        <div className="history-empty">
          <AlertCircle className="history-empty-icon is-error" />
          <p className="is-error">{error}</p>
          <button onClick={loadHistory} className="report-primary-button">重试</button>
        </div>
      ) : history.length === 0 ? (
        <div className="history-empty">
          <FileText className="history-empty-icon" />
          <p>暂无处理记录</p>
          <button onClick={onBack} className="report-primary-button">去上传视频</button>
        </div>
      ) : (
        <div className="history-list">
          {history.some(item => item.status === 'processing') && (
            <p className="history-refresh-note">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>有任务正在处理，进度每 5 秒自动刷新…</span>
            </p>
          )}
          {history.map((item, index) => (
            <HistoryCard
              key={item.id}
              item={item}
              index={index}
              onView={() => onViewReport(item)}
              onDelete={() => handleDelete(item.id)}
              onOpenProcessing={() => { window.location.href = `/processing/${item.id}` }}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function HistoryCard({ item, index, onView, onDelete, onOpenProcessing, formatDate }) {
  const isProcessing = item.status === 'processing'
  const isFailed = item.status === 'failed'
  const progress = Math.max(0, Math.min(100, item.progress || 0))
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.18) }}
      className="history-card"
    >
      <div className="history-card-layout">
        <div className="history-card-info">
          {/* 标题 */}
          <h3 className="history-card-title">
            <FileText className="history-document-icon" />
            <span>{item.videoName}</span>
          </h3>

          {/* 信息行 */}
          <div className="history-card-meta">
            <div className="flex items-center space-x-1">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(item.createdAt)}</span>
            </div>
            {item.duration && (
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>{item.duration}</span>
              </div>
            )}
            <div className={`px-2 py-1 rounded text-xs font-medium ${
              item.status === 'completed'
                ? 'bg-green-100 text-green-700'
                : isProcessing
                ? 'bg-primary-50 text-primary-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {item.status === 'completed' ? '已完成' :
               isProcessing ? '处理中' : '失败'}
            </div>
          </div>

          {/* 处理中：实时进度条与阶段消息 */}
          {isProcessing && (
            <div className="history-progress">
              <div className="history-progress-head">
                <span>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{item.message || '正在处理…'}</span>
                </span>
                <span>{progress}%</span>
              </div>
              <div className="history-progress-track">
                <div className="history-progress-bar" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {/* 失败：错误信息 */}
          {isFailed && item.message && (
            <p className="history-error">{item.message}</p>
          )}

          {/* 描述 */}
          {item.description && (
            <p className="history-card-meta" style={{ paddingLeft: 32, marginTop: 10 }}>{item.description}</p>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="history-card-actions">
          {item.status === 'completed' && (
            <motion.button
              onClick={onView}
              className="history-open-button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              title="查看报告"
              aria-label={`查看报告：${item.videoName}`}
            >
              <span>查看报告</span><ArrowRight size={15} />
            </motion.button>
          )}
          {isProcessing && onOpenProcessing && (
            <motion.button
              onClick={onOpenProcessing}
              className="history-action-button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              title="查看处理详情"
            >
              查看进度
            </motion.button>
          )}
          <motion.button
            onClick={onDelete}
            className="history-delete-button"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title="删除记录"
            aria-label={`删除记录：${item.videoName}`}
          >
            <Trash2 className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

export default HistoryList

