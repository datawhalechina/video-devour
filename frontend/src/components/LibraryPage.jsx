import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { triggerDownload } from '../utils/helpers'
import {
  ArrowLeft, BookOpen, Search, Loader2, FileText, Eye, Download, Zap, AlertCircle, Layers,
} from 'lucide-react'

const SCOPE_TABS = [
  { key: 'all', label: '全部' },
  { key: 'outline', label: '图文大纲' },
  { key: 'report', label: '精简报告' },
  { key: 'detailed', label: '详细报告' },
]

const cleanSnippet = (value = '') => value
  .replace(/!\[[^\]]*\]\([^)]*(?:\)|$)/g, '')
  .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
  .replace(/(^|\s)#{1,6}\s/g, '$1')
  .replace(/\*\*|__|`/g, '')
  .replace(/\s+/g, ' ')
  .trim()

/**
 * 个人文档库：以「视频」为存储单位的文章库。
 * 同一视频的多次处理形成 V1/V2… 版本链，卡片内选择版本后打开具体文章；
 * 关键词搜索走 BM25（按文章命中，附版本标记）。支持整库 ZIP 导出。
 */
function LibraryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState('all')
  const [videos, setVideos] = useState(null)      // 浏览模式：按视频聚合
  const [hits, setHits] = useState(null)          // 搜索模式：按文章命中
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)
  const requestRef = useRef(0)

  const loadVideos = async () => {
    const request = ++requestRef.current
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/library/videos')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (request === requestRef.current) setVideos(data)
    } catch (err) {
      if (request === requestRef.current) setError(err.message)
    } finally {
      if (request === requestRef.current) setLoading(false)
    }
  }

  const loadSearch = async (q, sc) => {
    const request = ++requestRef.current
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/library/search?q=${encodeURIComponent(q)}&scope=${sc}&top_k=30`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (request === requestRef.current) setHits(data)
    } catch (err) {
      if (request === requestRef.current) setError(err.message)
    } finally {
      if (request === requestRef.current) setLoading(false)
    }
  }

  useEffect(() => {
    loadVideos()
    return () => { clearTimeout(debounceRef.current); requestRef.current++ }
  }, [])

  const onQueryChange = (v) => {
    requestRef.current++
    setQuery(v)
    clearTimeout(debounceRef.current)
    if (!v.trim()) {
      setHits(null)
      loadVideos()
      return
    }
    debounceRef.current = setTimeout(() => loadSearch(v, scope), 400)
  }

  const onScopeChange = (key) => {
    clearTimeout(debounceRef.current)
    setScope(key)
    if (query.trim()) loadSearch(query, key)
  }

  // 打开具体内容 → 视频学习页（二级页面，内含版本与文章切换）
  const openVideo = (videoKey, runId, sc) => {
    const params = new URLSearchParams()
    if (runId) params.set('run', runId)
    if (sc) params.set('scope', sc)
    const q = params.toString()
    navigate(`/library/video/${encodeURIComponent(videoKey)}${q ? `?${q}` : ''}`)
  }

  // 首页每个视频一张卡片，点进去是该视频的学习页（二级页面）
  const renderVideoCard = (video, i) => (
    <motion.button
      type="button"
      key={video.video_key}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(i * 0.03, 0.4) }}
      className="library-card"
      onClick={() => openVideo(video.video_key, video.latest_doc_id && video.versions[0]?.run_id, scope === 'all' ? '' : scope)}
    >
      <div className="library-card-tags">
        <span className="library-tag">{video.platform_label}</span>
        <span className="library-tag is-type">
          <Layers className="w-3 h-3 inline -mt-0.5 mr-0.5" />
          {video.version_count > 1 ? `${video.version_count} 个版本` : '1 个版本'}
        </span>
        <span className="library-tag is-version">{video.versions[0]?.version_label}</span>
      </div>
      <h3 className="line-clamp-2">{video.title}</h3>
      <p className="line-clamp-3">{cleanSnippet(video.snippet)}</p>
      <div className="library-card-foot">
        <span>{new Date(video.created_at).toLocaleString('zh-CN')}</span>
        <span className="library-card-open">
          <Eye className="w-3.5 h-3.5" /> 进入学习
        </span>
      </div>
    </motion.button>
  )

  const renderHitCard = (r, i) => (
    <motion.button
      type="button"
      key={`${r.doc_id}-${r.scope}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(i * 0.03, 0.4) }}
      className="library-card"
      onClick={() => openVideo(r.video_key, r.run_id, r.scope)}
    >
      <div className="library-card-tags">
        <span className="library-tag is-type">{r.label}</span>
        <span className="library-tag">{r.platform_label}</span>
        {r.version_label && <span className="library-tag is-version">{r.version_label}</span>}
        {r.query && r.score > 0 && <span className="library-tag is-score">相关度 {r.score}</span>}
      </div>
      <h3 className="line-clamp-2">{r.title}</h3>
      <p className="line-clamp-4">{cleanSnippet(r.snippet)}</p>
      <div className="library-card-foot">
        <span>{new Date(r.created_at).toLocaleString('zh-CN')}</span>
        <span className="library-card-open">
          <Eye className="w-3.5 h-3.5" /> 阅读全文
        </span>
      </div>
    </motion.button>
  )

  const searching = !!query.trim()
  const items = searching ? (hits?.results || []) : (videos?.results || [])
  const total = searching ? (hits?.total || 0) : (videos?.total || 0)

  return (
    <div className="workspace-page librarypage">
      <header className="page-toolbar">
        <div className="container mx-auto px-4 py-4 max-w-7xl flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
            <ArrowLeft className="w-5 h-5" />
            <span>返回</span>
          </button>
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-primary-600" />
            <h1 className="text-lg font-bold text-gray-900">个人文档库</h1>
          </div>
          <button
            onClick={() => triggerDownload('/api/library/export')}
            title="整库导出（按视频/版本组织的 md + 关键帧 + manifest.json）"
            className="report-tool-button"
          >
            <Download className="w-3.5 h-3.5" />
            整库导出 ZIP
          </button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-7xl">
        <div className="page-intro"><div className="eyebrow">YOUR KNOWLEDGE, CONNECTED</div><h1>每次学习，都有迹可循。</h1><p>在这里重读、检索和导出你的视频笔记。</p></div>
        {/* 搜索区 */}
        <div className="library-search flex flex-wrap items-center gap-3 mb-4">
          <div className="library-search-field">
            <Search className="w-5 h-5 text-gray-400" />
            <input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              aria-label="搜索知识库"
              placeholder="搜索标题、关键词或你记得的某个观点…"
              className="flex-1 outline-none text-sm bg-transparent"
            />
            {loading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
          </div>
          <div className="library-filters">
            {SCOPE_TABS.map((t) => (
              <button
                key={t.key}
                aria-pressed={scope === t.key}
                onClick={() => onScopeChange(t.key)}
                className={`library-filter ${scope === t.key ? 'is-active' : ''}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* 统计行 */}
        {(videos || hits) && !error && (
          <p className="library-stats">
            <Zap className="w-3.5 h-3.5" />
            {searching
              ? `“${query}” 按相关度命中 ${total} 条`
              : `共收录 ${total} 个视频（同视频多次处理自动存为 V1/V2…）`}
          </p>
        )}

        {/* 错误 / 空态 */}
        {error && (
          <div role="alert" className="history-empty">
            <AlertCircle className="history-empty-icon is-error" />
            <p className="is-error">加载失败：{error}</p>
            <button onClick={() => (searching ? loadSearch(query, scope) : loadVideos())} className="report-primary-button">重新加载</button>
          </div>
        )}
        {loading && !videos && !hits && (
          <div className="history-empty">
            <Loader2 className="history-empty-icon animate-spin" />
            <p>加载中…</p>
          </div>
        )}
        {!error && !loading && items.length === 0 && (
          <div className="history-empty">
            <FileText className="history-empty-icon" />
            <p>{searching ? `没有包含“${query}”的内容` : '还没有任何已生成的内容'}</p>
          </div>
        )}

        {/* 知识卡片：浏览=按视频（含版本），搜索=按文章命中 */}
        {!error && items.length > 0 && (
          <div className="library-grid">
            {searching
              ? items.map((r, i) => renderHitCard(r, i))
              : items.map((v, i) => renderVideoCard(v, i))}
          </div>
        )}
      </main>
    </div>
  )
}

export default LibraryPage
