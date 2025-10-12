import { motion } from 'framer-motion'
import { Video, Upload, History, FileText, ArrowLeft, Clock, Play } from 'lucide-react'
import { useState, useEffect } from 'react'
import { getTaskStatus } from '../api/videoService'

function Header({ currentView, onNavigate, onBackToUpload, currentTask, onBackToProcessing }) {
  const [taskInfo, setTaskInfo] = useState(null)

  // 获取任务详情
  useEffect(() => {
    if (currentTask) {
      const fetchTaskInfo = async () => {
        try {
          const info = await getTaskStatus(currentTask)
          setTaskInfo(info)
        } catch (error) {
          console.error('获取任务信息失败:', error)
          setTaskInfo(null)
        }
      }
      fetchTaskInfo()
    } else {
      setTaskInfo(null)
    }
  }, [currentTask])

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-5 max-w-7xl">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={onBackToUpload}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Video className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">VideoDevour</h1>
              <p className="text-xs text-gray-500">智能视频分析工具</p>
            </div>
          </motion.div>

          {/* 任务状态指示器 */}
          {currentTask && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center space-x-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2"
            >
              <div className="flex items-center space-x-2">
                <Play className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">正在处理</span>
              </div>
              <div className="text-xs text-blue-700 bg-blue-100 px-2 py-1 rounded">
                {taskInfo?.filename || `${currentTask.slice(0, 8)}...`}
              </div>
            </motion.div>
          )}

          {/* Navigation */}
          <nav className="flex items-center space-x-3">
            {/* 如果有正在处理的任务且当前不在处理页面，显示返回处理页面按钮 */}
            {currentTask && currentView !== 'processing' && (
              <NavButton
                icon={<Clock className="w-5 h-5" />}
                label="查看进度"
                active={false}
                onClick={onBackToProcessing}
                variant="processing"
              />
            )}
            <NavButton
              icon={<Upload className="w-5 h-5" />}
              label="上传视频"
              active={currentView === 'upload'}
              onClick={() => onNavigate('upload')}
            />
            <NavButton
              icon={<History className="w-5 h-5" />}
              label="历史记录"
              active={currentView === 'history'}
              onClick={() => onNavigate('history')}
            />
          </nav>
        </div>
      </div>
    </header>
  )
}

function NavButton({ icon, label, active, onClick, variant = 'default' }) {
  const getButtonStyles = () => {
    if (variant === 'processing') {
      return 'bg-orange-500 text-white shadow-md hover:bg-orange-600'
    }
    return active
      ? 'bg-primary-500 text-white shadow-md'
      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
  }

  return (
    <motion.button
      onClick={onClick}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${getButtonStyles()}`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </motion.button>
  )
}

export default Header

