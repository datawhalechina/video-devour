import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Download, FileDown, Loader2, FileText, RefreshCw, Volume2, Square } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * 文档库文章子页：Markdown 渲染展示（图片内嵌正确路径），支持 .md 下载。
 * 路由：/library/article/:docId/:scope?run=<run_id>
 * run 用于区分同一视频的多次处理（V1/V2…），缺省取最新版本。
 */
function LibraryArticlePage() {
  const { docId, scope } = useParams()
  const [searchParams] = useSearchParams()
  const runId = searchParams.get('run') || ''
  const navigate = useNavigate()
  const [article, setArticle] = useState(null)
  const [error, setError] = useState(null)
  const [repairing, setRepairing] = useState(false)
  // 语音朗读（TTS）：阶跃星辰 /audio/speech 合成后播放
  const [speaking, setSpeaking] = useState(false)
  const [ttsLoading, setTtsLoading] = useState(false)
  const audioRef = useRef(null)

  // Markdown → 纯文本（去图片/链接/标记），供 TTS 朗读
  const toPlainText = (md) => (md || '')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')       // 图片
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')    // 链接保留文字
    .replace(/^#{1,6}\s*/gm, '')                // 标题井号
    .replace(/[*`>_~]/g, '')                    // 强调/引用/删除线标记
    .replace(/\s+/g, ' ').trim().slice(0, 800)  // 压缩空白并截断（TTS 单次上限）

  const speak = async () => {
    if (speaking) { audioRef.current?.pause(); audioRef.current = null; setSpeaking(false); return }
    if (!article || ttsLoading) return
    setTtsLoading(true)
    try {
      const res = await fetch('/api/tts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: toPlainText(article.content) }),
      })
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || `HTTP ${res.status}`) }
      const url = URL.createObjectURL(await res.blob())
      if (!audioRef.current) audioRef.current = new Audio()
      audioRef.current.src = url
      audioRef.current.onended = () => { setSpeaking(false) }
      await audioRef.current.play()
      setSpeaking(true)
    } catch (e) {
      alert(`朗读失败：${e.message}`)
    } finally {
      setTtsLoading(false)
    }
  }

  const load = async (cancelledRef) => {
    const q = runId ? `?run_id=${encodeURIComponent(runId)}` : ''
    const res = await fetch(`/api/library/article/${docId}/${scope}${q}`)
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d.detail || `HTTP ${res.status}`)
    }
    const data = await res.json()
    if (!cancelledRef?.cancelled) setArticle(data)
  }

  // 处理中途生成的产物会缺配图：丢弃缓存、基于完整报告重新生成后重载
  const repair = async () => {
    if (repairing) return
    setRepairing(true)
    try {
      const body = new FormData()
      if (runId) body.append('run_id', runId)
      const res = await fetch(
        `/api/library/article/${docId}/${scope}/generate?force=true`,
        { method: 'POST', body })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        throw new Error(d.detail || `HTTP ${res.status}`)
      }
      await load()
    } catch (err) {
      setError(`重新生成失败：${err.message}`)
    } finally {
      setRepairing(false)
    }
  }

  useEffect(() => {
    const ref = { cancelled: false }
    load(ref).catch((err) => { if (!ref.cancelled) setError(err.message) })
    return () => { ref.cancelled = true }
  }, [docId, scope, runId])

  // Markdown 里的相对路径图片 → 静态目录（补任务输出目录层）。
  // 注意：不要手动 encodeURIComponent——react-markdown 的 urlTransform 已对
  // src 做过编码，再编码会变成 %25xx 双重编码导致 404。
  const imgOverride = (outputDir) => ({ src, alt, ...props }) => {
    let imageSrc = src
    if (src && !src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/')) {
      imageSrc = `/static/${outputDir ? outputDir + '/' : ''}${src}`
    }
    return <img src={imageSrc} alt={alt} {...props} className="max-w-full h-auto rounded-lg shadow-sm my-4" loading="lazy" />
  }

  return (
    <div className="workspace-page libraryarticlepage">
      <header className="page-toolbar">
        <div className="container mx-auto px-4 py-4 max-w-5xl flex items-center justify-between">
          <button
            onClick={() => navigate('/library')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回文档库</span>
          </button>
          <div className="flex items-center gap-2">
            {article && (
              <>
                <button
                  onClick={speak}
                  disabled={ttsLoading}
                  title="调用阶跃星辰 TTS 朗读本文（需在设置页配置阶跃星辰 API Key）"
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 disabled:opacity-60"
                >
                  {ttsLoading ? <Loader2 className="w-4 h-4 animate-spin" />
                    : speaking ? <Square className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  {speaking ? '停止朗读' : '朗读'}
                </button>
                {article.needs_image_repair && (
                  <button
                    onClick={repair}
                    disabled={repairing}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-800 text-sm font-medium hover:bg-amber-100 disabled:opacity-60"
                    title="该文体生成时报告还没插入关键帧，因此没有配图；点此基于完整报告重新生成"
                  >
                    {repairing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    {repairing ? '重新生成中…' : '重新生成（补图）'}
                  </button>
                )}
                <a
                  href={`/api/library/article/${docId}/${scope}/download${runId ? `?run_id=${encodeURIComponent(runId)}&` : '?'}fmt=md`}
                  download=""
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
                >
                  <Download className="w-4 h-4" />
                  下载 .md
                </a>
                <a
                  href={`/api/library/article/${docId}/${scope}/download${runId ? `?run_id=${encodeURIComponent(runId)}&` : '?'}fmt=pdf`}
                  download=""
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50"
                >
                  <FileDown className="w-4 h-4" />
                  下载 PDF
                </a>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {error ? (
          <div className="bg-white rounded-xl shadow p-10 text-center text-red-600">{error}</div>
        ) : !article ? (
          <div className="bg-white rounded-xl shadow p-10 text-center">
            <Loader2 className="w-10 h-10 text-primary-500 mx-auto mb-3 animate-spin" />
            <p className="text-gray-500 text-sm">加载中…</p>
          </div>
        ) : (
          <motion.article
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl shadow-lg p-10"
          >
            <div className="article-meta flex items-center gap-2 mb-4 text-xs text-gray-400">
              <span className="px-2 py-0.5 rounded bg-primary-50 text-primary-700 font-medium">{article.label}</span>
              <span className="px-2 py-0.5 rounded bg-gray-100 text-gray-600">{article.platform_label}</span>
              {article.version_label && (
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">
                  {article.version_label}
                  {article.version_count > 1 ? ` / 共 ${article.version_count} 版` : ''}
                </span>
              )}
              <a
                href={article.source_url}
                target="_blank"
                rel="noreferrer"
                className="truncate max-w-[420px] hover:text-primary-600"
              >
                {article.source_url}
              </a>
            </div>
            <div className="prose prose-lg max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ img: imgOverride(article.output_dir) }}>
                {article.content}
              </ReactMarkdown>
            </div>
          </motion.article>
        )}
      </main>
    </div>
  )
}

export default LibraryArticlePage
