import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Link2, Search, Download, Loader2, Play, Tv, Globe, AlertCircle, MessageCircle, Settings, KeyRound, NotebookPen, ThumbsUp, Star, MessageSquare } from 'lucide-react'
import { getLinkInfo, searchLinkVideos, processLink, generateSubtitleNotes } from '../api/videoService'
import ExtrasPicker, { getSelectedExtras } from './ExtrasPicker'
import { useConfigGate } from './ConfigGateProvider'

const PLATFORM_TABS = [
  { key: 'bilibili', label: 'B站', searchable: true, embed: (id) => `https://player.bilibili.com/player.html?bvid=${id}&autoplay=0` },
  { key: 'youtube', label: 'YouTube', searchable: true, embed: (id) => `https://www.youtube.com/embed/${id}` },
  { key: 'douyin', label: '抖音', searchable: true, embed: null },   // 抖音无可公开内嵌播放器
  // X：官方 embed 在未登录/受限网络下常加载不出，改为提示 + cookie 说明（同抖音）；
  // 关键词搜索需登录 GraphQL 不做，仅支持粘贴推文链接
  { key: 'x', label: 'X', searchable: false, embed: null },
]

const PLATFORM_LABELS = {
  bilibili: 'B站',
  youtube: 'YouTube',
  wechat: '微信视频号',
  douyin: '抖音',
  x: 'X',
}

function formatDuration(seconds) {
  if (!seconds) return '未知'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}

