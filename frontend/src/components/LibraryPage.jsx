import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, BookOpen, Search, Loader2, FileText, Eye, Download, Zap, AlertCircle,
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
 * 个人文档库：以「单次视频处理」为单位的文章库，支持 BM25 相关度检索。
 * 响应式卡片展示；卡片点击进入文章子页（Markdown 渲染 + 图片 + 下载），
 * 另支持单篇 .md 下载与整库 ZIP 导出。
 */
function LibraryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState('all')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)
  const requestRef = useRef(0)

  const load = async (q, sc) => {
    const request = ++requestRef.current
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/library/search?q=${encodeURIComponent(q)}&scope=${sc}&top_k=30`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (request === requestRef.current) setResults(data)
    } catch (err) {
      if (request === requestRef.current) setError(err.message)
    } finally {
      if (request === requestRef.current) setLoading(false)
    }
  }

  useEffect(() => { load('', 'all'); return () => { clearTimeout(debounceRef.current); requestRef.current++ } }, [])

  const onQueryChange = (v) => {
    requestRef.current++
    setQuery(v)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(v, scope), 400)
  }

  const onScopeChange = (key) => {
    clearTimeout(debounceRef.current)
    setScope(key)
    load(query, key)
  }

  // 卡片点击 → 进入文章子页（Markdown 渲染 + 图片 + 下载）
  const openArticle = (r) => {
    navigate(`/library/article/${r.doc_id}/${r.scope}`)
  }

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
            onClick={() => window.open('/api/library/export', '_blank')}
            title="整库导出（全部任务的 md + 关键帧 + manifest.json）"
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
        {results && (
          <p className="library-stats">
            <Zap className="w-3.5 h-3.5" />
            {results.query
              ? `“${results.query}” 按相关度命中 ${results.total} 条`
              : `共收录 ${results.total} 篇文章（每个视频任务含图文大纲 / 精简报告 / 详细报告）`}
          </p>
        )}

        {/* 错误 / 空态 */}
        {error && (
          <div role="alert" className="history-empty">
            <AlertCircle className="history-empty-icon is-error" />
            <p className="is-error">加载失败：{error}</p>
            <button onClick={() => load(query, scope)} className="report-primary-button">重新加载</button>
          </div>
        )}
        {loading && !results && (
          <div className="history-empty">
            <Loader2 className="history-empty-icon animate-spin" />
            <p>加载中…</p>
          </div>
        )}
        {!error && !loading && results && results.results.length === 0 && (
          <div className="history-empty">
            <FileText className="history-empty-icon" />
            <p>{query ? `没有包含“${query}”的内容` : '还没有任何已生成的内容'}</p>
          </div>
        )}

        {/* 知识卡片 */}
        {results && results.results.length > 0 && (
          <div className="library-grid">
            {results.results.map((r, i) => (
              <motion.button
                type="button"
                key={`${r.doc_id}-${r.scope}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.4) }}
                className="library-card"
                onClick={() => openArticle(r)}
              >
                <div className="library-card-tags">
                  <span className="library-tag is-type">{r.label}</span>
                  <span className="library-tag">{r.platform_label}</span>
                  {r.query && r.score > 0 && (
                    <span className="library-tag is-score">相关度 {r.score}</span>
                  )}
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
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default LibraryPage
