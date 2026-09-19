import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function BackLink({ to, onClick, parent, current }) {
  const content = <><ChevronLeft size={15} /><span>{parent}</span></>
  return <nav className="workspace-breadcrumb" aria-label="页面路径">
    {to ? <Link to={to}>{content}</Link> : <button type="button" onClick={onClick}>{content}</button>}
    <ChevronRight size={12} aria-hidden="true" /><span aria-current="page">{current}</span>
  </nav>
}
