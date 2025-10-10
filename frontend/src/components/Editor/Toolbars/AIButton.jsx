import { useState } from 'react'
import { useSlate } from 'slate-react'
import { Editor } from 'slate'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import AIRewritePanel from '../AI/AIRewritePanel'
import { getSelectedText } from '../editorUtils'

/**
 * AI 功能按钮（添加到选区工具栏）
 */
function AIButton() {
  const editor = useSlate()
  const [showPanel, setShowPanel] = useState(false)
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0 })
  const [selectedText, setSelectedText] = useState('')

  const handleClick = () => {
    const text = getSelectedText(editor)
    if (!text || text.trim() === '') {
      alert('请先选择要重写的文本')
      return
    }

    setSelectedText(text)

    // 计算面板位置
    const domSelection = window.getSelection()
    if (domSelection && domSelection.rangeCount > 0) {
      const domRange = domSelection.getRangeAt(0)
      const rect = domRange.getBoundingClientRect()
      
      setPanelPosition({
        top: rect.bottom + window.scrollY + 10,
        left: rect.left + window.scrollX,
      })
    }

    setShowPanel(true)
  }

  const handleAccept = (newText) => {
    // 替换选中的文本
    if (editor.selection) {
      editor.insertText(newText)
    }
    setShowPanel(false)
  }

  const handleReject = () => {
    setShowPanel(false)
  }

  return (
    <>
      <button
        onMouseDown={(e) => {
          e.preventDefault()
          handleClick()
        }}
        className="p-2 rounded transition-all text-purple-400 hover:bg-purple-900/30 hover:text-purple-300"
        title="AI 重写"
      >
        <Sparkles className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {showPanel && (
          <>
            {/* 遮罩层 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/20 z-40"
              onClick={handleReject}
            />

            {/* AI 面板 */}
            <AIRewritePanel
              originalText={selectedText}
              onAccept={handleAccept}
              onReject={handleReject}
              position={panelPosition}
            />
          </>
        )}
      </AnimatePresence>
    </>
  )
}

export default AIButton

