import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, Link2, Upload, FileText, BookOpen, Layers, Search, Sparkles, Play, RefreshCw } from 'lucide-react'

export default function LandingPage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [reload, setReload] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    fetch('/api/library/search?q=&scope=outline&top_k=4', { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error('加载失败'); return response.json() })
      .then(data => setDocuments((data.results || []).slice(0, 4)))
      .catch(err => { if (err.name !== 'AbortError') setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [reload])
  const start = event => { event.preventDefault(); if (url.trim()) navigate('/link', { state: { url: url.trim() } }) }
  return (
    <main className="dashboard">
      <div className="dashboard-heading"><div><div className="eyebrow">YOUR LEARNING STUDIO</div><h1>把看过的，变成自己的。</h1><p>从一段视频开始，积累值得留下的知识。</p></div><span className="workspace-tag"><span />个人知识工作台</span></div>
      <section className="studio-hero">
        <div className="hero-copy"><span className="hero-kicker"><Sparkles size={14} /> 视频里的好内容，值得留下</span><h2>长视频，短时间理解。<br /><span>让知识有迹可循。</span></h2><p>提取关键观点、整理图文笔记，把零散的信息<br className="desktop-break" />变成可阅读、可编辑、可回顾的知识。</p><a href="#new-import" className="hero-cta">开始整理视频 <ArrowRight size={17} /></a><div className="hero-footnote">视频转文字 <span>／</span> 智能大纲 <span>／</span> 图文报告</div></div>
        <div className="hero-art" aria-label="视频转化为结构化笔记的示意图"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="video-illustration"><div className="illustration-label"><span /> VIDEO SOURCE <span>01</span></div><div className="illustration-play"><Play size={25} fill="currentColor" /></div><div className="video-timeline"><i /><span>08:24</span></div></div><div className="note-illustration"><div className="note-illustration-top"><span><FileText size={15} /> 知识笔记</span><span>示例</span></div><h3>从信息，到理解</h3><div className="note-text-line" /><div className="note-text-line short" /><div className="illustration-quote">抓住核心观点，<br />建立自己的知识脉络。</div><div className="note-check"><span>✓</span> 关键观点已整理</div></div><span className="art-spark"><Sparkles size={20} /></span></div>
      </section>
      <section id="new-import" className="import-section"><div className="section-heading"><h2>开始一次新的探索</h2><span>选择你的视频来源</span></div><div className="import-grid"><form className="link-import" onSubmit={start}><div className="import-title"><span className="icon-tile"><Link2 size={19} /></span><div><h3>粘贴视频链接</h3><p>B站、YouTube、微信视频号</p></div></div><label htmlFor="dashboard-url" className="sr-only">视频链接或分享文案</label><div className="quick-url"><input id="dashboard-url" value={url} onChange={event => setUrl(event.target.value)} placeholder="粘贴视频链接或分享文案…" /><button type="submit" disabled={!url.trim()}>开始解析 <ArrowRight size={15} /></button></div></form><Link to="/upload" className="upload-import"><span className="icon-tile"><Upload size={21} /></span><h3>上传本地视频</h3><p>把课程、会议或灵感带进来</p><span className="upload-types">MP4 · MOV · MKV · AVI</span><ArrowUpRight className="upload-arrow" size={20} /></Link></div></section>
      <section className="recent-section"><div className="section-heading"><h2>最近的知识笔记 <span className="section-label">继续你的学习</span></h2><Link to="/library">查看知识库 <ArrowRight size={15} /></Link></div><div className="recent-documents" aria-live="polite">{loading ? Array.from({ length: 3 }, (_, i) => <div className="document-skeleton" key={i}><span /><div><i /><i /></div></div>) : error ? <div className="dashboard-empty"><BookOpen size={24} /><div><h3>暂时无法加载知识笔记</h3><p>请检查服务连接，或稍后重试。</p></div><button className="subtle-button" onClick={() => setReload(value => value + 1)}><RefreshCw size={15} /> 重试</button></div> : documents.length ? documents.map((doc, index) => <Link className="document-row" to={`/library/article/${doc.doc_id}/${doc.scope}`} key={`${doc.doc_id}-${doc.scope}`}><span className="document-number">{String(index + 1).padStart(2, '0')}</span><span className="document-icon"><FileText size={20} /></span><div className="document-info"><h3>{doc.title}</h3><p>{doc.platform_label || '视频笔记'}<span>·</span>{doc.label || '图文大纲'}</p></div><time>{doc.created_at ? new Date(doc.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : ''}</time><ArrowUpRight size={17} /></Link>) : <div className="dashboard-empty"><BookOpen size={26} /><div><h3>你的知识库，从第一段视频开始</h3><p>解析视频后，生成的笔记会出现在这里。</p></div><Link to="/link" className="subtle-button">添加视频 <ArrowRight size={15} /></Link></div>}</div></section>
      <div className="studio-footer"><span>把时间留给思考。</span><div><Layers size={14} /> 结构化整理 <span>·</span><Search size={14} /> 随时检索 <span>·</span><FileText size={14} /> 自由编辑</div></div>
    </main>
  )
}
