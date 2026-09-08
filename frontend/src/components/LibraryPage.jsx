import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, BookOpen, Search, Loader2, FileText, Eye } from 'lucide-react'

const SCOPE_TABS = [
  { key: 'all', label: '全部' },
  { key: 'outline', label: '图文大纲' },
  { key: 'report', label: '精简报告' },
  { key: 'detailed', label: '详细报告' },
]

/**
 * 个人文档库：跨任务检索所有已生成的内容（图文大纲 / 精简报告 / 详细报告）。
 * 输入关键词全文检索，点击结果跳转到对应报告页查看。
 */
function LibraryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState('all')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const debounceRef = useRef(null)

  const load = async (q, sc) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/library/search?q=${encodeURIComponent(q)}&scope=${sc}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load('', 'all') }, [])

  const onQueryChange = (v) => {
    setQuery(v)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => load(v, scope), 400)   // 输入防抖
  }

  const onScopeChange = (key) => {
    setScope(key)
    load(query, key)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 max-w-6xl flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
            <ArrowLeft className="w-5 h-5" />
            <span>返回</span>
          </button>
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-primary-600" />
            <h1 className="text-lg font-bold text-gray-900">个人文档库</h1>
          </div>
          <div className="w-16" />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl space-y-5">
        {/* 搜索框 */}
        <div className="flex items-center gap-3">
          <div className="flex-1 flex items-center gap-2 px-4 py-3 bg-white rounded-xl border border-gray-200 focus-within:ring-2 focus-within:ring-primary-500">
            <Search className="w-5 h-5 text-gray-400" />
            <input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="跨任务检索已生成的全部内容，如：新教师、PO Token、3D 课件…"
              className="flex-1 outline-none text-sm bg-transparent"
            />
            {loading && <Loader2 className="w-4 h-4 animate-spin text-gray-400" />}
          </div>
        </div>

        {/* 范围过滤 */}
        <div className="flex items-center gap-2">
          {SCOPE_TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => onScopeChange(t.key)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
                scope === t.key ? 'bg-primary-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              {t.label}
            </button>
          ))}
          {results && (
            <span className="ml-auto text-xs text-gray-400">
              {results.query ? `“${results.query}” 命中 ${results.total} 条` : `共 ${results.total} 篇文档`}
            </span>
          )}
        </div>

        {/* 结果列表 */}
        {error ? (
          <div className="bg-white rounded-xl shadow p-10 text-center text-red-600">{error}</div>
        ) : loading && !results ? (
          <div className="bg-white rounded-xl shadow p-10 text-center">
            <Loader2 className="w-10 h-10 text-primary-500 mx-auto mb-3 animate-spin" />
            <p className="text-gray-500 text-sm">加载中…</p>
          </div>
        ) : results && results.results.length === 0 ? (
          <div className="bg-white rounded-xl shadow p-10 text-center">
            <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">{query ? `没有包含“${query}”的内容` : '还没有任何已生成的内容'}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {results?.results.map((r, i) => (
              <motion.div
                key={`${r.task_id}-${r.scope}-${i}`}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.3) }}
                className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium">{r.label}</span>
                      <span className="text-sm font-semibold text-gray-800 truncate">{r.title}</span>
                    </div>
                    <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{r.snippet}</p>
                    <p className="text-xs text-gray-400 mt-1.5">{new Date(r.created_at).toLocaleString('zh-CN')}</p>
                  </div>
                  <a
                    href={r.view_url}
                    className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    查看
                  </a>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default LibraryPage
