import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react'
import { getTaskStatus } from '../api/videoService'

const PROCESSING_STAGES = [
  { key: 'uploading', label: '上传视频', icon: '📤' },
  { key: 'extracting_audio', label: '提取音频', icon: '🎵' },
  { key: 'asr', label: '语音识别', icon: '🎙️' },
  { key: 'generating_outline', label: '生成大纲', icon: '📝' },
  { key: 'extracting_frames', label: '提取关键帧', icon: '🖼️' },
  { key: 'vlm_analysis', label: 'VLM 分析', icon: '🤖' },
  { key: 'generating_report', label: '生成报告', icon: '📄' },
  { key: 'completed', label: '完成', icon: '✅' }
]

function ProcessingStatus({ taskId, onComplete, onCancel }) {
  const [status, setStatus] = useState({
    stage: 'uploading',
    progress: 0,
    message: '正在处理...',
    error: null
  })
  const [elapsedTime, setElapsedTime] = useState(0)

  useEffect(() => {
    // 从localStorage获取任务开始时间
    const getTaskStartTime = () => {
      try {
        const stored = localStorage.getItem('videodevour_current_task');
        if (stored) {
          const taskData = JSON.parse(stored);
          return taskData.startTime || Date.now();
        }
      } catch (error) {
        console.error('获取任务开始时间失败:', error);
      }
      return Date.now();
    };

    const startTime = getTaskStartTime();
    
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000))
    }, 1000)

    return () => clearInterval(timer)
  }, [taskId])

  useEffect(() => {
    if (!taskId) return

    const pollStatus = async () => {
      try {
        const result = await getTaskStatus(taskId)
        setStatus(result)

        if (result.stage === 'completed') {
          onComplete(result.report)
        } else if (result.stage === 'error') {
          // 错误处理已在 status 中
        }
      } catch (err) {
        // 检查是否是404错误（任务被删除）
        if (err.message && err.message.includes('404')) {
          console.log('任务已被删除，返回上传页面')
          onCancel() // 返回上传页面
          return
        }
        
        setStatus({
          stage: 'error',
          progress: 0,
          message: err.message || '获取状态失败',
          error: err.message
        })
      }
    }

    // 立即执行一次
    pollStatus()

    // 每2秒轮询一次
    const interval = setInterval(pollStatus, 2000)

    return () => clearInterval(interval)
  }, [taskId, onComplete, onCancel])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const currentStageIndex = PROCESSING_STAGES.findIndex(s => s.key === status.stage)
  const isError = status.stage === 'error'
  const isCompleted = status.stage === 'completed'

  return (
    <div className="max-w-4xl mx-auto">
      {/* 状态卡片 */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-xl p-8"
      >
        {/* 头部 */}
        <div className="text-center mb-8">
          {isError ? (
            <>
              <XCircle className="w-20 h-20 text-red-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800 mb-2">处理失败</h2>
              <p className="text-red-600">{status.error}</p>
            </>
          ) : isCompleted ? (
            <>
              <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800 mb-2">处理完成！</h2>
              <p className="text-gray-600">报告已生成，正在跳转...</p>
            </>
          ) : (
            <>
              <Loader2 className="w-20 h-20 text-primary-500 mx-auto mb-4 animate-spin" />
              <h2 className="text-2xl font-bold text-gray-800 mb-2">正在处理视频</h2>
              <p className="text-gray-600">{status.message}</p>
            </>
          )}
        </div>

        {/* 进度条 */}
        {!isError && !isCompleted && (
          <div className="mb-8">
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-primary-500 to-purple-600"
                initial={{ width: 0 }}
                animate={{ width: `${status.progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <div className="flex justify-between mt-2 text-sm text-gray-600">
              <span>{status.progress}%</span>
              <span className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span>已用时 {formatTime(elapsedTime)}</span>
              </span>
            </div>
          </div>
        )}

        {/* 处理阶段 */}
        <div className="space-y-4">
          {PROCESSING_STAGES.map((stage, index) => {
            const isCurrent = index === currentStageIndex
            const isCompleted = index < currentStageIndex
            const isPending = index > currentStageIndex

            return (
              <motion.div
                key={stage.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex items-center space-x-4 p-4 rounded-lg transition-all ${
                  isCurrent
                    ? 'bg-primary-50 border-2 border-primary-500'
                    : isCompleted
                    ? 'bg-green-50'
                    : 'bg-gray-50'
                }`}
              >
                <div className="text-3xl">{stage.icon}</div>
                <div className="flex-1">
                  <p className={`font-semibold ${
                    isCurrent ? 'text-primary-700' : 
                    isCompleted ? 'text-green-700' : 
                    'text-gray-500'
                  }`}>
                    {stage.label}
                  </p>
                </div>
                <div>
                  {isCompleted ? (
                    <CheckCircle className="w-6 h-6 text-green-500" />
                  ) : isCurrent ? (
                    <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                  ) : (
                    <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* 操作按钮 */}
        <div className="mt-8 flex justify-center">
          {isError && (
            <motion.button
              onClick={onCancel}
              className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              返回重试
            </motion.button>
          )}
        </div>

        {/* 提示信息 */}
        {!isError && !isCompleted && (
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
            <p className="font-semibold mb-1">💡 处理提示</p>
            <p>处理时间取决于视频长度和内容复杂度，请耐心等待。您可以关闭此页面，稍后在历史记录中查看结果。</p>
          </div>
        )}
      </motion.div>
    </div>
  )
}

export default ProcessingStatus

