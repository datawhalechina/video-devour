import { useEffect, useRef, useState, useMemo } from 'react'
import { useSlate } from 'slate-react'
import { Editor, Transforms, Range } from 'slate'
import { motion, AnimatePresence } from 'framer-motion'
import { SLASH_COMMANDS } from '../editorConfig'

/**
 * 斜杠命令菜单
 */
function SlashMenu() {
  const editor = useSlate()
  const menuRef = useRef(null)
  const selectedItemRef = useRef(null)
  const [show, setShow] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const [target, setTarget] = useState(null)

  // 过滤命令
  const filteredCommands = useMemo(() => {
    if (!search) return SLASH_COMMANDS

    const searchLower = search.toLowerCase()
    return SLASH_COMMANDS.filter((cmd) => {
      return (
        cmd.title.toLowerCase().includes(searchLower) ||
        cmd.description.toLowerCase().includes(searchLower) ||
        cmd.keywords.some((kw) => kw.includes(searchLower))
      )
    })
  }, [search])

  useEffect(() => {
    const { selection } = editor

    if (!selection || !Range.isCollapsed(selection)) {
      setShow(false)
      return
    }

    const [start] = Range.edges(selection)
    const beforeText = Editor.string(editor, {
      anchor: { path: start.path, offset: 0 },
      focus: start,
    })

    // 检查是否输入了 /
    const match = beforeText.match(/\/(\w*)$/)
    
    if (match) {
      const searchText = match[1]
      setSearch(searchText)
      setTarget(selection)
      setShow(true)

      // 计算菜单位置
      const domSelection = window.getSelection()
      if (domSelection && domSelection.rangeCount > 0) {
        const domRange = domSelection.getRangeAt(0)
        const rect = domRange.getBoundingClientRect()
        setPosition({
          top: rect.bottom + window.scrollY + 5,
          left: rect.left + window.scrollX,
        })
      }
    } else {
      setShow(false)
    }
  }, [editor, editor.selection])

  useEffect(() => {
    setSelectedIndex(0)
  }, [search])

  // 自动滚动选中项到可见区域
  useEffect(() => {
    if (selectedItemRef.current) {
      selectedItemRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
    }
  }, [selectedIndex])

  // 键盘事件处理
  useEffect(() => {
    if (!show) return

    const handleKeyDown = (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % filteredCommands.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length)
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        if (filteredCommands[selectedIndex]) {
          handleSelectCommand(filteredCommands[selectedIndex])
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        setShow(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [show, selectedIndex, filteredCommands])

  const handleSelectCommand = (command) => {
    if (!target) return

    // 删除 / 和搜索文本
    Transforms.delete(editor, {
      at: target,
      distance: search.length + 1,
      reverse: true,
      unit: 'character',
    })

    // 插入对应的块
    insertBlock(editor, command.type)
    
    setShow(false)
    setSearch('')
    setSelectedIndex(0)
  }

  const insertBlock = (editor, type) => {
    const newBlock = {
      type,
      children: [{ text: '' }],
    }

    // 特殊块的额外属性
    if (type === 'callout') {
      newBlock.calloutType = 'info'
    } else if (type === 'code-block') {
      newBlock.language = 'javascript'
    } else if (type === 'heading-one' || type === 'heading-two' || type === 'heading-three') {
      Transforms.setNodes(editor, { type })
      return
    } else if (type === 'divider') {
      Transforms.insertNodes(editor, newBlock)
      Transforms.insertNodes(editor, {
        type: 'paragraph',
        children: [{ text: '' }],
      })
      return
    } else if (type === 'image') {
      // 插入图片 - 提示用户输入 URL
      const url = window.prompt('请输入图片 URL:')
      if (url) {
        newBlock.url = url
        newBlock.alt = ''
        Transforms.insertNodes(editor, newBlock)
        Transforms.insertNodes(editor, {
          type: 'paragraph',
          children: [{ text: '' }],
        })
      }
      return
    } else if (type === 'video') {
      // 插入视频 - 提示用户输入 URL
      const url = window.prompt('请输入视频 URL:')
      if (url) {
        newBlock.url = url
        Transforms.insertNodes(editor, newBlock)
        Transforms.insertNodes(editor, {
          type: 'paragraph',
          children: [{ text: '' }],
        })
      }
      return
    }

    Transforms.setNodes(editor, newBlock)
  }

  if (!show || filteredCommands.length === 0) return null

  return (
    <AnimatePresence>
      <motion.div
        ref={menuRef}
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="fixed z-50 bg-white rounded-xl shadow-2xl border border-gray-200 w-80 max-h-96 overflow-y-auto"
        style={{
          top: `${position.top}px`,
          left: `${position.left}px`,
        }}
      >
        <div className="p-2">
          {filteredCommands.map((command, index) => (
            <motion.button
              key={command.id}
              ref={index === selectedIndex ? selectedItemRef : null}
              onClick={() => handleSelectCommand(command)}
              className={`w-full text-left px-4 py-3 rounded-lg transition-all flex items-center space-x-3 ${
                index === selectedIndex
                  ? 'bg-primary-50 border-primary-200'
                  : 'hover:bg-gray-50'
              }`}
              whileHover={{ x: 2 }}
            >
              <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-gray-100 rounded-lg text-xl">
                {command.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-gray-900">{command.title}</div>
                <div className="text-xs text-gray-500 truncate">{command.description}</div>
              </div>
            </motion.button>
          ))}
        </div>

        {/* 提示 */}
        <div className="border-t border-gray-200 px-4 py-2 bg-gray-50 text-xs text-gray-500 flex items-center justify-between">
          <span>↑↓ 选择</span>
          <span>Enter 确认</span>
          <span>Esc 关闭</span>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default SlashMenu

