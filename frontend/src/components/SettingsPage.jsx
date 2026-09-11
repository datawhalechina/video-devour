import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Save, Radio, HardDriveDownload, KeyRound, CheckCircle, XCircle, Loader2, GraduationCap } from 'lucide-react'
import { getSettings, updateSettings, testSettings, importCookiesFromBrowser, youtubeEnvCheck } from '../api/settingsService'

// 供应商预设：点击芯片自动填充接口地址与推荐模型
const PROVIDER_PRESETS = {
  llm: [
    { key: 'dashscope', label: 'DashScope 阿里云', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'] },
    { key: 'stepfun', label: '阶跃星辰 StepFun', url: 'https://api.stepfun.com/step_plan/v1', models: ['step-3.7-flash', 'step-3.5-flash'] },
    { key: 'deepseek', label: 'DeepSeek', url: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-reasoner'] },
    { key: 'ark', label: '火山方舟', url: 'https://ark.cn-beijing.volces.com/api/v3', models: ['doubao-seed-1-6-flash-250828'] },
    { key: 'openai', label: 'OpenAI', url: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini'] },
  ],
  vlm: [
    { key: 'dashscope', label: 'DashScope 阿里云', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-vl-max', 'qwen-vl-plus'] },
    { key: 'stepfun', label: '阶跃星辰 StepFun', url: 'https://api.stepfun.com/step_plan/v1', models: ['step-3.7-flash'] },
    { key: 'ark', label: '火山方舟', url: 'https://ark.cn-beijing.volces.com/api/v3', models: ['doubao-seed-1-6-flash-250828'] },
    { key: 'openai', label: 'OpenAI', url: 'https://api.openai.com/v1', models: ['gpt-4o'] },
  ],
}

function SettingsPage() {
  const navigate = useNavigate()
  const [settings, setSettings] = useState(null)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState(null)
  const [testing, setTesting] = useState({})   // { asr: bool, llm: bool, vlm: bool }
  const [testResults, setTestResults] = useState({})  // { asr: {ok, message}, ... }
  const [cookieImport, setCookieImport] = useState({ loading: false, message: '', attempts: [] })
  const [cacheInfo, setCacheInfo] = useState(null)
  const [offlineCheck, setOfflineCheck] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await getSettings()
      setSettings(data)
      loadCache()
      setForm({
        asr_mode: data.asr_mode,
        dashscope_api_key: data.dashscope_api_key,
        online_asr_model: data.online_asr_model,
        online_asr_provider: data.online_asr_provider || 'dashscope',
        stepfun_api_key: data.stepfun_api_key,

        llm_api_key: data.llm_api_key,
        llm_api_url: data.llm_api_url,
        llm_model_type: data.llm_model_type,
        vlm_api_key: data.vlm_api_key,
        vlm_api_url: data.vlm_api_url,
        vlm_model_type: data.vlm_model_type,
        default_education_level: data.default_education_level,

        wechat_yuanbao_cookie: data.wechat_yuanbao_cookie || '',
        wechat_resolver_url: data.wechat_resolver_url || '',
        wechat_resolver_token: data.wechat_resolver_token || '',
        youtube_cookies: data.youtube_cookies || '',
        douyin_cookies: data.douyin_cookies || '',
        bilibili_sessdata: data.bilibili_sessdata || '',
        cookie_browser: data.cookie_browser || '',
      })
    } catch (err) {
      setError(`加载设置失败: ${err.message}`)
    }
  }

  const setField = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
    if (key === 'asr_mode' && value === 'offline') checkOffline()
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveMessage(null)
    setError(null)
    try {
      const result = await updateSettings(form)
      setSettings(result.settings)
      setForm(prev => ({
        ...prev,
        ...result.settings,
      }))
      setSaveMessage({ ok: true, text: '设置已保存并生效' })
    } catch (err) {
      setSaveMessage({ ok: false, text: `保存失败: ${err.message}` })
    } finally {
      setSaving(false)
    }
  }

  const [ytCheck, setYtCheck] = useState({ loading: false, result: null })

  const handleYtCheck = async () => {
    if (ytCheck.loading) return
    setYtCheck({ loading: true, result: null })
    try {
      const result = await youtubeEnvCheck()
      setYtCheck({ loading: false, result })
    } catch (err) {
      setYtCheck({ loading: false, result: { checks: {}, suggestions: [`自检失败: ${err.message}`] } })
    }
  }

  const checkOffline = async () => {
    try {
      const res = await fetch('/api/asr/offline-check')
      if (res.ok) setOfflineCheck(await res.json())
    } catch (e) { /* 忽略 */ }
  }

  const loadCache = async () => {
    try {
      const res = await fetch('/api/downloads/cache')
      if (res.ok) setCacheInfo(await res.json())
    } catch (e) { /* 忽略 */ }
  }

  const handleImportCookies = async () => {
    if (cookieImport.loading) return
    setCookieImport({ loading: true, message: '正在读取浏览器 Cookie（首次可能需要 1-3 分钟；若弹出钥匙串授权请点「允许」）…', attempts: [] })
    try {
      const result = await importCookiesFromBrowser(form.cookie_browser || '')
      setCookieImport({ loading: false, message: result.message, attempts: result.attempts || [] })
      // 读取到的字段由后端直接写入了设置，刷新表单中的脱敏值
      const data = await getSettings()
      setForm(prev => ({
        ...prev,
        wechat_yuanbao_cookie: data.wechat_yuanbao_cookie || prev.wechat_yuanbao_cookie,
        youtube_cookies: data.youtube_cookies || prev.youtube_cookies,
        bilibili_sessdata: data.bilibili_sessdata || prev.bilibili_sessdata,
      }))
    } catch (err) {
      setCookieImport({ loading: false, message: `读取失败: ${err.message}`, attempts: [] })
    }
  }

  const handleTest = async (target) => {
    setTesting(prev => ({ ...prev, [target]: true }))
    try {
      // 先保存再测试，确保测试用的是当前填写的配置
      await updateSettings(form)
      const result = await testSettings(target)
      setTestResults(prev => ({ ...prev, ...result.results }))
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [target]: { ok: false, message: `测试失败: ${err.message}` }
      }))
    } finally {
      setTesting(prev => ({ ...prev, [target]: false }))
    }
  }

  // 当前表单 URL 匹配到的供应商（未匹配则为 custom）
  const detectProvider = (section) => {
    const urlKey = section === 'llm' ? 'llm_api_url' : 'vlm_api_url'
    const url = form[urlKey] || ''
    const hit = PROVIDER_PRESETS[section].find(p => url.startsWith(p.url))
    return hit ? hit.key : 'custom'
  }

  // 点击供应商芯片：自动填地址 + 推荐模型；StepFun 时自动复用 ASR 的 Key
  const applyProvider = (section, prov) => {
    const updates = section === 'llm'
      ? { llm_api_url: prov.url, llm_model_type: prov.models[0] }
      : { vlm_api_url: prov.url, vlm_model_type: prov.models[0] }
    if (prov.key === 'stepfun' && form.stepfun_api_key) {
      if (section === 'llm' && !form.llm_api_key) updates.llm_api_key = form.stepfun_api_key
      if (section === 'vlm' && !form.vlm_api_key) updates.vlm_api_key = form.stepfun_api_key
    }
    setForm(prev => ({ ...prev, ...updates }))
  }

  const ProviderChips = ({ section }) => {
    const active = detectProvider(section)
    return (
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {PROVIDER_PRESETS[section].map(prov => (
          <button
            key={prov.key}
            onClick={() => applyProvider(section, prov)}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border-2 transition ${
              active === prov.key
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {prov.label}
          </button>
        ))}
        <span className={`px-4 py-1.5 rounded-full text-xs font-medium border-2 ${active === 'custom' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-400'}`}>
          自定义
        </span>
      </div>
    )
  }

  const TestResult = ({ target }) => {
    const result = testResults[target]
    if (!result) return null
    return (
      <div className={`mt-2 flex items-start space-x-2 text-sm ${result.ok ? 'text-green-700' : 'text-red-700'}`}>
        {result.ok ? <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" /> : <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />}
        <span>{result.message}</span>
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const inputClass = "w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-sm transition"
  const labelClass = "block text-sm font-semibold text-gray-700 mb-1.5"

  return (
    <div className="workspace-page settingspage">
      {/* 顶部导航 */}
      <header className="page-toolbar">
        <div className="container mx-auto px-4 py-4 max-w-4xl flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>返回</span>
          </button>
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5 text-primary-600" />
            <h1 className="text-lg font-bold text-gray-900">设置控制台</h1>
          </div>
          <div className="w-16" />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl space-y-6">
        <div className="page-intro"><div className="eyebrow">MAKE IT YOURS</div><h1>适合你的学习方式。</h1><p>管理语音识别、内容生成和个人偏好，让每次整理更顺手。</p></div>
        {/* ASR 模式 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center space-x-2">
            <Radio className="w-5 h-5 text-primary-600" />
            <span>语音识别模式</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setField('asr_mode', 'offline')}
              className={`p-4 rounded-xl border-2 text-left transition ${form.asr_mode === 'offline' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center space-x-2 mb-1">
                <HardDriveDownload className="w-5 h-5 text-gray-700" />
                <span className="font-semibold text-gray-900">离线模式（本地模型）</span>
              </div>
              <p className="text-sm text-gray-500">本地 FunASR Paraformer，无 API 消耗；需下载约 2GB 模型，首次很慢且占资源（按需安装）</p>
            </button>
            <button
              onClick={() => setField('asr_mode', 'online')}
              className={`p-4 rounded-xl border-2 text-left transition ${form.asr_mode === 'online' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center space-x-2 mb-1">
                <Radio className="w-5 h-5 text-gray-700" />
                <span className="font-semibold text-gray-900">在线模式（云端 API）</span>
              </div>
              <p className="text-sm text-gray-500">云端识别，零模型下载、启动即用（推荐），需填写 API Key</p>
            </button>
          </div>

          {form.asr_mode === 'online' && (
            <div className="mt-5 space-y-4">
              <div>
                <label className={labelClass}>云端识别提供商</label>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    onClick={() => { setField('online_asr_provider', 'dashscope'); setField('online_asr_model', 'fun-asr-realtime') }}
                    className={`px-5 py-2 rounded-lg border-2 text-sm font-medium transition ${form.online_asr_provider === 'dashscope' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                  >
                    DashScope（阿里云）
                  </button>
                  <button
                    onClick={() => { setField('online_asr_provider', 'stepfun'); setField('online_asr_model', 'stepaudio-2.5-asr') }}
                    className={`px-5 py-2 rounded-lg border-2 text-sm font-medium transition ${form.online_asr_provider === 'stepfun' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                  >
                    阶跃星辰 StepFun
                  </button>
                </div>
              </div>
              {form.online_asr_provider === 'stepfun' ? (
                <div>
                  <label className={labelClass}>StepFun API Key</label>
                  <input
                    type="password"
                    value={form.stepfun_api_key || ''}
                    onChange={(e) => setField('stepfun_api_key', e.target.value)}
                    placeholder="阶跃星辰 API Key"
                    className={inputClass}
                  />
                </div>
              ) : (
                <div>
                  <label className={labelClass}>DashScope API Key</label>
                  <input
                    type="password"
                    value={form.dashscope_api_key || ''}
                    onChange={(e) => setField('dashscope_api_key', e.target.value)}
                    placeholder="sk-..."
                    className={inputClass}
                  />
                </div>
              )}
              <div>
                <label className={labelClass}>在线识别模型</label>
                <input
                  type="text"
                  value={form.online_asr_model || ''}
                  onChange={(e) => setField('online_asr_model', e.target.value)}
                  placeholder={form.online_asr_provider === 'stepfun' ? 'stepaudio-2.5-asr' : 'fun-asr-realtime'}
                  className={inputClass}
                />
              </div>
              <button
                onClick={() => handleTest('asr')}
                disabled={testing.asr}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
              >
                {testing.asr ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
                <span>测试在线 ASR 连通性</span>
              </button>
              <TestResult target="asr" />
            </div>
          )}
        
          {form.asr_mode === 'offline' && (
            <div className="mt-5 p-4 rounded-xl bg-amber-50 border border-amber-200">
              <p className="text-sm font-semibold text-amber-800 mb-2">离线模式需要先安装本地模型</p>
              <p className="text-xs text-amber-700 leading-relaxed mb-3">
                本地语音识别约需 2GB 模型 + torch/funasr 依赖，首次安装耗时较久且占磁盘/内存。
                若只是临时使用，建议切回「在线模式」（零下载）。
              </p>
              {offlineCheck ? (
                <div className="text-xs space-y-1 mb-3">
                  <p className={offlineCheck.ready ? 'text-green-700' : 'text-amber-800'}>
                    {offlineCheck.ready ? '✓ 环境就绪，可直接使用' : '✗ 尚未就绪'}
                  </p>
                  <p className="text-amber-700">计算后端：{offlineCheck.compute_backend?.toUpperCase()}</p>
                  {offlineCheck.missing_models?.length > 0 && (
                    <p className="text-amber-700">缺少模型：{offlineCheck.missing_models.length} 个</p>
                  )}
                </div>
              ) : (
                <p className="text-xs text-amber-600 mb-3">正在检查环境…</p>
              )}
              <div className="flex flex-wrap gap-2">
                <button onClick={checkOffline} className="px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-xs font-medium text-amber-800 hover:bg-amber-100">
                  重新检查
                </button>
                {offlineCheck && !offlineCheck.ready && (
                  <span className="px-3 py-1.5 rounded-lg bg-amber-100 text-xs font-mono text-amber-800 select-all">
                    bash scripts/install_offline_asr.sh
                  </span>
                )}
              </div>
            </div>
          )}
</motion.section>

        {/* LLM 配置 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-4">LLM 配置（OpenAI 兼容接口）</h2>
          <label className={labelClass}>快速选择供应商</label>
          <ProviderChips section="llm" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className={labelClass}>API Key</label>
              <input
                type="password"
                value={form.llm_api_key || ''}
                onChange={(e) => setField('llm_api_key', e.target.value)}
                placeholder="sk-..."
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>接口地址（Base URL）</label>
              <input
                type="text"
                value={form.llm_api_url || ''}
                onChange={(e) => setField('llm_api_url', e.target.value)}
                placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>模型名称</label>
              <input
                type="text"
                value={form.llm_model_type || ''}
                onChange={(e) => setField('llm_model_type', e.target.value)}
                placeholder="qwen-max / deepseek-chat"
                className={inputClass}
              />
              <div className="flex flex-wrap gap-2 mt-2">
                {(PROVIDER_PRESETS.llm.find(p => detectProvider('llm') === p.key)?.models || []).map(m => (
                  <button key={m} onClick={() => setField('llm_model_type', m)}
                    className={`px-3 py-1 rounded-full text-xs transition ${form.llm_model_type === m ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <button
            onClick={() => handleTest('llm')}
            disabled={testing.llm}
            className="mt-4 flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {testing.llm ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
            <span>测试 LLM 连通性</span>
          </button>
          <TestResult target="llm" />
        </motion.section>

        {/* VLM 配置 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-4">VLM 配置（关键帧分析，OpenAI 兼容接口）</h2>
          <label className={labelClass}>快速选择供应商</label>
          <ProviderChips section="vlm" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className={labelClass}>API Key</label>
              <input
                type="password"
                value={form.vlm_api_key || ''}
                onChange={(e) => setField('vlm_api_key', e.target.value)}
                placeholder="sk-..."
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>接口地址（Base URL）</label>
              <input
                type="text"
                value={form.vlm_api_url || ''}
                onChange={(e) => setField('vlm_api_url', e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>模型名称</label>
              <input
                type="text"
                value={form.vlm_model_type || ''}
                onChange={(e) => setField('vlm_model_type', e.target.value)}
                className={inputClass}
              />
              <div className="flex flex-wrap gap-2 mt-2">
                {(PROVIDER_PRESETS.vlm.find(p => detectProvider('vlm') === p.key)?.models || []).map(m => (
                  <button key={m} onClick={() => setField('vlm_model_type', m)}
                    className={`px-3 py-1 rounded-full text-xs transition ${form.vlm_model_type === m ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                    {m}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <button
            onClick={() => handleTest('vlm')}
            disabled={testing.vlm}
            className="mt-4 flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {testing.vlm ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
            <span>测试 VLM 连通性</span>
          </button>
          <TestResult target="vlm" />
        </motion.section>

        {/* 抖音 cookies */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2">抖音 cookies（下载需要登录态）</h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            抖音下载要求登录态 Cookie（yt-dlp 提示 Fresh cookies are needed）。获取方式：登录 douyin.com 后
            用浏览器扩展导出 cookies.txt（Netscape 格式），粘贴到下方；也可用上方「一键读取浏览器 Cookie」自动获取。
          </p>
          <div>
            <label className={labelClass}>cookies.txt 内容（Netscape 格式）</label>
            <textarea
              value={form.douyin_cookies || ''}
              onChange={(e) => setField('douyin_cookies', e.target.value)}
              placeholder="# Netscape HTTP Cookie File&#10;.douyin.com	TRUE	/	TRUE	0	sessionid	..."
              rows={5}
              className={`${inputClass} font-mono text-xs`}
            />
          </div>
        </motion.section>

        {/* 一键读取浏览器 Cookie */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.115 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2">一键读取浏览器 Cookie（推荐）</h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            在本机浏览器登录过 B站 / YouTube / 元宝后，点击按钮即可自动读取登录 Cookie 并填入下方各卡片
            （仅读取这三个站的 cookie，本机处理，不上传）。macOS 首次读取 Chrome/Edge 会弹出钥匙串授权，
            请点「允许」；Windows 下 Chrome/Edge 127+ 受 App-Bound 加密限制可能失败，可改用 Firefox 或手动粘贴。
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={form.cookie_browser || ''}
              onChange={(e) => setField('cookie_browser', e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">自动检测（按序尝试）</option>
              <option value="chrome">Chrome</option>
              <option value="edge">Edge</option>
              <option value="firefox">Firefox</option>
              <option value="safari">Safari</option>
              <option value="brave">Brave</option>
              <option value="opera">Opera</option>
              <option value="vivaldi">Vivaldi</option>
            </select>
            <button
              onClick={handleImportCookies}
              disabled={cookieImport.loading}
              className="flex items-center space-x-2 px-5 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-bold shadow-md hover:shadow-lg disabled:opacity-50"
            >
              {cookieImport.loading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{cookieImport.loading ? '读取中…' : '一键读取'}</span>
            </button>
          </div>
          {cookieImport.message && (
            <p className={`mt-3 text-sm ${cookieImport.attempts.some(a => a.includes('✅')) ? 'text-green-700' : 'text-gray-600'}`}>
              {cookieImport.message}
            </p>
          )}
          {cookieImport.attempts.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-gray-400 cursor-pointer">读取明细</summary>
              <ul className="mt-1 space-y-0.5">
                {cookieImport.attempts.map((a, i) => (
                  <li key={i} className="text-xs text-gray-500 font-mono">{a}</li>
                ))}
              </ul>
            </details>
          )}
        </motion.section>

        {/* 微信视频号 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2">微信视频号（分享链接解析）</h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            视频号没有公开直链，下载需通过腾讯元宝接口解析：登录
            <span className="text-primary-600"> yuanbao.tencent.com </span>
            后按 F12 打开开发者工具 → Network → 任选请求复制 Cookie 填入下方
            （仅保存在本机 settings.json）。未配置时自动尝试公共解析服务，或使用本地工具下载后直接上传。
          </p>
          <div className="space-y-4">
            <div>
              <label className={labelClass}>元宝 Cookie（用于解析分享链接）</label>
              <input
                type="password"
                value={form.wechat_yuanbao_cookie || ''}
                onChange={(e) => setField('wechat_yuanbao_cookie', e.target.value)}
                placeholder="粘贴 yuanbao.tencent.com 的 Cookie"
                className={inputClass}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>自建解析服务 URL（可选）</label>
                <input
                  type="text"
                  value={form.wechat_resolver_url || ''}
                  onChange={(e) => setField('wechat_resolver_url', e.target.value)}
                  placeholder="https://your-worker.workers.dev"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>解析服务 Token（可选）</label>
                <input
                  type="password"
                  value={form.wechat_resolver_token || ''}
                  onChange={(e) => setField('wechat_resolver_token', e.target.value)}
                  placeholder="sph worker 的 ACCESS_CREDENTIAL"
                  className={inputClass}
                />
              </div>
            </div>
          </div>
        </motion.section>

        {/* B站账号 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.13 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2">B站账号（可选，解锁 AI 字幕）</h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            B站 AI 字幕轨仅对登录态可见：配置 SESSDATA 后「字幕笔记」功能可用（仅保存在本机）。
            获取：登录 bilibili.com → F12 → Application（应用）→ Cookies → 复制 SESSDATA 的值。
          </p>
          <div>
            <label className={labelClass}>SESSDATA</label>
            <input
              type="password"
              value={form.bilibili_sessdata || ''}
              onChange={(e) => setField('bilibili_sessdata', e.target.value)}
              placeholder="粘贴 SESSDATA 的值"
              className={inputClass}
            />
          </div>
        </motion.section>

        {/* YouTube cookies */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2">YouTube cookies（下载防 bot 检查）</h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            YouTube 对部分 IP 强制登录验证，未配置 cookies 时下载会失败。获取方法：登录 youtube.com 后，
            使用浏览器扩展（如 Get cookies.txt LOCALLY）导出 cookies.txt（Netscape 格式），
            把文件内容完整粘贴到下方（仅保存在本机 settings.json，脱敏显示）。也可通过环境变量
            YTDLP_COOKIES_FILE 指向 cookies 文件。
          </p>
          <div>
            <label className={labelClass}>cookies.txt 内容（Netscape 格式）</label>
            <textarea
              value={form.youtube_cookies || ''}
              onChange={(e) => setField('youtube_cookies', e.target.value)}
              placeholder="# Netscape HTTP Cookie File&#10;.youtube.com	TRUE	/	TRUE	0	KEY	VALUE..."
              rows={6}
              className={`${inputClass} font-mono text-xs`}
            />
          </div>
          <div className="mt-4 border-t border-gray-100 pt-4">
            <button
              onClick={handleYtCheck}
              disabled={ytCheck.loading}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg border border-gray-300 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              {ytCheck.loading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>下载环境自检</span>
            </button>
            {ytCheck.result && (
              <div className="mt-3 space-y-1.5 text-xs">
                {(() => {
                  const c = ytCheck.result.checks || {}
                  const items = [
                    [!!c.yt_dlp_version, `yt-dlp ${c.yt_dlp_version || '未安装'}`],
                    [!!c.cookies_configured, 'YouTube cookies 已配置'],
                    [!!c.pot_script, 'PO Token 脚本已安装'],
                    [!!c.node_available, `node 运行时${c.node_version ? ` ${c.node_version}` : ''}`],
                  ]
                  return items.map(([ok, text], i) => (
                    <p key={i} className={ok ? 'text-green-700' : 'text-gray-500'}>
                      {ok ? '✓' : '○'} {text}
                    </p>
                  ))
                })()}
                {(ytCheck.result.suggestions || []).length > 0 && (
                  <div className="pt-1 border-t border-gray-100">
                    <p className="font-semibold text-gray-700 mt-1">建议：</p>
                    {(ytCheck.result.suggestions || []).map((s, i) => (
                      <p key={i} className="text-gray-500 leading-relaxed">· {s}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.section>

        {/* 默认学习阶段 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center space-x-2">
            <GraduationCap className="w-5 h-5 text-primary-600" />
            <span>默认学习阶段</span>
          </h2>
          <div className="flex flex-wrap items-center gap-3">
            {(settings.education_levels || ['小学', '初中', '高中']).map(level => (
              <button
                key={level}
                onClick={() => setField('default_education_level', level)}
                className={`px-6 py-2.5 rounded-lg border-2 font-medium text-sm transition ${form.default_education_level === level ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
              >
                {level}
              </button>
            ))}
          </div>
          <p className="mt-3 text-sm text-gray-500">上传视频时也可单独选择学习阶段，此处为未指定时的默认值。</p>
        </motion.section>

        {/* 下载缓存 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-2 flex items-center space-x-2">
            <HardDriveDownload className="w-5 h-5 text-primary-600" />
            <span>下载缓存</span>
          </h2>
          <p className="text-xs text-gray-500 leading-relaxed mb-4">
            处理过的视频会缓存到本地，再次处理同一视频时直接复用、不再下载。
            下方是存储映射表（来源 → 本地文件）。
          </p>
          {cacheInfo ? (
            <>
              <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
                <span className="text-gray-600">已缓存 <b className="text-gray-900">{cacheInfo.stats.entries}</b> 个视频</span>
                <span className="text-gray-600">占用 <b className="text-gray-900">{cacheInfo.stats.total_size_human}</b></span>
                <span className="text-gray-600">已复用 <b className="text-primary-600">{cacheInfo.stats.reused_downloads}</b> 次</span>
                <button onClick={loadCache} className="ml-auto px-3 py-1.5 rounded-lg border border-gray-300 text-xs font-medium hover:bg-gray-50">刷新</button>
              </div>
              {cacheInfo.entries.length > 0 ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="max-h-64 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 text-gray-500 sticky top-0">
                        <tr>
                          <th className="text-left px-3 py-2 font-medium">视频</th>
                          <th className="text-left px-3 py-2 font-medium">平台</th>
                          <th className="text-right px-3 py-2 font-medium">大小</th>
                          <th className="text-right px-3 py-2 font-medium">复用</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cacheInfo.entries.map((e) => (
                          <tr key={e.key} className="border-t border-gray-100 hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-800 max-w-[280px] truncate" title={e.title}>{e.title || e.key}</td>
                            <td className="px-3 py-2 text-gray-500">{e.platform}</td>
                            <td className="px-3 py-2 text-right text-gray-500">{(e.size / 1024 / 1024).toFixed(1)}MB</td>
                            <td className="px-3 py-2 text-right text-primary-600">{e.hit_count} 次</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-gray-400">暂无缓存视频。</p>
              )}
              <p className="mt-3 text-xs text-gray-400">缓存目录：{cacheInfo.stats.cache_dir}</p>
            </>
          ) : (
            <p className="text-xs text-gray-400">加载中…</p>
          )}
        </motion.section>

        {/* 保存 */}
        <div className="flex items-center justify-end space-x-4 pb-12">
          {saveMessage && (
            <span className={`text-sm flex items-center space-x-1 ${saveMessage.ok ? 'text-green-600' : 'text-red-600'}`}>
              {saveMessage.ok ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              <span>{saveMessage.text}</span>
            </span>
          )}
          {error && <span className="text-sm text-red-600">{error}</span>}
          <motion.button
            onClick={handleSave}
            disabled={saving}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex items-center space-x-2 px-8 py-3 rounded-xl font-bold text-white bg-primary-600 hover:bg-primary-700 shadow-lg disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            <span>保存设置</span>
          </motion.button>
        </div>
      </main>
    </div>
  )
}

export default SettingsPage
