import { useMemo } from 'react'

/**
 * 标题块组件
 */
function HeadingBlock({ attributes, children, element }) {
  const { type, align } = element

  const style = useMemo(() => {
    const styles = {}
    
    if (align) {
      styles.textAlign = align
    }
    
    return styles
  }, [align])

  const className = useMemo(() => {
    const baseClass = 'font-bold text-gray-900 my-3'
    
    switch (type) {
      case 'heading-one':
        return `${baseClass} text-4xl leading-tight`
      case 'heading-two':
        return `${baseClass} text-3xl leading-tight`
      case 'heading-three':
        return `${baseClass} text-2xl leading-snug`
      default:
        return baseClass
    }
  }, [type])

  const Tag = useMemo(() => {
    switch (type) {
      case 'heading-one':
        return 'h1'
      case 'heading-two':
        return 'h2'
      case 'heading-three':
        return 'h3'
      default:
        return 'h2'
    }
  }, [type])

  return (
    <Tag {...attributes} className={className} style={style}>
      {children}
    </Tag>
  )
}

export default HeadingBlock

