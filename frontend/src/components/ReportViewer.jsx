import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  Image as ImageIcon,
  Video as VideoIcon,
  Calendar,
  Clock,
  Edit3
} from 'lucide-react'
import SplitViewEditor from './Editor/SplitViewEditor'

function ReportViewer({ report, onBack }) {
  const [viewMode, setViewMode] = useState('detailed') // detailed, final
  const [isEditing, setIsEditing] = useState(false)
  const [editingContent, setEditingContent] = useState(null)

  if (!report) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">暂无报告数据</p>
      </div>
    )
  }

  const handleDownload = (type) => {
    // 实现下载逻辑
    const content = type === 'detailed' ? report.detailedOutline : report.finalReport
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.videoName}_${type}_report.md`
    a.click()
    URL.revokeObjectURL(url)
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

  const handleEdit = (type) => {
    const content = type === 'detailed' ? report.detailedOutline : report.finalReport
    setEditingContent({ type, content })
    setIsEditing(true)
  }

  const handleSaveEdit = async (newMarkdown) => {
    // 这里应该调用 API 保存编辑后的内容
    console.log('保存编辑:', editingContent.type, newMarkdown)
    
    // 更新本地报告内容
    if (editingContent.type === 'detailed') {
      report.detailedOutline = newMarkdown
    } else {
      report.finalReport = newMarkdown
    }
    
    setIsEditing(false)
    setEditingContent(null)
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditingContent(null)
  }

  // 如果正在编辑，显示编辑器
  if (isEditing && editingContent) {
    return (
      <SplitViewEditor
        initialMarkdown={editingContent.content}
        onSave={handleSaveEdit}
        onCancel={handleCancelEdit}
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 头部操作栏 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-xl shadow-md p-6 mb-6"
      >
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回</span>
          </button>

          <div className="flex items-center space-x-3">
            <motion.button
              onClick={() => handleEdit(viewMode)}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-primary-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Edit3 className="w-4 h-4" />
              <span>编辑报告</span>
            </motion.button>
            
            <motion.button
              onClick={() => handleDownload('detailed')}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Download className="w-4 h-4" />
              <span>下载详细报告</span>
            </motion.button>
            <motion.button
              onClick={() => handleDownload('final')}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Download className="w-4 h-4" />
              <span>下载精简报告</span>
            </motion.button>
          </div>
        </div>

        {/* 视频信息 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <InfoCard
            icon={<FileText className="w-5 h-5" />}
            label="视频名称"
            value={report.videoName}
          />
          <InfoCard
            icon={<Calendar className="w-5 h-5" />}
            label="处理时间"
            value={formatDate(report.createdAt)}
          />
          <InfoCard
            icon={<Clock className="w-5 h-5" />}
            label="视频时长"
            value={report.duration || '未知'}
          />
        </div>
      </motion.div>

      {/* 视图切换 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex space-x-2 mb-6"
      >
        <ViewToggleButton
          active={viewMode === 'detailed'}
          onClick={() => setViewMode('detailed')}
          icon={<ImageIcon className="w-4 h-4" />}
          label="图文大纲"
        />
        <ViewToggleButton
          active={viewMode === 'final'}
          onClick={() => setViewMode('final')}
          icon={<FileText className="w-4 h-4" />}
          label="精简报告"
        />
      </motion.div>

      {/* 报告内容 */}
      <motion.div
        key={viewMode}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="bg-white rounded-xl shadow-md p-8"
      >
        <div className="markdown-content prose max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {viewMode === 'detailed' ? report.detailedOutline : report.finalReport}
          </ReactMarkdown>
        </div>
      </motion.div>

      {/* 相关文件下载 */}
      {report.assets && report.assets.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-6 bg-white rounded-xl shadow-md p-6"
        >
          <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center space-x-2">
            <VideoIcon className="w-5 h-5" />
            <span>相关文件</span>
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {report.assets.map((asset, index) => (
              <AssetCard key={index} asset={asset} />
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
      <div className="text-primary-500">{icon}</div>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-semibold text-gray-800 truncate">{value}</p>
      </div>
    </div>
  )
}

function ViewToggleButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all ${
        active
          ? 'bg-primary-500 text-white shadow-md'
          : 'bg-white text-gray-700 hover:bg-gray-50 shadow'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

function AssetCard({ asset }) {
  return (
    <a
      href={asset.url}
      download
      className="flex flex-col items-center space-y-2 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors group"
    >
      {asset.type === 'video' ? (
        <VideoIcon className="w-8 h-8 text-primary-500 group-hover:scale-110 transition-transform" />
      ) : (
        <ImageIcon className="w-8 h-8 text-purple-500 group-hover:scale-110 transition-transform" />
      )}
      <p className="text-xs text-center text-gray-700 truncate w-full">{asset.name}</p>
    </a>
  )
}

export default ReportViewer

