import { useMemo } from 'react'
import { useSlate } from 'slate-react'
import { Transforms } from 'slate'

/**
 * 列表块组件
 */
function ListBlock({ attributes, children, element }) {
  const { type } = element

  const Tag = useMemo(() => {
    switch (type) {
      case 'bulleted-list':
        return 'ul'
      case 'numbered-list':
        return 'ol'
      default:
        return 'ul'
    }
  }, [type])

  const className = useMemo(() => {
    const baseClass = 'my-2 ml-6'
    
    switch (type) {
      case 'bulleted-list':
        return `${baseClass} list-disc`
      case 'numbered-list':
        return `${baseClass} list-decimal`
      default:
        return baseClass
    }
  }, [type])

  return (
    <Tag {...attributes} className={className}>
      {children}
    </Tag>
  )
}

/**
 * 列表项组件
 */
export function ListItemBlock({ attributes, children, element }) {
  return (
    <li {...attributes} className="text-base text-gray-800 leading-relaxed my-1">
      {children}
    </li>
  )
}

/**
 * 待办列表项组件
 */
export function TodoListItemBlock({ attributes, children, element }) {
  const editor = useSlate()
  const { checked = false } = element

  const handleCheck = (e) => {
    e.preventDefault()
    const path = editor.selection ? editor.selection.anchor.path.slice(0, -1) : []
    
    Transforms.setNodes(
      editor,
      { checked: !checked },
      { at: path }
    )
  }

  return (
    <div {...attributes} className="flex items-start space-x-2 my-1">
      <div contentEditable={false} className="flex-shrink-0 pt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={handleCheck}
          className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 cursor-pointer"
        />
      </div>
      <div
        className={`flex-1 text-base leading-relaxed ${
          checked ? 'text-gray-500 line-through' : 'text-gray-800'
        }`}
      >
        {children}
      </div>
    </div>
  )
}

export default ListBlock

