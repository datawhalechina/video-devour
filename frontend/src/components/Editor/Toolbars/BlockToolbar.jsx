import { useState } from 'react'
import { useSlate } from 'slate-react'
import { motion } from 'framer-motion'
import {
  Type,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  Code,
  Image,
  AlignLeft,
  AlignCenter,
  AlignRight,
} from 'lucide-react'
import { toggleBlock, setBlockProperty, getCurrentBlock } from '../editorUtils'
import { BLOCK_TYPES, ALIGN_TYPES } from '../editorConfig'

/**
 * 块级工具栏（顶部固定）
 */
function BlockToolbar() {
  const editor = useSlate()
  const currentBlock = getCurrentBlock(editor)
  const [showAlignMenu, setShowAlignMenu] = useState(false)

  const handleToggleBlock = (type) => {
    toggleBlock(editor, type)
  }

  const handleSetAlign = (align) => {
    setBlockProperty(editor, { align })
    setShowAlignMenu(false)
  }

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-3">
      <div className="flex items-center space-x-2 flex-wrap gap-2">
        {/* 块类型 */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.PARAGRAPH}
            onClick={() => handleToggleBlock(BLOCK_TYPES.PARAGRAPH)}
            icon={<Type className="w-4 h-4" />}
            label="正文"
          />
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.HEADING_1}
            onClick={() => handleToggleBlock(BLOCK_TYPES.HEADING_1)}
            icon={<Heading1 className="w-4 h-4" />}
            label="H1"
          />
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.HEADING_2}
            onClick={() => handleToggleBlock(BLOCK_TYPES.HEADING_2)}
            icon={<Heading2 className="w-4 h-4" />}
            label="H2"
          />
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.HEADING_3}
            onClick={() => handleToggleBlock(BLOCK_TYPES.HEADING_3)}
            icon={<Heading3 className="w-4 h-4" />}
            label="H3"
          />
        </div>

        {/* 列表 */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.BULLET_LIST}
            onClick={() => handleToggleBlock(BLOCK_TYPES.BULLET_LIST)}
            icon={<List className="w-4 h-4" />}
            label="无序列表"
          />
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.NUMBERED_LIST}
            onClick={() => handleToggleBlock(BLOCK_TYPES.NUMBERED_LIST)}
            icon={<ListOrdered className="w-4 h-4" />}
            label="有序列表"
          />
        </div>

        {/* 其他块 */}
        <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.QUOTE}
            onClick={() => handleToggleBlock(BLOCK_TYPES.QUOTE)}
            icon={<Quote className="w-4 h-4" />}
            label="引用"
          />
          <ToolbarButton
            active={currentBlock?.type === BLOCK_TYPES.CODE}
            onClick={() => handleToggleBlock(BLOCK_TYPES.CODE)}
            icon={<Code className="w-4 h-4" />}
            label="代码"
          />
        </div>

        {/* 对齐方式 */}
        <div className="relative flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
          <ToolbarButton
            active={!currentBlock?.align || currentBlock?.align === ALIGN_TYPES.LEFT}
            onClick={() => handleSetAlign(ALIGN_TYPES.LEFT)}
            icon={<AlignLeft className="w-4 h-4" />}
            label="左对齐"
          />
          <ToolbarButton
            active={currentBlock?.align === ALIGN_TYPES.CENTER}
            onClick={() => handleSetAlign(ALIGN_TYPES.CENTER)}
            icon={<AlignCenter className="w-4 h-4" />}
            label="居中"
          />
          <ToolbarButton
            active={currentBlock?.align === ALIGN_TYPES.RIGHT}
            onClick={() => handleSetAlign(ALIGN_TYPES.RIGHT)}
            icon={<AlignRight className="w-4 h-4" />}
            label="右对齐"
          />
        </div>
      </div>
    </div>
  )
}

function ToolbarButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center space-x-1 px-3 py-1.5 rounded transition-all text-sm ${
        active
          ? 'bg-white text-primary-600 shadow-sm'
          : 'text-gray-700 hover:bg-gray-200'
      }`}
      title={label}
    >
      {icon}
      <span className="hidden md:inline">{label}</span>
    </button>
  )
}

export default BlockToolbar

