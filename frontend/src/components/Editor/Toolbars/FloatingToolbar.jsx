import { useState } from 'react'
import { useSlate } from 'slate-react'
import { Editor, Transforms, Element as SlateElement } from 'slate'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Code,
  Link,
  List,
  ListOrdered,
  Quote,
  Heading1,
  Heading2,
  Heading3,
  AlignLeft,
  AlignCenter,
  AlignRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'

/**
 * 格式化按钮组件
 */
function FormatButton({ format, icon: Icon, title }) {
  const editor = useSlate()
  
  const isActive = () => {
    const marks = Editor.marks(editor)
    return marks ? marks[format] === true : false
  }

  const handleClick = (e) => {
    e.preventDefault()
    const isCurrentlyActive = isActive()
    
    if (isCurrentlyActive) {
      Editor.removeMark(editor, format)
    } else {
      Editor.addMark(editor, format, true)
    }
  }

  return (
    <button
      onMouseDown={handleClick}
      className={`p-2 rounded-lg transition-all ${
        isActive()
          ? 'bg-blue-100 text-blue-600'
          : 'hover:bg-gray-100 text-gray-600'
      }`}
      title={title}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}

/**
 * 块级按钮组件
 */
function BlockButton({ format, icon: Icon, title }) {
  const editor = useSlate()
  
  const isActive = () => {
    const [match] = Editor.nodes(editor, {
      match: n => SlateElement.isElement(n) && n.type === format,
    })
    return !!match
  }

  const handleClick = (e) => {
    e.preventDefault()
    const isCurrentlyActive = isActive()
    
    Transforms.setNodes(
      editor,
      { type: isCurrentlyActive ? 'paragraph' : format },
      { match: n => SlateElement.isElement(n) && Editor.isBlock(editor, n) }
    )
  }

  return (
    <button
      onMouseDown={handleClick}
      className={`p-2 rounded-lg transition-all ${
        isActive()
          ? 'bg-blue-100 text-blue-600'
          : 'hover:bg-gray-100 text-gray-600'
      }`}
      title={title}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}

/**
 * 顶部浮动工具栏
 */
function FloatingToolbar() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <div className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex items-center justify-between px-4 py-2">
        {/* 工具栏按钮组 - 单行显示 */}
        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-1 overflow-hidden"
            >
              {/* 文本格式 */}
              <FormatButton format="bold" icon={Bold} title="粗体 (Ctrl+B)" />
              <FormatButton format="italic" icon={Italic} title="斜体 (Ctrl+I)" />
              <FormatButton format="underline" icon={Underline} title="下划线 (Ctrl+U)" />
              <FormatButton format="strikethrough" icon={Strikethrough} title="删除线" />
              <FormatButton format="code" icon={Code} title="行内代码" />
              <FormatButton format="link" icon={Link} title="插入链接" />
              
              <div className="w-px h-6 bg-gray-300 mx-2" />
              
              {/* 标题 */}
              <BlockButton format="heading-one" icon={Heading1} title="一级标题" />
              <BlockButton format="heading-two" icon={Heading2} title="二级标题" />
              <BlockButton format="heading-three" icon={Heading3} title="三级标题" />
              
              <div className="w-px h-6 bg-gray-300 mx-2" />
              
              {/* 列表 */}
              <BlockButton format="bulleted-list" icon={List} title="无序列表" />
              <BlockButton format="numbered-list" icon={ListOrdered} title="有序列表" />
              <BlockButton format="quote" icon={Quote} title="引用" />
              
              <div className="w-px h-6 bg-gray-300 mx-2" />
              
              {/* 对齐 */}
              <BlockButton format="align-left" icon={AlignLeft} title="左对齐" />
              <BlockButton format="align-center" icon={AlignCenter} title="居中" />
              <BlockButton format="align-right" icon={AlignRight} title="右对齐" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* 折叠按钮 */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
          title={isCollapsed ? '展开工具栏' : '折叠工具栏'}
        >
          {isCollapsed ? (
            <ChevronDown className="w-4 h-4 text-gray-600" />
          ) : (
            <ChevronUp className="w-4 h-4 text-gray-600" />
          )}
        </button>
      </div>
    </div>
  )
}

export default FloatingToolbar

