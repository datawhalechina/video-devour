import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Download, FileDown, FileText, Loader2, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { mermaidMarkdownComponents } from './MermaidBlock'

const SCOPE_ORDER = ['outline', 'report', 'detailed', 'quantum', 'wechat', 'xiaohongshu']
const SCOPE_META = {
  outline: { label: '图文大纲', hint: '沿核心观点快速回顾' },
  report: { label: '精简报告', hint: '提炼重点，快速阅读' },
  detailed: { label: '详细报告', hint: '原文与笔记对照精读' },
  quantum: { label: '量子速读', hint: '30 秒抓住大意，附可发朋友圈的句子' },
  wechat: { label: '公众号文章', hint: '图文成稿，可直接发布' },
  xiaohongshu: { label: '小红书笔记', hint: '图文笔记，含话题标签' },
}
// 这些文体不随处理流程预生成，点开时才按需生成（结果缓存复用）
const GENERATABLE = ['quantum', 'wechat', 'xiaohongshu']

/**
 * 视频学习页（二级页面）：同一个视频的多次处理都在这里切换。
 * 顶部切换版本（V1/V2…），再切换文章类型（图文大纲 / 精简报告 / 详细报告），
 * 正文就地渲染，省去在首页铺开所有版本与文章。
 * 路由：/library/video/:videoKey?run=<run_id>&scope=<scope>
 */
