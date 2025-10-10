import { useSlate, useSelected, useFocused } from 'slate-react'
import { Transforms } from 'slate'
import { Trash2 } from 'lucide-react'

/**
 * 视频块组件
 */
function VideoBlock({ attributes, children, element }) {
  const editor = useSlate()
  const selected = useSelected()
  const focused = useFocused()
  const { url } = element

  const handleDelete = () => {
    const path = editor.selection ? editor.selection.anchor.path.slice(0, -1) : []
    Transforms.removeNodes(editor, { at: path })
  }

  return (
    <div {...attributes} className="my-4">
      <div contentEditable={false} className="relative group">
        <div
          className={`relative transition-all rounded-lg overflow-hidden ${
            selected && focused ? 'ring-2 ring-primary-500 ring-offset-2' : ''
          }`}
        >
          <video
            src={url}
            controls
            className="w-full max-w-3xl mx-auto rounded-lg shadow-md"
          />

          {/* 删除按钮 */}
          {selected && focused && (
            <div className="absolute top-2 right-2">
              <button
                onClick={handleDelete}
                className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors shadow-lg"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
      {children}
    </div>
  )
}

export default VideoBlock

