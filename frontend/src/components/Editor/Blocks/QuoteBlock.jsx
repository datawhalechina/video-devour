/**
 * 引用块组件
 */
function QuoteBlock({ attributes, children }) {
  return (
    <blockquote
      {...attributes}
      className="border-l-4 border-gray-300 pl-4 py-2 my-4 text-gray-700 italic bg-gray-50 rounded-r"
    >
      {children}
    </blockquote>
  )
}

export default QuoteBlock

