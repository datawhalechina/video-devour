import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowLeft, 
  Calendar, 
  Clock, 
  FileText,
  Loader2,
  Trash2,
  Eye,
  AlertCircle
} from 'lucide-react'
import { getHistory, deleteReport } from '../api/videoService'

function HistoryList({ onViewReport, onBack }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getHistory()
      setHistory(data)
    } catch (err) {
      setError(err.message || '加载历史记录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定要删除这份报告吗？')) return

    try {
      await deleteReport(id)
      setHistory(history.filter(item => item.id !== id))
    } catch (err) {
      alert('删除失败：' + err.message)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* 头部 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>返回</span>
        </button>

        <h2 className="text-2xl font-bold text-gray-800">历史记录</h2>
        
        <div className="w-20"></div> {/* 占位符，保持布局平衡 */}
      </motion.div>

      {/* 内容 */}
      {loading ? (
        <div className="bg-white rounded-xl shadow-md p-12 text-center">
          <Loader2 className="w-12 h-12 text-primary-500 mx-auto mb-4 animate-spin" />
          <p className="text-gray-600">加载中...</p>
        </div>
      ) : error ? (
        <div className="bg-white rounded-xl shadow-md p-12 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadHistory}
            className="mt-4 px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            重试
          </button>
        </div>
      ) : history.length === 0 ? (
        <div className="bg-white rounded-xl shadow-md p-12 text-center">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">暂无处理记录</p>
          <button
            onClick={onBack}
            className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            去上传视频
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item, index) => (
            <HistoryCard
              key={item.id}
              item={item}
              index={index}
              onView={() => onViewReport(item)}
              onDelete={() => handleDelete(item.id)}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function HistoryCard({ item, index, onView, onDelete, formatDate }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* 标题 */}
          <h3 className="text-lg font-bold text-gray-800 mb-2 flex items-center space-x-2">
            <FileText className="w-5 h-5 text-primary-500" />
            <span>{item.videoName}</span>
          </h3>

          {/* 信息行 */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
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
                : item.status === 'processing'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {item.status === 'completed' ? '已完成' : 
               item.status === 'processing' ? '处理中' : '失败'}
            </div>
          </div>

          {/* 描述 */}
          {item.description && (
            <p className="mt-3 text-sm text-gray-600 line-clamp-2">
              {item.description}
            </p>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center space-x-2 ml-4">
          {item.status === 'completed' && (
            <motion.button
              onClick={onView}
              className="p-2 bg-primary-50 text-primary-600 rounded-lg hover:bg-primary-100 transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              title="查看报告"
            >
              <Eye className="w-5 h-5" />
            </motion.button>
          )}
          <motion.button
            onClick={onDelete}
            className="p-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title="删除"
          >
            <Trash2 className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}

export default HistoryList

