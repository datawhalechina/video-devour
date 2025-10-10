/**
 * 分割线块组件
 */
function DividerBlock({ attributes, children }) {
  return (
    <div {...attributes} className="my-6">
      <div contentEditable={false}>
        <hr className="border-t-2 border-gray-300" />
      </div>
      {children}
    </div>
  )
}

export default DividerBlock

