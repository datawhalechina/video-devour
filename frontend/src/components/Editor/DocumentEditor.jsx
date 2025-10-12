import { useCallback, useMemo, useState, useEffect } from 'react'
import { createEditor, Transforms, Editor, Element as SlateElement } from 'slate'
import { Slate, Editable, withReact } from 'slate-react'
import { withHistory } from 'slate-history'
import isHotkey from 'is-hotkey'
import EditorElement from './EditorElement'
import EditorLeaf from './EditorLeaf'
import SlashMenu from './Toolbars/SlashMenu'
import FloatingToolbar from './Toolbars/FloatingToolbar'
import { withMarkdownShortcuts } from './Plugins/withMarkdownShortcuts'
import useEditorStore from '../../store/editorStore'
import { toggleMark, isMarkActive, toggleBlock, createEmptyDocument } from './editorUtils'
import { HOTKEYS, BLOCK_TYPES } from './editorConfig'

/**
 * 文档编辑器核心组件
 */
function DocumentEditor({ initialValue, onChange, readOnly = false }) {
  const { setDocument, setSelection } = useEditorStore()
  
  // 创建编辑器实例（带历史记录、React 支持和 Markdown 快捷输入）
  const editor = useMemo(
    () => withMarkdownShortcuts(withHistory(withReact(createEditor()))),
    []
  )
  
  // 初始化文档值
  const [value, setValue] = useState(
    initialValue && initialValue.length > 0 
      ? initialValue 
      : createEmptyDocument()
  )

  // 渲染元素
  const renderElement = useCallback(props => <EditorElement {...props} />, [])
  
  // 渲染叶子节点
  const renderLeaf = useCallback(props => <EditorLeaf {...props} />, [])

  // 处理文档变化
  const handleChange = useCallback((newValue) => {
    setValue(newValue)
    setDocument(newValue)
    if (onChange) {
      onChange(newValue)
    }
  }, [onChange, setDocument])

  // 处理选区变化
  const handleSelectionChange = useCallback(() => {
    setSelection(editor.selection)
  }, [editor.selection, setSelection])

  // 处理键盘事件
  const handleKeyDown = useCallback((event) => {
    // 快捷键处理
    for (const hotkey in HOTKEYS) {
      if (isHotkey(hotkey, event)) {
        event.preventDefault()
        const mark = HOTKEYS[hotkey]
        
        if (mark === 'undo') {
          editor.undo()
        } else if (mark === 'redo') {
          editor.redo()
        } else {
          toggleMark(editor, mark)
        }
        return
      }
    }

    // Enter 键处理
    if (event.key === 'Enter') {
      const { selection } = editor
      if (!selection) return

      const [match] = Editor.nodes(editor, {
        match: n => SlateElement.isElement(n) && Editor.isBlock(editor, n),
      })

      if (match) {
        const [block] = match
        
        // 在代码块中按 Enter 插入换行
        if (block.type === BLOCK_TYPES.CODE) {
          event.preventDefault()
          editor.insertText('\n')
          return
        }
      }
    }

    // Tab 键处理（在代码块中插入制表符）
    if (event.key === 'Tab') {
      const { selection } = editor
      if (!selection) return

      const [match] = Editor.nodes(editor, {
        match: n => SlateElement.isElement(n) && n.type === BLOCK_TYPES.CODE,
      })

      if (match) {
        event.preventDefault()
        editor.insertText('  ') // 插入两个空格
        return
      }
    }

    // Backspace 键处理
    if (event.key === 'Backspace') {
      const { selection } = editor
      if (!selection) return

      const [match] = Editor.nodes(editor, {
        match: n => SlateElement.isElement(n) && Editor.isBlock(editor, n),
      })

      if (match) {
        const [block, path] = match
        const start = Editor.start(editor, path)
        
        // 如果在块的开始位置，且不是普通段落，转换为段落
        if (
          selection.anchor.offset === 0 &&
          Editor.isStart(editor, selection.anchor, path) &&
          block.type !== BLOCK_TYPES.PARAGRAPH
        ) {
          event.preventDefault()
          Transforms.setNodes(editor, { type: BLOCK_TYPES.PARAGRAPH })
          return
        }
      }
    }
  }, [editor])

  // 装饰函数（用于语法高亮等）
  const decorate = useCallback(([node, path]) => {
    const ranges = []
    
    // 这里可以添加代码高亮、搜索高亮等装饰逻辑
    
    return ranges
  }, [])

  return (
    <div className="document-editor h-full flex flex-col">
      <Slate
        editor={editor}
        initialValue={value}
        onChange={handleChange}
        onSelectionChange={handleSelectionChange}
      >
        {/* 顶部工具栏 */}
        {!readOnly && <FloatingToolbar />}
        
        {/* 编辑区域 */}
        <div className="flex-1 overflow-y-auto">
          <Editable
            renderElement={renderElement}
            renderLeaf={renderLeaf}
            placeholder="开始输入内容，输入 / 查看命令菜单..."
            spellCheck
            autoFocus={!readOnly}
            readOnly={readOnly}
            onKeyDown={handleKeyDown}
            decorate={decorate}
            className={`
              outline-none px-16 py-12 min-h-full
              prose prose-lg max-w-none
              ${readOnly ? 'cursor-default' : 'cursor-text'}
            `}
            style={{
              caretColor: readOnly ? 'transparent' : 'auto',
            }}
          />
        </div>
        
        {/* 斜杠命令菜单 */}
        {!readOnly && <SlashMenu />}
      </Slate>
    </div>
  )
}

export default DocumentEditor

