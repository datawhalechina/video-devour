import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Plus,
  Calendar,
  Clock,
  FileText,
  Loader2,
  Trash2,
  AlertCircle,
  RotateCcw,
  Pencil
} from 'lucide-react'
import { getHistory, deleteReport } from '../api/videoService'

function HistoryList({ onViewReport, onBack, onBackToProcessing, currentTask }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryingId, setRetryingId] = useState('')
  const [renamingId, setRenamingId] = useState('')
  const navigate = useNavigate()

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

  // 重试失败任务：服务端按原任务的输入创建新任务，成功后跳到处理进度页
  const handleRetry = async (taskId) => {
    if (retryingId) return
    setRetryingId(taskId)
    try {
      const res = await fetch(`/api/task/${taskId}/retry`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      navigate(`/processing/${data.task_id}`)
    } catch (err) {
      alert(`重试失败：${err.message}`)
    } finally {
      setRetryingId('')
    }
  }

  // 重命名：保存展示名后刷新列表，让卡片标题立即同步
  const handleRename = async (taskId, name) => {
    if (renamingId) return
    setRenamingId(taskId)
    try {
      const res = await fetch(`/api/task/${taskId}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      const fresh = await getHistory()
      setHistory(fresh)
    } catch (err) {
      alert(`重命名失败：${err.message}`)
    } finally {
      setRenamingId('')
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
              onRetry={handleRetry}
              retrying={retryingId === item.id}
              onRename={handleRename}
              renaming={renamingId === item.id}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function HistoryCard({ item, index, onView, onDelete, onOpenProcessing, onRetry, retrying, onRename, renaming, formatDate }) {
  const isProcessing = item.status === 'processing'
  const isFailed = item.status === 'failed'
  const progress = Math.max(0, Math.min(100, item.progress || 0))
  // 就地改名状态
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const saveRef = useRef('')        // 保存最新的输入值，避免闭包读到旧 draft
  const save = async () => {
    const name = (saveRef.current || draft).trim()
    setEditing(false)
    if (!name || name === (item.displayName || item.videoName)) return
    if (onRename) await onRename(item.id, name)
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.18) }}
      className="history-card"
    >
      <div className="history-card-layout">
        <div className="history-card-info">
          {/* 标题（可改名：点铅笔就地编辑，回车/失焦保存） */}
          <h3 className="history-card-title">
            <FileText className="history-document-icon" />
            {editing ? (
              <input
                autoFocus
                className="flex-1 px-2 py-1 text-sm border border-primary-400 rounded outline-none focus:ring-2 focus:ring-primary-300"
                value={draft}
                onChange={(e) => { setDraft(e.target.value); saveRef.current = e.target.value }}
                onClick={(e) => e.stopPropagation()}
                onBlur={save}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); save() }
                  if (e.key === 'Escape') { setEditing(false) }
                }}
                placeholder={item.videoName}
              />
            ) : (
              <span className="truncate">{item.displayName || item.videoName}</span>
            )}
            {onRename && !editing && (
              <button
                onClick={(e) => { e.stopPropagation(); saveRef.current = item.displayName || item.videoName; setEditing(true); setDraft(item.displayName || item.videoName) }}
                className="ml-1 p-1 rounded text-gray-400 hover:text-primary-600 hover:bg-primary-50"
                title="重命名"
                aria-label="重命名"
              >
                {renaming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Pencil className="w-3.5 h-3.5" />}
              </button>
            )}
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

          {/* 失败：错误信息 + 重试入口 */}
          {isFailed && item.message && (
            <div className="flex items-center justify-between gap-3">
              <p className="history-error">{item.message}</p>
              {onRetry && (
                <button
                  onClick={() => onRetry(item.id)}
                  disabled={retrying}
                  className="flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-primary-300 text-primary-700 text-xs font-medium hover:bg-primary-50 disabled:opacity-60"
                  title="按原任务的输入重新处理（链接重下 / 本地文件重跑）"
                >
                  {retrying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                  {retrying ? '重试中…' : '重试'}
                </button>
              )}
            </div>
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

