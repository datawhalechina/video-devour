import { useState, useRef, useEffect } from 'react'
import { useSlate, useSelected, useFocused } from 'slate-react'
import { Transforms } from 'slate'
import { Image as ImageIcon, Trash2, ZoomIn, X } from 'lucide-react'

/**
 * 图片查看器组件 - 支持放大、缩小、拖动
 */
function ImageViewer({ url, alt, onClose }) {
  const [scale, setScale] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const viewerRef = useRef(null)
  const rafRef = useRef(null)

  // 放大
  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.5, 4))
  }

  // 缩小
  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.5, 0.5))
  }

  // 重置
  const handleReset = () => {
    setScale(1)
    setPosition({ x: 0, y: 0 })
  }

  // 鼠标按下开始拖动
  const handleMouseDown = (e) => {
    if (e.target.tagName === 'IMG') {
      e.preventDefault()
      setIsDragging(true)
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      })
    }
  }

  // 鼠标移动拖动图片 - 使用 requestAnimationFrame 优化性能
  const handleMouseMove = (e) => {
    if (isDragging) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
      }
      
      rafRef.current = requestAnimationFrame(() => {
        setPosition({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y
        })
      })
    }
  }

  // 鼠标抬起停止拖动
  const handleMouseUp = () => {
    setIsDragging(false)
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
    }
  }

  // 滚轮缩放 - 优化缩放速度和流畅度
  const handleWheel = (e) => {
    e.preventDefault()
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
    }
    
    rafRef.current = requestAnimationFrame(() => {
      const delta = e.deltaY > 0 ? -0.15 : 0.15
      setScale(prev => Math.max(0.5, Math.min(4, prev + delta)))
    })
  }

  // ESC 键关闭
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      ref={viewerRef}
      className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center"
      onClick={(e) => e.target === viewerRef.current && onClose()}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* 顶部工具栏 */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white bg-opacity-20 backdrop-blur-md rounded-full px-6 py-3 flex items-center space-x-4">
        <button
          onClick={handleZoomOut}
          className="text-white hover:text-gray-300 transition-colors text-2xl font-bold"
          title="缩小 (滚轮向下)"
        >
          −
        </button>
        <span className="text-white font-medium min-w-[80px] text-center">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={handleZoomIn}
          className="text-white hover:text-gray-300 transition-colors text-2xl font-bold"
          title="放大 (滚轮向上)"
        >
          +
        </button>
        <div className="w-px h-6 bg-white bg-opacity-30"></div>
        <button
          onClick={handleReset}
          className="text-white hover:text-gray-300 transition-colors text-sm"
          title="重置"
        >
          重置
        </button>
      </div>

      {/* 关闭按钮 */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-3 bg-white bg-opacity-20 backdrop-blur-md rounded-full hover:bg-opacity-30 transition-all"
        title="关闭 (ESC)"
      >
        <X className="w-6 h-6 text-white" />
      </button>

      {/* 图片 */}
      <img
        src={url}
        alt={alt}
        className="max-w-none max-h-none object-contain select-none"
        style={{
          transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          cursor: isDragging ? 'grabbing' : 'grab',
          transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          willChange: 'transform'
        }}
        onMouseDown={handleMouseDown}
        onWheel={handleWheel}
        draggable={false}
      />

      {/* 提示文字 */}
      {alt && (
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-60 text-white px-4 py-2 rounded-lg max-w-2xl text-center">
          {alt}
        </div>
      )}
    </div>
  )
}

/**
 * 图片块组件
 */
function ImageBlock({ attributes, children, element }) {
  const editor = useSlate()
  const selected = useSelected()
  const focused = useFocused()
  const { url, alt = '', width } = element
  const [imageLoaded, setImageLoaded] = useState(false)
  const [showViewer, setShowViewer] = useState(false)

  const handleDelete = () => {
    const path = editor.selection ? editor.selection.anchor.path.slice(0, -1) : []
    Transforms.removeNodes(editor, { at: path })
  }

  return (
    <div {...attributes} className="my-6">
      <div contentEditable={false} className="relative group">
        {/* 居中容器 */}
        <div className="flex justify-center">
          <div
            className={`relative transition-all ${
              selected && focused ? 'ring-2 ring-blue-500 ring-offset-2' : ''
            }`}
            style={{ maxWidth: width || '800px', width: '100%' }}
          >
            {!imageLoaded && (
              <div className="flex items-center justify-center bg-gray-100 rounded-2xl h-64">
                <ImageIcon className="w-12 h-12 text-gray-400" />
              </div>
            )}
            
            {/* 图片 - 圆角 */}
            <div className="relative">
              <img
                src={url}
                alt={alt}
                onLoad={() => setImageLoaded(true)}
                onClick={() => setShowViewer(true)}
                className={`rounded-2xl shadow-lg max-w-full h-auto cursor-pointer transition-all hover:shadow-2xl ${
                  imageLoaded ? 'block' : 'hidden'
                }`}
              />
              
              {/* 放大图标提示 */}
              {imageLoaded && (
                <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black bg-opacity-30 rounded-2xl cursor-pointer"
                     onClick={() => setShowViewer(true)}>
                  <div className="bg-white bg-opacity-90 rounded-full p-3">
                    <ZoomIn className="w-8 h-8 text-gray-700" />
                  </div>
                </div>
              )}
            </div>

            {/* 操作按钮 */}
            {selected && focused && (
              <div className="absolute top-3 right-3 flex space-x-2">
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

        {/* 图片说明 */}
        {alt && (
          <p className="text-center text-sm text-gray-500 mt-3 italic">{alt}</p>
        )}
      </div>
      {children}

      {/* 图片查看器 */}
      {showViewer && (
        <ImageViewer
          url={url}
          alt={alt}
          onClose={() => setShowViewer(false)}
        />
      )}
    </div>
  )
}

export default ImageBlock