function LibraryVideoPage() {
  const { videoKey } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const [video, setVideo] = useState(null)
  const [article, setArticle] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  // 按 scope 独立追踪生成状态（scope -> true）。
  // 不能共用一个字符串：那会互相阻塞，导致三个文体只能逐个生成。
  const [generating, setGenerating] = useState({})
  const [runId, setRunId] = useState(searchParams.get('run') || '')
  const [scope, setScope] = useState(searchParams.get('scope') || '')
  // 已尝试过按需生成的文体（每个版本各一次），避免异常时反复触发生成
  const attempted = useRef(new Set())
  // 在途生成请求（scope -> Promise）：并行触发时复用，避免重复请求
  const inFlight = useRef(new Map())

  // 生成单个文体（仅落盘，不负责展示）；同一 scope 的并发调用复用同一请求
  const generateScope = (run, sc) => {
    if (inFlight.current.has(sc)) return inFlight.current.get(sc)
    attempted.current.add(sc)
    setGenerating((prev) => ({ ...prev, [sc]: true }))
    const task = (async () => {
      const body = new FormData()
      if (run.run_id) body.append('run_id', run.run_id)
      const gen = await fetch(
        `/api/library/article/${run.doc_id}/${sc}/generate`,
        { method: 'POST', body })
      if (!gen.ok) {
        const d = await gen.json().catch(() => ({}))
        throw new Error(d.detail || `生成失败 HTTP ${gen.status}`)
      }
    })().finally(() => {
      inFlight.current.delete(sc)
      setGenerating((prev) => { const next = { ...prev }; delete next[sc]; return next })
    })
    inFlight.current.set(sc, task)
    return task
  }

  // 三个衍生文体并行发起：只等当前选中的那个，其余在后台继续生成，
  // 用户切过去时通常已就绪（服务端按 scope 缓存，重复调用直接命中文件）。
  const generateAllStyles = (run, current) => {
    GENERATABLE.filter((sc) => !attempted.current.has(sc)).forEach((sc) => {
      generateScope(run, sc)
    })
    return generateScope(run, current)
  }

  // 读取某版本的某篇文章；不存在返回 null（不抛错，便于「先读、没有再生成」）
  const readArticle = async (run, sc) => {
    try {
      const q = run.run_id ? `?run_id=${encodeURIComponent(run.run_id)}` : ''
      const res = await fetch(`/api/library/article/${run.doc_id}/${sc}${q}`)
      if (!res.ok) return null
      const body = await res.json()
      return typeof body.content === 'string' && body.content ? body : null
    } catch {
      return null
    }
  }

  const loadVideo = async () => {
    const res = await fetch(`/api/library/video/${encodeURIComponent(videoKey)}`)
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d.detail || `HTTP ${res.status}`)
    }
    const data = await res.json()
    setVideo(data)
    return data
  }

  // 视频详情：全部版本与各版本文章清单
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    ;(async () => {
      try {
        const res = await fetch(`/api/library/video/${encodeURIComponent(videoKey)}`)
        if (!res.ok) {
          const d = await res.json().catch(() => ({}))
          throw new Error(d.detail || `HTTP ${res.status}`)
        }
        const data = await res.json()
        if (!cancelled) setVideo(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    })()
    return () => { cancelled = true }
  }, [videoKey])

  // 当前版本：默认最新（后端已按最新在前排序）
  const activeRun = useMemo(() => {
    if (!video?.versions?.length) return null
    return video.versions.find((v) => v.run_id === runId) || video.versions[0]
  }, [video, runId])

  const scopeReady = (sc) => !!activeRun?.articles?.some((a) => a.scope === sc)

  // 当前文章类型：默认优先「详细报告」。
  // 衍生文体需要先生成，不作为默认项。
  const activeScope = useMemo(() => {
    const ready = SCOPE_ORDER.filter((s) => activeRun?.articles?.some((a) => a.scope === s))
    if (scope && (ready.includes(scope) || GENERATABLE.includes(scope))) return scope
    return ready.includes('detailed') ? 'detailed' : (ready[0] || '')
  }, [activeRun, scope])

  // 正文：衍生文体尚未生成时先按需生成（生成结果会落盘复用）
  useEffect(() => {
    if (!activeRun || !activeScope) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    ;(async () => {
      try {
        // 先直接按当前版本读取：服务端已持久化就直接用，避免把已生成的内容再生成一遍。
        let data = await readArticle(activeRun, activeScope)
        if (!data && GENERATABLE.includes(activeScope)) {
          // 三个衍生文体并行生成，只等当前选中的这个（其余后台继续）
          await generateAllStyles(activeRun, activeScope)
          if (!cancelled) await loadVideo()   // 刷新文章清单，让新文体出现
          data = await readArticle(activeRun, activeScope)
        }
        if (cancelled) return
        if (!data) throw new Error('内容不存在')
        setArticle(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [activeRun, activeScope])

  // 选择版本：已经是当前版本时不处理（否则清空正文却不会重新拉取，会卡在“正在载入”）
  const pickVersion = (run) => {
    if (run.run_id === activeRun?.run_id) return
    setRunId(run.run_id)
    setScope('')
    setArticle(null)
  }
  // 选择内容类型：同上，点击已选中的类型不做无谓清空
  const pickScope = (next) => {
    if (next === activeScope) return
    setScope(next)
    setArticle(null)
  }

  // Markdown 相对路径图片 → 任务输出目录（react-markdown 已做过 URL 编码，勿再编码）
  const imgOverride = (outputDir) => ({ src, alt, ...props }) => {
    let imageSrc = src
    if (src && !src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/')) {
      imageSrc = `/static/${outputDir ? outputDir + '/' : ''}${src}`
    }
    return <img src={imageSrc} alt={alt} {...props} className="max-w-full h-auto rounded-lg shadow-sm my-4" loading="lazy" />
  }

  const currentQuery = activeRun && activeScope
    ? `/api/library/article/${activeRun.doc_id}/${activeScope}/download`
      + (activeRun.run_id ? `?run_id=${encodeURIComponent(activeRun.run_id)}` : '')
    : ''
  const downloadHref = currentQuery ? `${currentQuery}${currentQuery.includes('?') ? '&' : '?'}fmt=md` : ''
  const pdfHref = currentQuery ? `${currentQuery}${currentQuery.includes('?') ? '&' : '?'}fmt=pdf` : ''

  return (
    <div className="workspace-page libraryvideopage">
      <header className="page-toolbar">
        <div className="container mx-auto px-4 py-4 max-w-6xl flex items-center justify-between">
          <button
            onClick={() => navigate('/library')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回文档库</span>
          </button>
          <div className="flex items-center gap-2">
            {currentQuery && (
              <>
                <a href={downloadHref} download="" className="report-tool-button">
                  <Download className="w-3.5 h-3.5" />
                  下载 .md
                </a>
                <a href={pdfHref} download="" className="report-tool-button">
                  <FileDown className="w-3.5 h-3.5" />
                  下载 PDF
                </a>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-6xl">
        {error && !video ? (
          <div className="history-empty">
            <p className="is-error">加载失败：{error}</p>
            <button onClick={() => navigate('/library')} className="report-primary-button">返回文档库</button>
          </div>
        ) : !video ? (
          <div className="history-empty">
            <Loader2 className="history-empty-icon animate-spin" />
            <p>加载中…</p>
          </div>
        ) : (
          <>
            {/* 视频信息 */}
            <div className="video-hero">
              <div className="library-card-tags">
                <span className="library-tag is-type">{video.platform_label}</span>
                {video.version_count > 1 && (
                  <span className="library-tag">{video.version_count} 个版本</span>
                )}
              </div>
              <h1>{video.title}</h1>
              <div className="video-hero-meta">
                <Clock className="w-3.5 h-3.5" />
                {activeRun && <span>{activeRun.version_label} · {new Date(activeRun.created_at).toLocaleString('zh-CN')}</span>}
                {video.source_url && (
                  <a href={video.source_url} target="_blank" rel="noreferrer" className="truncate max-w-[380px] hover:text-primary-600">
                    {video.source_url}
                  </a>
                )}
              </div>
            </div>

            {/* 版本切换：同一视频的多次处理 */}
            {video.version_count > 1 && (
              <div className="video-picker">
                <span className="video-picker-label">版本</span>
                <div className="library-version-row">
                  {video.versions.map((v) => (
                    <button
                      key={v.run_id || v.doc_id}
                      type="button"
                      aria-pressed={v.run_id === activeRun?.run_id}
                      className={`library-version-chip ${v.run_id === activeRun?.run_id ? 'is-active' : ''}`}
                      onClick={() => pickVersion(v)}
                      title={`${new Date(v.created_at).toLocaleString('zh-CN')} · ${v.education_level}`}
                    >
                      {v.version_label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 文章类型切换：已生成的直接读；衍生文体未生成时可点击生成 */}
            <div className="video-picker">
              <span className="video-picker-label">内容</span>
              <div className="library-article-links">
                {SCOPE_ORDER.map((sc) => {
                  const ready = scopeReady(sc)
                  const meta = SCOPE_META[sc] || { label: sc }
                  const isGenerating = !!generating[sc]
                  return (
                    <button
                      key={sc}
                      type="button"
                      aria-pressed={sc === activeScope}
                      disabled={isGenerating}
                      className={`library-article-link ${sc === activeScope ? 'is-active' : ''} ${ready ? '' : 'is-pending'}`}
                      onClick={() => pickScope(sc)}
                      title={ready ? '' : '点击生成'}
                    >
                      {isGenerating
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <FileText className="w-3.5 h-3.5" />}
                      {meta.label}
                      {!ready && !isGenerating && <span className="library-link-plus">生成</span>}
                    </button>
                  )
                })}
              </div>
              {activeScope && SCOPE_META[activeScope] && (
                <span className="video-picker-hint">
                  {generating[activeScope] ? '正在生成，请稍候…' : SCOPE_META[activeScope].hint}
                </span>
              )}
            </div>

            {/* 正文阅读区 */}
            {error && (
              <div className="history-empty">
                <p className="is-error">加载失败：{error}</p>
              </div>
            )}
            {!error && (!article || loading) && (
              <div className="history-empty">
                <Loader2 className="history-empty-icon animate-spin" />
                <p>正在载入内容…</p>
              </div>
            )}
            {!error && article && !loading && (
              <motion.article
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="reading-pane"
              >
                <div className="article-meta">
                  <span className="library-tag is-type">{article.label}</span>
                  {article.version_label && (
                    <span className="library-tag is-version">
                      {article.version_label}{article.version_count > 1 ? ` / 共 ${article.version_count} 版` : ''}
                    </span>
                  )}
                  {activeRun?.education_level && <span className="library-tag">{activeRun.education_level}</span>}
                </div>
                <div className="prose prose-lg max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      ...mermaidMarkdownComponents,
                      img: imgOverride(article.output_dir),
                    }}
                  >
                    {article.content}
                  </ReactMarkdown>
                </div>
              </motion.article>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default LibraryVideoPage
