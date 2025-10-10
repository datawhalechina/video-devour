import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import DocumentEditor from './DocumentEditor'
import BlockToolbar from './Toolbars/BlockToolbar'
import SelectionToolbar from './Toolbars/SelectionToolbar'
import { slateToMarkdown, markdownToSlate } from './editorUtils'
import { Eye, Edit3, Save, X } from 'lucide-react'

/**
 * 左右分栏编辑器
 * 左侧：富文本编辑器
 * 右侧：实时 Markdown 预览
 */
function SplitViewEditor({ initialMarkdown, onSave, onCancel }) {
  const [editorValue, setEditorValue] = useState(() => {
    return markdownToSlate(initialMarkdown || '')
  })
  const [isSaving, setIsSaving] = useState(false)
  const [viewMode, setViewMode] = useState('split') // 'split' | 'editor' | 'preview'

  // 实时转换为 Markdown 预览
  const markdownPreview = useMemo(() => {
    return slateToMarkdown(editorValue)
  }, [editorValue])

  const handleSave = async () => {
    setIsSaving(true)
    try {
      if (onSave) {
        await onSave(markdownPreview)
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleEditorChange = (value) => {
    setEditorValue(value)
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-bold text-gray-900">编辑报告</h2>
            
            {/* 视图模式切换 */}
            <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
              <ViewButton
                active={viewMode === 'editor'}
                onClick={() => setViewMode('editor')}
                icon={<Edit3 className="w-4 h-4" />}
                label="编辑"
              />
              <ViewButton
                active={viewMode === 'split'}
                onClick={() => setViewMode('split')}
                icon={<span className="text-xs font-bold">⫿</span>}
                label="分栏"
              />
              <ViewButton
                active={viewMode === 'preview'}
                onClick={() => setViewMode('preview')}
                icon={<Eye className="w-4 h-4" />}
                label="预览"
              />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center space-x-3">
            <motion.button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex items-center space-x-2"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <X className="w-4 h-4" />
              <span>取消</span>
            </motion.button>
            
            <motion.button
              onClick={handleSave}
              disabled={isSaving}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Save className="w-4 h-4" />
              <span>{isSaving ? '保存中...' : '保存'}</span>
            </motion.button>
          </div>
        </div>

        {/* 块级工具栏（仅在编辑模式显示） */}
        {(viewMode === 'editor' || viewMode === 'split') && <BlockToolbar />}
      </div>

      {/* 主内容区 */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex">
          {/* 左侧编辑器 */}
          {(viewMode === 'editor' || viewMode === 'split') && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`${
                viewMode === 'split' ? 'w-1/2 border-r border-gray-200' : 'w-full'
              } bg-white overflow-auto`}
            >
              <DocumentEditor
                initialValue={editorValue}
                onChange={handleEditorChange}
              />
              
              {/* 选区工具栏 */}
              <SelectionToolbar />
            </motion.div>
          )}

          {/* 右侧预览 */}
          {(viewMode === 'preview' || viewMode === 'split') && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className={`${
                viewMode === 'split' ? 'w-1/2' : 'w-full'
              } bg-gray-50 overflow-auto p-12`}
            >
              <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-12">
                <div className="prose prose-lg max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {markdownPreview}
                  </ReactMarkdown>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

function ViewButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center space-x-1 px-3 py-1.5 rounded transition-all text-sm ${
        active
          ? 'bg-white text-primary-600 shadow-sm'
          : 'text-gray-600 hover:text-gray-900'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

export default SplitViewEditor

