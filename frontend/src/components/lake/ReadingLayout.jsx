import { useEffect, useId, useRef, useState } from 'react'
import { List } from 'lucide-react'

export default function ReadingLayout({ children, contentKey }) {
  const bodyRef = useRef(null)
  const prefix = useId()
  const [headings, setHeadings] = useState([])
  const [active, setActive] = useState('')
  useEffect(() => {
    const nodes = [...(bodyRef.current?.querySelectorAll('h2, h3') || [])]
    const chapters = nodes.map((node, index) => {
      node.id = `${prefix}-chapter-${index}`
      node.tabIndex = -1
      return { id: node.id, label: node.textContent, level: node.tagName }
    })
    setHeadings(chapters); setActive(chapters[0]?.id || '')
    const container = bodyRef.current
    container?.scrollTo(0,0)
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => a.boundingClientRect.top-b.boundingClientRect.top)
      if (visible[0]) setActive(visible[0].target.id)
    }, { root: container, rootMargin: '0px 0px -65% 0px' })
    nodes.forEach(node => observer.observe(node))
    return () => observer.disconnect()
  }, [contentKey, prefix])
  const jump = id => {
    const target = document.getElementById(id)
    target?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' })
    target?.focus({ preventScroll: true }); setActive(id)
  }
  return <div className={`lake-reading-layout ${headings.length ? '' : 'without-chapters'}`}>
    {headings.length > 0 && <aside className="lake-toc"><div><List size={17} /><h2>章节目录</h2></div><nav aria-label="章节目录">{headings.map((item, index) => <button className={item.level === 'H3' ? 'is-subchapter' : ''} key={item.id} aria-current={active === item.id ? 'location' : undefined} onClick={() => jump(item.id)}><span>{String(index + 1).padStart(2, '0')}</span>{item.label}</button>)}</nav></aside>}
    <div ref={bodyRef} className="lake-reading-body" tabIndex={0} role="region" aria-label="报告正文">{children}</div>
  </div>
}
