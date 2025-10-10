import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Check, X, Loader2, ArrowRight } from 'lucide-react'
import { rewriteText } from '../../../api/aiService'

/**
 * AI 重写面板
 * 显示 AI 建议，支持接受/拒绝
 */
function AIRewritePanel({ originalText, onAccept, onReject, position }) {
  const [loading, setLoading] = useState(false)
  const [suggestion, setSuggestion] = useState(null)
  const [selectedInstruction, setSelectedInstruction] = useState('优化')

  const instructions = [
    { id: '优化', label: '优化', icon: '✨', desc: '让文本更清晰流畅' },
    { id: '扩展', label: '扩展', icon: '📝', desc: '增加更多细节' },
    { id: '精简', label: '精简', icon: '✂️', desc: '删减冗余内容' },
    { id: '改写', label: '改写', icon: '🔄', desc: '换一种表达方式' },
    { id: '专业化', label: '专业化', icon: '🎓', desc: '使用专业术语' },
    { id: '通俗化', label: '通俗化', icon: '💬', desc: '简化表达' },
  ]

  const handleRewrite = async (instruction) => {
    setLoading(true)
    setSelectedInstruction(instruction)
    
    try {
      const result = await rewriteText(originalText, instruction)
      setSuggestion(result)
    } catch (error) {
      console.error('AI 重写失败:', error)
      alert('AI 重写失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleAccept = () => {
    if (suggestion) {
      onAccept(suggestion)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.95 }}
      className="fixed z-50 bg-white rounded-xl shadow-2xl border border-gray-200 w-[600px] max-h-[80vh] overflow-hidden"
      style={position}
    >
      {/* 头部 */}
      <div className="bg-gradient-to-r from-primary-600 to-purple-600 px-6 py-4 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5" />
            <h3 className="text-lg font-bold">AI 智能重写</h3>
          </div>
          <button
            onClick={onReject}
            className="text-white hover:bg-white/20 rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 内容区 */}
      <div className="max-h-[60vh] overflow-y-auto">
        {/* 原始文本 */}
        <div className="p-6 bg-gray-50 border-b border-gray-200">
          <div className="text-xs font-semibold text-gray-500 mb-2">原文</div>
          <div className="text-sm text-gray-800 leading-relaxed">
            {originalText}
          </div>
        </div>

        {/* 指令选择 */}
        {!suggestion && (
          <div className="p-6">
            <div className="text-sm font-semibold text-gray-700 mb-4">选择重写方式</div>
            <div className="grid grid-cols-2 gap-3">
              {instructions.map((inst) => (
                <motion.button
                  key={inst.id}
                  onClick={() => handleRewrite(inst.id)}
                  disabled={loading}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    loading && selectedInstruction === inst.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                  whileHover={{ scale: loading ? 1 : 1.02 }}
                  whileTap={{ scale: loading ? 1 : 0.98 }}
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xl">{inst.icon}</span>
                    <span className="font-semibold text-gray-900">{inst.label}</span>
                  </div>
                  <div className="text-xs text-gray-500">{inst.desc}</div>
                </motion.button>
              ))}
            </div>

            {loading && (
              <div className="mt-6 flex items-center justify-center space-x-2 text-primary-600">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm font-medium">AI 正在处理中...</span>
              </div>
            )}
          </div>
        )}

        {/* AI 建议 */}
        {suggestion && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-semibold text-gray-700">AI 建议</div>
              <button
                onClick={() => {
                  setSuggestion(null)
                  setSelectedInstruction('优化')
                }}
                className="text-xs text-primary-600 hover:text-primary-700 font-medium"
              >
                重新生成
              </button>
            </div>
            
            <div className="relative">
              <div className="absolute -left-4 top-0 bottom-0 w-1 bg-gradient-to-b from-primary-500 to-purple-500 rounded-full"></div>
              <div className="text-sm text-gray-800 leading-relaxed pl-4">
                {suggestion}
              </div>
            </div>

            {/* 对比视图 */}
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center space-x-2 text-blue-700 text-xs font-medium mb-2">
                <ArrowRight className="w-4 h-4" />
                <span>文字变化</span>
              </div>
              <div className="text-xs text-blue-600">
                原文 {originalText.length} 字 → {suggestion.length} 字
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 底部操作 */}
      {suggestion && (
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex items-center justify-end space-x-3">
          <motion.button
            onClick={onReject}
            className="px-6 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors font-medium"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            取消
          </motion.button>
          <motion.button
            onClick={handleAccept}
            className="px-6 py-2 bg-gradient-to-r from-primary-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all font-medium flex items-center space-x-2"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Check className="w-4 h-4" />
            <span>接受建议</span>
          </motion.button>
        </div>
      )}
    </motion.div>
  )
}

export default AIRewritePanel

