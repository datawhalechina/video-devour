import { useEffect, useRef, useState } from 'react'
import { useSlate } from 'slate-react'
import { Editor, Range } from 'slate'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Code,
  Link as LinkIcon,
  Highlighter,
  Palette,
} from 'lucide-react'
import AIButton from './AIButton'
import { toggleMark, isMarkActive, insertLink, unwrapLink, isLinkActive } from '../editorUtils'
import { MARKS } from '../editorConfig'

/**
 * 选区浮动工具栏
 */
function SelectionToolbar() {
  const editor = useSlate()
  const toolbarRef = useRef(null)
  const [position, setPosition] = useState(null)
  const [showLinkInput, setShowLinkInput] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')

  useEffect(() => {
    const { selection } = editor

    if (
      !selection ||
      !toolbarRef.current ||
      Range.isCollapsed(selection) ||
      Editor.string(editor, selection) === ''
    ) {
      setPosition(null)
      setShowLinkInput(false)
      return
    }

    const domSelection = window.getSelection()
    if (!domSelection || domSelection.rangeCount === 0) {
      setPosition(null)
      return
    }

    const domRange = domSelection.getRangeAt(0)
    const rect = domRange.getBoundingClientRect()

    setPosition({
      top: rect.top + window.scrollY - 60,
      left: rect.left + window.scrollX + rect.width / 2,
    })
  }, [editor, editor.selection])

  const handleToggleMark = (mark) => {
    toggleMark(editor, mark)
    editor.selection && editor.focus()
  }

  const handleAddLink = () => {
    if (linkUrl.trim()) {
      insertLink(editor, linkUrl.trim())
      setShowLinkInput(false)
      setLinkUrl('')
    }
  }

  const handleRemoveLink = () => {
    unwrapLink(editor)
    setShowLinkInput(false)
  }

  if (!position) return null

  return (
    <AnimatePresence>
      <motion.div
        ref={toolbarRef}
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="fixed z-50 bg-gray-900 rounded-lg shadow-2xl border border-gray-700"
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
          transform: 'translateX(-50%)',
        }}
      >
        {!showLinkInput ? (
          <div className="flex items-center space-x-1 p-2">
            <ToolbarButton
              active={isMarkActive(editor, MARKS.BOLD)}
              onClick={() => handleToggleMark(MARKS.BOLD)}
              icon={<Bold className="w-4 h-4" />}
              tooltip="粗体 (Ctrl+B)"
            />
            <ToolbarButton
              active={isMarkActive(editor, MARKS.ITALIC)}
              onClick={() => handleToggleMark(MARKS.ITALIC)}
              icon={<Italic className="w-4 h-4" />}
              tooltip="斜体 (Ctrl+I)"
            />
            <ToolbarButton
              active={isMarkActive(editor, MARKS.UNDERLINE)}
              onClick={() => handleToggleMark(MARKS.UNDERLINE)}
              icon={<Underline className="w-4 h-4" />}
              tooltip="下划线 (Ctrl+U)"
            />
            <ToolbarButton
              active={isMarkActive(editor, MARKS.STRIKETHROUGH)}
              onClick={() => handleToggleMark(MARKS.STRIKETHROUGH)}
              icon={<Strikethrough className="w-4 h-4" />}
              tooltip="删除线"
            />
            
            <div className="w-px h-6 bg-gray-700 mx-1" />
            
            <ToolbarButton
              active={isMarkActive(editor, MARKS.CODE)}
              onClick={() => handleToggleMark(MARKS.CODE)}
              icon={<Code className="w-4 h-4" />}
              tooltip="行内代码"
            />
            <ToolbarButton
              active={isLinkActive(editor)}
              onClick={() => {
                if (isLinkActive(editor)) {
                  handleRemoveLink()
                } else {
                  setShowLinkInput(true)
                }
              }}
              icon={<LinkIcon className="w-4 h-4" />}
              tooltip="链接 (Ctrl+K)"
            />
            <ToolbarButton
              active={isMarkActive(editor, MARKS.HIGHLIGHT)}
              onClick={() => handleToggleMark(MARKS.HIGHLIGHT)}
              icon={<Highlighter className="w-4 h-4" />}
              tooltip="高亮"
            />
            
            <div className="w-px h-6 bg-gray-700 mx-1" />
            
            {/* AI 功能 */}
            <AIButton />
          </div>
        ) : (
          <div className="flex items-center space-x-2 p-2">
            <input
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddLink()
                } else if (e.key === 'Escape') {
                  setShowLinkInput(false)
                  setLinkUrl('')
                }
              }}
              placeholder="输入链接地址..."
              autoFocus
              className="px-3 py-1.5 bg-gray-800 text-white text-sm border border-gray-700 rounded focus:outline-none focus:ring-2 focus:ring-primary-500 w-64"
            />
            <button
              onClick={handleAddLink}
              className="px-3 py-1.5 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 transition-colors"
            >
              确定
            </button>
            <button
              onClick={() => {
                setShowLinkInput(false)
                setLinkUrl('')
              }}
              className="px-3 py-1.5 bg-gray-700 text-white text-sm rounded hover:bg-gray-600 transition-colors"
            >
              取消
            </button>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

function ToolbarButton({ active, onClick, icon, tooltip }) {
  return (
    <button
      onMouseDown={(e) => {
        e.preventDefault()
        onClick()
      }}
      className={`p-2 rounded transition-all ${
        active
          ? 'bg-primary-600 text-white'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white'
      }`}
      title={tooltip}
    >
      {icon}
    </button>
  )
}

export default SelectionToolbar

