import { useMemo } from 'react'

/**
 * 段落块组件
 */
function ParagraphBlock({ attributes, children, element }) {
  const style = useMemo(() => {
    const styles = {}
    
    if (element.align) {
      styles.textAlign = element.align
    }
    
    return styles
  }, [element.align])

  return (
    <p
      {...attributes}
      className="text-base text-gray-800 leading-relaxed my-2 min-h-[1.5rem]"
      style={style}
    >
      {children}
    </p>
  )
}

export default ParagraphBlock

