import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Film, AlertCircle, Loader2, Clock, X, CheckCircle, Trash2, Play, GraduationCap, Tv, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { uploadVideo } from '../api/videoService'
import ExtrasPicker, { getSelectedExtras } from './ExtrasPicker'

function VideoUpload({ onUploadSuccess, onViewHistory, currentTask, onBackToProcessing }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({})
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [educationLevel, setEducationLevel] = useState('自由学习')
  const fileInputRef = useRef(null)

  const handleFileSelect = (files) => {
    const fileList = Array.from(files || [])
    const validFiles = fileList.filter(file => file.type.startsWith('video/'))
    
    if (validFiles.length === 0) {
      setError('请选择有效的视频文件')
      return
    }
    
    // 添加新文件到已选列表
    const newFiles = validFiles.map(file => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file: file,
      status: 'pending' // pending, uploading, success, error
    }))
    
    setSelectedFiles(prev => [...prev, ...newFiles])
    setError(null)
  }

  const removeFile = (fileId) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const clearAllFiles = () => {
    setSelectedFiles([])
    setUploadProgress({})
    setError(null)
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files)
    }
  }

  const handleUploadAll = async () => {
    if (selectedFiles.length === 0) return

    setUploading(true)
    setError(null)
    
    // 逐个上传视频
    for (const fileItem of selectedFiles) {
      if (fileItem.status !== 'pending') continue
      
      try {
        // 更新状态为上传中
        setSelectedFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'uploading' } : f)
        )
        
        const result = await uploadVideo(fileItem.file, (progress) => {
          setUploadProgress(prev => ({ ...prev, [fileItem.id]: progress }))
        }, educationLevel, getSelectedExtras())

        // 更新状态为成功
        setSelectedFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'success', taskId: result.task_id } : f)
        )
        
        // 如果只有一个文件，直接跳转到处理页面
        if (selectedFiles.length === 1) {
          onUploadSuccess(result.task_id)
          return
        }
      } catch (err) {
        // 更新状态为失败
        setSelectedFiles(prev => 
          prev.map(f => f.id === fileItem.id ? { ...f, status: 'error', error: err.message } : f)
        )
        setError(`${fileItem.file.name} 上传失败: ${err.message}`)
      }
    }
    
    setUploading(false)
    
    // 批量上传完成后，提示用户查看历史记录
    if (selectedFiles.length > 1) {
      setTimeout(() => {
        alert('所有视频已提交处理！请前往"历史记录"查看处理进度')
      }, 500)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="page-intro"><div className="eyebrow">IMPORT YOUR VIDEO</div><h1>让视频里的知识，留下来。</h1><p>上传课程、会议或访谈，整理成一份可阅读的图文报告。</p></div>

      {/* 正在处理任务提示 */}
      {currentTask && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="bg-primary-50 border border-primary-200 rounded-2xl p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-primary-100 rounded-xl">
                  <Play className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-blue-900 mb-1">
                    有任务正在处理中
                  </h3>
                  <p className="text-blue-700 text-sm">
                    任务ID: {currentTask}
                  </p>
                </div>
              </div>
              <button
                onClick={onBackToProcessing}
                className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium flex items-center space-x-2"
              >
                <Clock className="w-4 h-4" />
                <span>查看进度</span>
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* 上传区域 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="upload-panel bg-white rounded-3xl border border-gray-100"
      >
        {/* 在线链接入口 */}
        <div className="mb-4 flex justify-end">
          <Link
            to="/link"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:border-primary-400 hover:text-primary-600 transition"
          >
            <Tv className="w-4 h-4" />
            <span>通过 B站 / YouTube 链接处理</span>
          </Link>
        </div>

        {/* 拖拽上传区 */}
        <div
          className={`upload-dropzone relative border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer group ${
            dragActive
              ? 'border-primary-500 bg-primary-50 scale-[1.02]'
              : selectedFiles.length > 0
              ? 'border-green-300 bg-gradient-to-br from-green-50 to-emerald-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
          role={selectedFiles.length ? undefined : 'button'}
          tabIndex={uploading || selectedFiles.length ? -1 : 0}
          aria-label="选择视频文件，支持多选"
          onKeyDown={(event) => { if (event.target === event.currentTarget && !uploading && ['Enter', ' '].includes(event.key)) { event.preventDefault(); fileInputRef.current?.click() } }}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
            disabled={uploading}
          />

          {selectedFiles.length === 0 && (
            <div className="space-y-6">
              <motion.div
                className="relative"
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <Upload className="w-20 h-20 text-gray-400 mx-auto group-hover:text-gray-500 transition-colors" />
                <motion.div
                  className="absolute inset-0 bg-primary-600 rounded-full blur-xl opacity-0 group-hover:opacity-20 transition-opacity"
                  initial={false}
                />
              </motion.div>
              <div>
                <p className="text-xl font-bold text-gray-800 mb-2">
                  拖拽视频文件到这里
                </p>
                <p className="text-base text-gray-500">
                  或点击选择文件（支持多选）
                </p>
                <div className="mt-4 inline-flex items-center space-x-2 px-4 py-2 bg-gray-100 rounded-full">
                  <span className="text-sm text-gray-600">支持 MP4, AVI, MOV, MKV 等格式</span>
                </div>
              </div>
            </div>
          )}

          {selectedFiles.length > 0 && (
            <div className="space-y-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Film className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">
                      已选择 {selectedFiles.length} 个视频
                    </h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {uploading ? '正在处理中...' : '可继续添加或开始处理'}
                    </p>
                  </div>
                </div>
                {!uploading && (
                  <button
                    onClick={clearAllFiles}
                    className="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg font-medium flex items-center space-x-1 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>清空</span>
                  </button>
                )}
              </div>

              {/* 文件列表 */}
              <div className="max-h-96 overflow-y-auto space-y-3 text-left">
                <AnimatePresence>
                  {selectedFiles.map((fileItem) => (
                    <motion.div
                      key={fileItem.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, x: -100 }}
                      className={`flex items-center justify-between p-4 rounded-xl border-2 ${
                        fileItem.status === 'uploading' 
                          ? 'bg-blue-50 border-blue-300'
                          : fileItem.status === 'success'
                          ? 'bg-green-50 border-green-300'
                          : fileItem.status === 'error'
                          ? 'bg-red-50 border-red-300'
                          : 'bg-white border-gray-200'
                      }`}
                    >
                      <div className="flex items-center space-x-3 flex-1 min-w-0">
                        {fileItem.status === 'uploading' ? (
                          <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
                        ) : fileItem.status === 'success' ? (
                          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                        ) : fileItem.status === 'error' ? (
                          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                        ) : (
                          <Film className="w-5 h-5 text-gray-400 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-800 truncate">
                            {fileItem.file.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatFileSize(fileItem.file.size)}
                            {fileItem.status === 'uploading' && uploadProgress[fileItem.id] && 
                              ` - ${uploadProgress[fileItem.id]}%`
                            }
                            {fileItem.status === 'error' && fileItem.error && 
                              ` - ${fileItem.error}`
                            }
                          </p>
                        </div>
                      </div>
                      {!uploading && fileItem.status === 'pending' && (
                        <button
                          aria-label={`移除 ${fileItem.file.name}`}
                          onClick={() => removeFile(fileItem.id)}
                          className="ml-2 text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>

              {/* 继续添加按钮 */}
              {!uploading && (
                <div className="mt-4">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50 transition-all font-medium flex items-center justify-center space-x-2"
                  >
                    <Upload className="w-4 h-4" />
                    <span>继续添加视频</span>
                  </button>
                </div>
              )}

              {uploading && (
                <div className="mt-6 text-center">
                  <p className="text-sm font-semibold text-gray-700">正在上传处理中，请勿关闭页面...</p>
                </div>
              )}
            </div>
          )}
        </div>

        <details className="upload-config">
          <summary>处理偏好 <span>{educationLevel} · 可选附加内容</span></summary>
        {/* 学习阶段选择 */}
        <div className="upload-options mb-4 bg-white rounded-2xl border border-gray-100 p-5 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <GraduationCap className="w-5 h-5 text-primary-600" />
            <div>
              <p className="text-sm font-semibold text-gray-900">学习阶段</p>
              <p className="text-xs text-gray-500">自由学习为通用模式，其余阶段将调整内容深度</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {['自由学习', '小学', '初中', '高中', '大学', '硕士', '博士', '深入研究', '垂直领域研究'].map((level) => (
              <button
                key={level}
                aria-pressed={educationLevel === level}
                onClick={() => setEducationLevel(level)}
                className={`px-5 py-2 rounded-lg border-2 text-sm font-medium transition ${
                  educationLevel === level
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        {/* 附加产物（可选）：勾选后任务完成时自动生成，不勾最省时间 */}
        <div className="upload-extras mb-6 bg-white rounded-2xl border border-gray-100 p-5 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-primary-500" />
            <div>
              <p className="text-sm font-semibold text-gray-900">完成后生成（可选）</p>
              <p className="text-xs text-gray-500">默认不生成；勾选后报告完成时自动产出对应内容，报告页也可随时手动生成</p>
            </div>
          </div>
          <ExtrasPicker />
        </div>

        </details>

        {/* 错误提示 */}
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-6 flex items-start space-x-3 p-5 bg-red-50 border-l-4 border-red-500 rounded-xl text-red-800 shadow-sm"
          >
            <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold mb-1">上传失败</p>
              <p className="text-sm">{error}</p>
            </div>
          </motion.div>
        )}

        {/* 底部操作按钮 */}
        <AnimatePresence>
          {selectedFiles.length > 0 && !uploading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="mt-8 flex items-center justify-center space-x-4"
            >
              <motion.button
                onClick={clearAllFiles}
                className="px-10 py-4 rounded-xl font-semibold text-gray-700 bg-white border-2 border-gray-300 hover:border-gray-400 hover:bg-gray-50 transition-all shadow-sm"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                取消
              </motion.button>
              <motion.button
                onClick={handleUploadAll}
                className="px-10 py-4 rounded-xl font-bold text-white bg-primary-600 hover:shadow-2xl transition-all shadow-xl relative overflow-hidden group"
                whileHover={{ scale: 1.05, y: -2 }}
                whileTap={{ scale: 0.95 }}
              >
                <span className="relative z-10 flex items-center space-x-2">
                  <span>{selectedFiles.length === 1 ? '确认并开始处理' : `批量处理 ${selectedFiles.length} 个视频`}</span>
                  <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </span>
                <div className="absolute inset-0 bg-primary-700 opacity-0 group-hover:opacity-100 transition-opacity" />
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* 处理时间提示 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-8 flex items-start space-x-3 p-5 bg-primary-50 border border-primary-200 rounded-2xl"
      >
        <Clock className="w-6 h-6 text-primary-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-primary-700">
          <p className="font-bold mb-1">预计处理时间</p>
          <p className="text-blue-700">视频长度 × 0.5 - 1.5 倍（例如：10分钟视频需要 5-15 分钟处理）</p>
        </div>
      </motion.div>

      {/* 历史记录快捷入口 */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        onClick={onViewHistory}
        className="mt-8 w-full text-center text-primary-600 hover:text-primary-700 font-medium py-3 transition-all"
      >
        查看历史处理记录 →
      </motion.button>
    </div>
  )
}

export default VideoUpload

