import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Link2, Search, Download, Loader2, Play, Tv, Globe, AlertCircle, MessageCircle, Settings, KeyRound } from 'lucide-react'
import { getLinkInfo, searchLinkVideos, processLink } from '../api/videoService'
import ExtrasPicker, { getSelectedExtras } from './ExtrasPicker'

const PLATFORM_TABS = [
  { key: 'bilibili', label: 'B站', embed: (id) => `https://player.bilibili.com/player.html?bvid=${id}&autoplay=0` },
  { key: 'youtube', label: 'YouTube', embed: (id) => `https://www.youtube.com/embed/${id}` },
]

const PLATFORM_LABELS = {
  bilibili: 'B站',
  youtube: 'YouTube',
  wechat: '微信视频号',
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
  const [url, setUrl] = useState('')
  const [query, setQuery] = useState('')
  const [platform, setPlatform] = useState('bilibili')
  const [results, setResults] = useState([])
  const [preview, setPreview] = useState(null)       // 预览窗视频信息
  const [previewLoading, setPreviewLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState(null)

  const embedUrl = (item) => {
    const tab = PLATFORM_TABS.find((t) => t.key === item.platform)
    return tab && item.video_id ? tab.embed(item.video_id) : null
  }

  const showError = (msg) => setError(msg)

  const handleProbe = async () => {
    const link = url.trim()
    if (!link) return
    setPreviewLoading(true)
    setError(null)
    try {
      const info = await getLinkInfo(link)
      setPreview(info)
      setResults([])
    } catch (err) {
      showError(`获取视频信息失败: ${err.message}`)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSearch = async (kw) => {
    const keyword = (kw ?? query).trim()
    if (!keyword) return
    setSearchLoading(true)
    setError(null)
    try {
      const data = await searchLinkVideos(keyword, platform, 8)
      setResults(data.results || [])
      setPreview(null)
    } catch (err) {
      showError(`搜索失败: ${err.message}`)
    } finally {
      setSearchLoading(false)
    }
  }

  const handleProcess = async (link) => {
    if (processing) return
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

  const InfoMeta = ({ item }) => (
    <div className="text-sm text-gray-600 space-y-1">
      <p className="font-semibold text-gray-900">{item.title}</p>
      <p className="flex items-center gap-3 text-xs">
        {item.uploader && <span>UP: {item.uploader}</span>}
        {item.duration && <span>时长: {formatDuration(item.duration)}</span>}
        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">
          {PLATFORM_LABELS[item.platform] || '网页'}
        </span>
      </p>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* 顶部导航 */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
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
        {/* 链接输入 + 搜索区 */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
          <div className="flex items-center space-x-2">
            <Link2 className="w-5 h-5 text-primary-600" />
            <h2 className="text-base font-bold text-gray-900">粘贴视频链接</h2>
          </div>
          <div className="flex items-center space-x-3">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleProbe()}
              placeholder="支持 B站 / YouTube / 微信视频号分享链接（weixin.qq.com/sph/...），可直接粘贴分享文案"
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
              onClick={() => handleProcess(url.trim())}
              disabled={processing || !url.trim()}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-primary-600 to-purple-600 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
            >
              {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              <span>一键下载处理</span>
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
                {PLATFORM_TABS.map((t) => (
                  <button
                    key={t.key}
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
                placeholder={`在${platform === 'bilibili' ? 'B站' : 'YouTube'}搜索视频关键词...`}
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
            </div>
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
          </div>
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
                  className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-gradient-to-r from-primary-600 to-purple-600 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
                >
                  {processing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  <span>一键下载处理</span>
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
                  ) : preview.platform === 'wechat' ? (
                    <div className="w-full h-[420px] flex flex-col items-center justify-center gap-3 text-gray-400 px-8 text-center">
                      <MessageCircle className="w-12 h-12" />
                      <p className="text-sm font-medium text-gray-300">微信视频号内容不支持网页内嵌预览</p>
                      <p className="text-xs text-gray-500 leading-relaxed">
                        点击右上角“一键下载处理”将调用解析服务下载；
                        若解析失败（链接过期/服务限流），请用本地工具下载后到“上传视频”页上传处理
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
