import { useEffect } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Link2, Upload, BookOpen, History, Settings, ArrowUpRight, ChevronRight, Play, Plus } from 'lucide-react'

const navigation = [
  { to: '/', label: '工作台', icon: LayoutDashboard, end: true },
  { to: '/link', label: '在线视频', icon: Link2 },
  { to: '/upload', label: '本地上传', icon: Upload },
  { to: '/library', label: '知识库', icon: BookOpen },
  { to: '/history', label: '处理记录', icon: History },
]
const titles = { link: '在线视频', upload: '本地上传', library: '知识库', history: '处理记录', settings: '偏好设置', processing: '处理进度', report: '视频报告', editor: '文档编辑', 'editor-test': '编辑器' }

export default function AppShell({ children }) {
  const { pathname } = useLocation()
  const section = pathname.split('/')[1]
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">跳转到内容</a>
      <aside className="app-sidebar">
        <Link to="/" className="brand-lockup" aria-label="VideoDevour 工作台"><span className="brand-mark"><Play size={19} fill="currentColor" /></span><span>VideoDevour<span className="brand-caption">让视频成为你的知识</span></span></Link>
        <Link to="/link" className="sidebar-create"><Plus size={18} /> 新建解析 <span>+</span></Link>
        <div className="nav-caption">工作空间</div>
        <nav className="workspace-nav" aria-label="主导航">{navigation.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} aria-label={label} title={label} className={({ isActive }) => `nav-item ${isActive || (to === '/history' && ['report', 'processing', 'editor'].includes(section)) ? 'is-active' : ''}`}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><span className="note-line" /><p>少一点反复观看，<br />多一点真正理解。</p><span>WATCH. LEARN. KEEP.</span></div>
          <NavLink aria-label="偏好设置" title="偏好设置" to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'is-active' : ''}`}><Settings size={18} /><span>偏好设置</span></NavLink>
          <a className="nav-item" href="https://github.com/datawhalechina/video-devour" target="_blank" rel="noreferrer"><BookOpen size={18} /><span>项目文档</span><ArrowUpRight size={14} /></a>
          <div className="workspace-identity"><span>V</span><div>个人工作空间<small>VideoDevour · 自托管</small></div></div>
        </div>
      </aside>
      <div className={`app-body ${section.startsWith('editor') ? 'editor-workspace' : ''}`}>
        <header className="workspace-topbar"><div className="breadcrumbs"><span>我的工作空间</span><ChevronRight size={14} /><strong>{titles[section] || '工作台'}</strong></div><Link to="/library" className="topbar-library"><BookOpen size={15} /><span>我的知识库</span><ArrowUpRight size={14} /></Link></header>
        <div id="workspace-content" className="workspace-content" tabIndex={-1}>{children}</div>
      </div>
    </div>
  )
}
