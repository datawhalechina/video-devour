/**
 * 渲染编辑器叶子节点（行内样式）
 */
function EditorLeaf({ attributes, children, leaf }) {
  let styledChildren = children

  // 粗体
  if (leaf.bold) {
    styledChildren = <strong className="font-bold">{styledChildren}</strong>
  }

  // 斜体
  if (leaf.italic) {
    styledChildren = <em className="italic">{styledChildren}</em>
  }

  // 下划线
  if (leaf.underline) {
    styledChildren = <u className="underline">{styledChildren}</u>
  }

  // 删除线
  if (leaf.strikethrough) {
    styledChildren = <s className="line-through">{styledChildren}</s>
  }

  // 行内代码
  if (leaf.code) {
    styledChildren = (
      <code className="px-1.5 py-0.5 bg-gray-100 text-red-600 rounded text-sm font-mono">
        {styledChildren}
      </code>
    )
  }

  // 高亮
  if (leaf.highlight) {
    styledChildren = (
      <mark 
        className="bg-yellow-200 px-0.5 rounded"
        style={leaf.highlightColor ? { backgroundColor: leaf.highlightColor } : undefined}
      >
        {styledChildren}
      </mark>
    )
  }

  // 文字颜色
  if (leaf.color) {
    styledChildren = (
      <span style={{ color: leaf.color }}>
        {styledChildren}
      </span>
    )
  }

  // 背景颜色
  if (leaf.backgroundColor) {
    styledChildren = (
      <span style={{ backgroundColor: leaf.backgroundColor }}>
        {styledChildren}
      </span>
    )
  }

  return <span {...attributes}>{styledChildren}</span>
}

export default EditorLeaf