function LinkProcess() {
  const navigate = useNavigate()
  const location = useLocation()
  const { guardConfig } = useConfigGate()
  const [url, setUrl] = useState(location.state?.url || '')
  const [query, setQuery] = useState('')
  const [platform, setPlatform] = useState('bilibili')
  const [results, setResults] = useState([])
  const [preview, setPreview] = useState(null)       // 预览窗视频信息
  const [previewLoading, setPreviewLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [notesLoading, setNotesLoading] = useState(false)
  const [notesResult, setNotesResult] = useState(null)
  const [error, setError] = useState(null)

  const embedUrl = (item) => {
    const tab = PLATFORM_TABS.find((t) => t.key === item.platform)
    // embed 可能为 null（如抖音无可公开内嵌播放器），必须判可调用，
    // 否则空调用会让整个页面崩溃白屏
    return tab && typeof tab.embed === 'function' && item.video_id
      ? tab.embed(item.video_id)
      : null
  }

  const showError = (msg) => setError(msg)

  // 多集模式：B站系列链接探测后拉取分集列表，勾选批量排队处理
  const [episodes, setEpisodes] = useState(null)     // {type, title, episodes} | null
  const [selectedEps, setSelectedEps] = useState(() => new Set())
  const [batchQueued, setBatchQueued] = useState(0)  // 已加入队列数

  const loadEpisodes = async (link) => {
    setEpisodes(null)
    setSelectedEps(new Set())
    setBatchQueued(0)
    try {
      const res = await fetch('/api/video/link/episodes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: link }),
      })
      if (!res.ok) return
      const data = await res.json()
      if (data.episodes?.length > 1) {
        setEpisodes(data)
        setSelectedEps(new Set(data.episodes.map((_, i) => i)))
      }
    } catch { /* 分集获取失败不影响单集流程 */ }
  }

  const toggleEpisode = (idx) => {
    setSelectedEps(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
  }

  const handleBatchProcess = async () => {
    if (!episodes || batchQueued > 0 || processing) return
    const chosen = episodes.episodes.filter((_, i) => selectedEps.has(i))
    if (!chosen.length) return
    let firstTaskId = null
    for (const ep of chosen) {
      try {
        const result = await processLink(ep.url, '自由学习', getSelectedExtras())
        if (!firstTaskId) firstTaskId = result.task_id
        setBatchQueued(q => q + 1)
      } catch (err) {
        showError(`「${ep.title.slice(0, 20)}」加入队列失败: ${err.message}`)
      }
    }
    if (firstTaskId) navigate(`/processing/${firstTaskId}`)
  }

  const handleProbe = async () => {
    const link = url.trim()
    if (!link) return
    setPreviewLoading(true)
    setError(null)
    try {
      const info = await getLinkInfo(link)
      setPreview(info)
      setResults([])
      if (info.platform === 'bilibili') await loadEpisodes(link)
      else setEpisodes(null)
    } catch (err) {
      showError(`获取视频信息失败: ${err.message}`)
    } finally {
      setPreviewLoading(false)
    }
  }

  // 搜索：初始 1 页 8 条；「搜索更多」翻页累积，按 web_url 去重；空页视为穷尽
  const [searchPage, setSearchPage] = useState(1)
  const [exhausted, setExhausted] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const mergeResults = (existing, incoming) => {
    const seen = new Set(existing.map(r => r.webpage_url || r.video_id || r.id))
    const fresh = (incoming || []).filter(r => !seen.has(r.webpage_url || r.video_id || r.id))
    return [...existing, ...fresh]
  }

  const handleSearch = async (kw) => {
    const keyword = (kw ?? query).trim()
    if (!keyword) return
    setSearchLoading(true)
    setError(null)
    try {
      const data = await searchLinkVideos(keyword, platform, 8, 1)
      setSearchPage(1)
      setExhausted((data.results || []).length === 0)
      setResults(data.results || [])
      setPreview(null)
    } catch (err) {
      showError(`搜索失败: ${err.message}`)
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSearchMore = async () => {
    const keyword = query.trim()
    if (!keyword || loadingMore || exhausted) return
    setLoadingMore(true)
    setError(null)
    try {
      const next = searchPage + 1
      const data = await searchLinkVideos(keyword, platform, 8, next)
      const incoming = data.results || []
      const merged = mergeResults(results, incoming)
      setSearchPage(next)
      setResults(merged)
      // 空页或没有新增（去重后无增量）→ 穷尽
      if (incoming.length === 0 || merged.length === results.length) setExhausted(true)
    } catch (err) {
      showError(`加载更多失败: ${err.message}`)
    } finally {
      setLoadingMore(false)
    }
  }

  const handleProcess = async (link) => {
    if (processing) return
    // 未配置 LLM/VLM/ASR 时先引导去设置，避免点完只看到报错
    if (!(await guardConfig(['llm', 'vlm', 'asr']))) return
    setProcessing(true)
    setError(null)
    try {
      const result = await processLink(link, '自由学习', getSelectedExtras())
      navigate(`/processing/${result.task_id}`)
    } catch (err) {
      showError(`创建任务失败: ${err.message}`)
      setProcessing(false)
    }
  }

  const handleNotes = async () => {
    const link = url.trim()
    if (!link || notesLoading) return
    // 字幕速记不下载视频、不走 ASR，但需要 LLM 整理要点
    if (!(await guardConfig(['llm']))) return
    setNotesLoading(true)
    setError(null)
    setNotesResult(null)
    try {
      const result = await generateSubtitleNotes(link)
      setNotesResult(result)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      showError(`字幕笔记生成失败: ${err.message}`)
    } finally {
      setNotesLoading(false)
    }
  }

  // 字幕笔记：渲染 Markdown（含 Mermaid 关系图）
  const notesRef = useRef(null)
  useEffect(() => {
    const el = notesRef.current
    if (!el || !notesResult?.notes) return
    let cancelled = false
    const render = async () => {
      const { marked } = await import('marked')
      let html = marked.parse(notesResult.notes)
      // 把 mermaid 代码块转成 <div class="mermaid">，其余保留
      html = html.replace(
        /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,
        (_, code) => `<div class="mermaid">${code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')}</div>`
      )
      if (cancelled) return
      el.innerHTML = html
      if (html.includes('class="mermaid"')) {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' })
        await mermaid.run({ nodes: el.querySelectorAll('.mermaid') })
      }
    }
    render().catch(err => console.error('笔记渲染失败:', err))
    return () => { cancelled = true }
  }, [notesResult])

  // 新窗口打开：桌面客户端内 window.open 不可用（WebView 返回 null），
  // 改走原生桥写临时文件后用系统浏览器打开；纯浏览器仍用 Blob URL
  //（用 Blob 而非静态路径，避免中文/特殊字符编码导致打不开）
  const buildNotesHtml = () => `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>${notesResult.title}</title>
<style>body{max-width:820px;margin:32px auto;padding:0 20px;font:15px/1.8 -apple-system,"PingFang SC",sans-serif;color:#1f2937}
pre{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
h1,h2,h3{line-height:1.35}</style>
</head><body><pre style="white-space:pre-wrap;font-family:inherit;background:none;padding:0">${notesResult.notes.replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'}[c]))}</pre></body></html>`

  const handleOpenNotesWindow = async () => {
    const html = buildNotesHtml()
    const bridge = window.pywebview?.api
    if (bridge?.open_html) {
      try {
        await bridge.open_html(html, `字幕笔记-${notesResult.title || ''}`)
        return
      } catch { /* 桥失败时退回窗口方式 */ }
    }
    const win = window.open('', '_blank')
    if (!win) {
      alert('浏览器拦截了新窗口，请允许弹窗后重试')
      return
    }
    win.document.write(html)
    win.document.close()
  }

  // 热度数字格式化：万位缩写（1955206 → 195.5万，96030 → 9.6万），其余原样
  const fmtHeat = (n) => {
    if (n == null || isNaN(n)) return null
    if (n >= 100000000) return `${(n / 100000000).toFixed(1)}亿`
    if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
    return String(n)
  }

  const HeatStats = ({ stats }) => {
    if (!stats) return null
    const items = [
      { key: 'views', label: '播放', icon: Play },
      { key: 'likes', label: '点赞', icon: ThumbsUp },
      { key: 'favorites', label: '收藏', icon: Star },
      { key: 'comments', label: '评论', icon: MessageSquare },
    ].map(s => ({ ...s, text: fmtHeat(stats[s.key]) })).filter(s => s.text)
    if (!items.length) return null
    return (
      <p className="flex items-center flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
        {items.map(({ key, label, icon: Icon, text }) => (
          <span key={key} className="inline-flex items-center gap-1" title={`${label} ${text}`}>
            <Icon size={12} className="text-gray-400" />{text}
          </span>
        ))}
      </p>
    )
  }

  const InfoMeta = ({ item }) => (
    <div className="text-sm text-gray-600 space-y-1">
      <p className="font-semibold text-gray-900">{item.title}</p>
      <p className="flex items-center gap-3 text-xs">
        {item.uploader && <span>UP: {item.uploader}</span>}
        {item.duration && <span>时长: {formatDuration(item.duration)}</span>}
        {item.published_at && (
          <span title="视频发布时间">📅 {item.published_at}</span>
        )}
        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">
          {PLATFORM_LABELS[item.platform] || '网页'}
        </span>
      </p>
      <HeatStats stats={item.stats} />
    </div>
  )

  return (
    <div className="workspace-page linkprocess">
      {/* 顶部导航 */}
      <header className="page-toolbar">
        <div className="container mx-auto px-4 py-4 max-w-6xl flex items-center justify-between">
          <button onClick={() => navigate(-1)} className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition">
            <ArrowLeft className="w-5 h-5" />
            <span>返回</span>
          </button>
          <div className="flex items-center space-x-2">
            <Tv className="w-5 h-5 text-primary-600" />
            <h1 className="text-lg font-bold text-gray-900">在线视频链接处理</h1>
          </div>
          <button
            onClick={() => navigate('/settings')}
            title="设置控制台（ASR / LLM / VLM / 视频号 Cookie）"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-gray-500 hover:text-primary-600 hover:border-primary-300 transition text-sm"
          >
            <Settings className="w-4 h-4" />
            <span>设置</span>
          </button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-6xl space-y-6">
        <div className="page-intro"><div className="eyebrow">FROM VIDEO TO KNOWLEDGE</div><h1>发现值得留下的内容。</h1><p>粘贴视频链接，或搜索感兴趣的主题，开始整理你的下一份笔记。</p></div>
        {/* 链接输入 + 搜索区 */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
          <div className="flex items-center space-x-2">
            <Link2 className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-bold text-gray-900">粘贴视频链接</h2>
          </div>
          <div className="link-input-row">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleProbe()}
              aria-label="视频链接或分享文案"
              placeholder="支持 B站 / YouTube / 抖音 / X / 微信视频号链接，可直接粘贴分享文案（如 v.douyin.com/...）"
              className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
            />
            <button
              onClick={handleProbe}
              disabled={previewLoading || !url.trim()}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
            >
              {previewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
              <span>预览</span>
            </button>
            <button
              onClick={handleNotes}
              disabled={notesLoading || !url.trim()}
              title="不下载视频，直接用平台字幕生成纯文本笔记（仅 B站 / YouTube）"
              className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
            >
              {notesLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <NotebookPen className="w-4 h-4" />}
              <span>字幕笔记</span>
            </button>
            <button
              onClick={() => handleProcess(url.trim())}
              disabled={processing || !url.trim()}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
            >
              {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span>生成图文报告</span>
            </button>
          </div>

          {/* 附加产物（可选）：勾选后任务完成时自动生成 */}
          <div className="flex items-center space-x-3">
            <span className="text-xs text-gray-500 flex-shrink-0">完成后生成（可选，默认不生成）：</span>
            <ExtrasPicker />
          </div>

          <div className="border-t border-gray-100 pt-4">
            <div className="flex items-center space-x-2 mb-3">
              <Search className="w-4 h-4 text-primary-600" />
              <h3 className="text-sm font-bold text-gray-900">或搜索视频</h3>
              <div className="flex items-center space-x-1 ml-2">
                {PLATFORM_TABS.filter((t) => t.searchable).map((t) => (
                  <button
                    key={t.key}
                    aria-pressed={platform === t.key}
                    onClick={() => setPlatform(t.key)}
                    className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
                      platform === t.key ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={`在${({bilibili: 'B站', youtube: 'YouTube', douyin: '抖音'})[platform] || ''}搜索视频关键词...`}
                className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm"
              />
              <button
                onClick={() => handleSearch()}
                disabled={searchLoading || !query.trim()}
                className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gray-100 border border-gray-300 text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
              >
                {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>搜索</span>
              </button>
              {platform === 'douyin' && (
                <a
                  href={`https://www.douyin.com/search/${encodeURIComponent(query || '')}`}
                  target="_blank"
                  rel="noreferrer"
                  title="服务端搜索受限，改为浏览器检索（你已登录），找到后复制链接粘贴到上方"
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700"
                >
                  <Search className="w-4 h-4" />
                  <span>浏览器搜索</span>
                </a>
              )}
            </div>
            {platform === 'douyin' && (
              <p className="mt-2 text-xs text-gray-500 leading-relaxed">
                抖音搜索接口有浏览器签名校验（反爬），服务端无法直接检索。请用右侧「浏览器搜索」打开抖音搜索，
                找到视频后复制链接粘贴到上方输入框即可处理（你浏览器的登录态天然可用）。
              </p>
            )}
          </div>
        </section>

        {error && (
          <div className="flex items-center space-x-2 p-4 bg-red-50 border-l-4 border-red-500 rounded-xl text-red-700 text-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="flex-1">{error}</span>
            {/Cookie/.test(error) && (
              <button
                onClick={() => navigate('/settings')}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold flex-shrink-0 transition"
              >
                <KeyRound className="w-3.5 h-3.5" />
                <span>去配置 Cookie</span>
              </button>
            )}
            {platform === 'douyin' && (
              <a
                href={`https://www.douyin.com/search/${encodeURIComponent(query || '')}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 text-red-700 text-xs font-semibold flex-shrink-0 transition"
              >
                <Search className="w-3.5 h-3.5" />
                <span>打开抖音搜索</span>
              </a>
            )}
          </div>
        )}

        {/* 字幕笔记结果 */}
        {notesResult && (
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-bold text-gray-900 flex items-center space-x-2">
                <NotebookPen className="w-5 h-5 text-primary-600" />
                <span>字幕笔记：{notesResult.title}</span>
              </h2>
              <div className="flex items-center gap-2">
                <a
                  href={notesResult.md_url}
                  className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700"
                >
                  下载 Markdown
                </a>
                <a
                  href={notesResult.txt_url}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  下载 .txt
                </a>
                {notesResult.pdf_url && (
                  <a
                    href={notesResult.pdf_url}
                    className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700"
                  >
                    下载 PDF
                  </a>
                )}
                <button
                  onClick={handleOpenNotesWindow}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  新窗口打开
                </button>
              </div>
            </div>
            <div className="p-5">
              <p className="text-xs text-gray-400 mb-3">
                来源：{notesResult.platform === 'bilibili' ? 'B站' : 'YouTube'} 字幕（{notesResult.lang}）· Markdown 笔记（含概念关系图）
              </p>
              <div className="markdown-body text-sm text-gray-800 leading-relaxed"
                   ref={notesRef} />
            </div>
          </section>
        )}

        {/* 预览窗口 */}
        {(preview || previewLoading) && (
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-bold text-gray-900 flex items-center space-x-2">
                <Play className="w-5 h-5 text-primary-600" />
                <span>预览窗口</span>
              </h2>
              {preview && (
                <button
                  onClick={() => handleProcess(preview.webpage_url)}
                  disabled={processing}
                  className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-primary-600 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
                >
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  <span>生成图文报告</span>
                </button>
              )}
            </div>
            {previewLoading ? (
              <div className="h-[420px] flex items-center justify-center text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            ) : preview && (
              <div className="grid grid-cols-1 lg:grid-cols-3">
                <div className="lg:col-span-2 bg-black">
                  {embedUrl(preview) ? (
                    <iframe
                      key={preview.webpage_url}
                      src={embedUrl(preview)}
                      className="w-full h-[420px]"
                      frameBorder="0"
                      allowFullScreen
                      allow="encrypted-media; fullscreen"
                      title={preview.title}
                    />
                  ) : preview.platform === 'wechat' || preview.platform === 'douyin' || preview.platform === 'x' ? (
                    <div className="w-full h-[420px] flex flex-col items-center justify-center gap-3 text-gray-400 px-8 text-center">
                      <MessageCircle className="w-12 h-12" />
                      <p className="text-sm font-medium text-gray-300">
                        {preview.platform === 'douyin' ? '抖音内容不支持网页内嵌预览'
                          : preview.platform === 'x' ? 'X 内容不支持网页内嵌预览'
                          : '微信视频号内容不支持网页内嵌预览'}
                      </p>
                      <p className="text-xs text-gray-500 leading-relaxed">
                        {preview.platform === 'douyin'
                          ? '点击右上角「生成图文报告」将直接下载并处理；抖音下载需要登录态 Cookie，可在设置页「抖音 cookies」配置（桌面客户端可用「应用内登录读取」，或从浏览器读取/手动粘贴）'
                          : preview.platform === 'x'
                          ? '点击右上角「生成图文报告」将直接下载并处理；X 下载需要登录态 Cookie（需含 auth_token），可在设置页「X cookies」配置（桌面客户端可用「应用内登录读取」，或从浏览器读取/手动粘贴）'
                          : '点击右上角「生成图文报告」将调用解析服务下载；若解析失败（链接过期/服务限流），请用本地工具下载后到「上传视频」页上传处理'}
                      </p>
                    </div>
                  ) : (
                    preview.thumbnail && (
                      <img src={preview.thumbnail} alt={preview.title} referrerPolicy="no-referrer" className="w-full h-[420px] object-contain" />
                    )
                  )}
                </div>
                <div className="p-5">
                  <InfoMeta item={preview} />
                  {preview.description && (
                    <p className="mt-3 text-xs text-gray-500 leading-relaxed line-clamp-6">{preview.description}</p>
                  )}
                  <p className="mt-4 text-xs text-gray-400">
                    链接：{preview.webpage_url}
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        {/* 多集模式：B站系列/多P 分集选择，批量排队处理 */}
        {episodes && episodes.episodes.length > 1 && (
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-5 border-b border-gray-100">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Tv className="w-5 h-5 text-primary-600" />
                  检测到多集系列（{episodes.episodes.length} 集）
                </h2>
                <button
                  onClick={() => setSelectedEps(selectedEps.size === episodes.episodes.length
                    ? new Set()
                    : new Set(episodes.episodes.map((_, i) => i)))}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  {selectedEps.size === episodes.episodes.length ? '取消全选' : '全选'}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1.5">
                {episodes.title} · 勾选要处理的分集，逐集排队生成报告（已完成下载的分集会复用缓存）
              </p>
            </div>
            <div className="max-h-72 overflow-y-auto px-5 py-2">
              {episodes.episodes.map((ep, i) => (
                <label key={ep.url} className="flex items-center gap-2.5 py-1.5 cursor-pointer hover:bg-gray-50 rounded px-1">
                  <input type="checkbox" checked={selectedEps.has(i)}
                         onChange={() => toggleEpisode(i)}
                         className="accent-primary-600" />
                  <span className="text-sm text-gray-800 flex-1 truncate">{ep.title}</span>
                  {ep.duration && <span className="text-xs text-gray-400 flex-shrink-0">{formatDuration(ep.duration)}</span>}
                </label>
              ))}
            </div>
            <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                已选 {selectedEps.size} / {episodes.episodes.length} 集
                {batchQueued > 0 && <span className="text-primary-600 ml-2">已加入队列 {batchQueued} 集</span>}
              </span>
              <button
                onClick={handleBatchProcess}
                disabled={selectedEps.size === 0 || batchQueued > 0 || processing}
                className="px-5 py-2 rounded-lg bg-primary-600 text-white text-sm font-bold hover:bg-primary-700 disabled:opacity-50 flex items-center gap-1.5"
              >
                <Download className="w-4 h-4" />
                批量处理（{selectedEps.size} 集）
              </button>
            </div>
          </section>
        )}

        {/* 搜索结果卡片 */}
        {results.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-base font-bold text-gray-900">搜索结果</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results.map((item, idx) => (
                <motion.div
                  key={item.webpage_url || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden flex hover:shadow-md transition-shadow"
                >
                  <div
                    className="relative w-44 flex-shrink-0 cursor-pointer bg-gray-100"
                    onClick={() => { setPreview(item); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                  >
                    {item.thumbnail ? (
                      <img src={item.thumbnail} alt={item.title} referrerPolicy="no-referrer" className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none' }} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-300">
                        <Play className="w-8 h-8" />
                      </div>
                    )}
                    {item.duration && (
                      <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs">
                        {formatDuration(item.duration)}
                      </span>
                    )}
                  </div>
                  <div className="p-4 flex flex-col justify-between flex-1">
                    <InfoMeta item={item} />
                    <div className="flex items-center gap-2 mt-3">
                      <button
                        onClick={() => { setPreview(item); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                        className="px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium text-gray-700 hover:bg-gray-50"
                      >
                        预览
                      </button>
                      <button
                        onClick={() => handleProcess(item.webpage_url)}
                        disabled={processing}
                        className="px-3 py-1.5 rounded-lg bg-primary-600 text-white text-xs font-bold hover:bg-primary-700 disabled:opacity-50 flex items-center gap-1"
                      >
                        <Download className="w-3.5 h-3.5" />
                        下载处理
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
            {/* 搜索更多：翻页累积，直到该平台穷尽 */}
            <div className="flex items-center justify-center gap-3 pt-2 pb-1">
              {exhausted ? (
                <span className="text-xs text-gray-400">该平台已没有更多结果</span>
              ) : (
                <button
                  onClick={handleSearchMore}
                  disabled={loadingMore}
                  className="px-5 py-2 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 flex items-center gap-1.5"
                >
                  {loadingMore ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  {loadingMore ? '搜索中…' : '搜索更多'}
                </button>
              )}
            </div>
          </section>
        )}

        <p className="text-xs text-gray-400 pb-10 text-center">
          请确保对所处理的视频内容拥有相应权利或已获得授权，仅用于个人学习用途
        </p>
      </main>
    </div>
  )
}

export default LinkProcess
