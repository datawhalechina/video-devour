import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Save, Radio, HardDriveDownload, KeyRound, CheckCircle, XCircle, Loader2, GraduationCap } from 'lucide-react'
import { getSettings, updateSettings, testSettings } from '../api/settingsService'

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
  const [error, setError] = useState(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await getSettings()
      setSettings(data)
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
      })
    } catch (err) {
      setError(`加载设置失败: ${err.message}`)
    }
  }

  const setField = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* 顶部导航 */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
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
              <p className="text-sm text-gray-500">本地 FunASR Paraformer，无 API 消耗，首次使用需下载模型</p>
            </button>
            <button
              onClick={() => setField('asr_mode', 'online')}
              className={`p-4 rounded-xl border-2 text-left transition ${form.asr_mode === 'online' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center space-x-2 mb-1">
                <Radio className="w-5 h-5 text-gray-700" />
                <span className="font-semibold text-gray-900">在线模式（云端 API）</span>
              </div>
              <p className="text-sm text-gray-500">DashScope 云端识别，零模型下载、启动即用，需填写 API Key</p>
            </button>
          </div>

          {form.asr_mode === 'online' && (
            <div className="mt-5 space-y-4">
              <div>
                <label className={labelClass}>云端识别提供商</label>
                <div className="flex items-center space-x-3">
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

        {/* 默认学习阶段 */}
        <motion.section
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6"
        >
          <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center space-x-2">
            <GraduationCap className="w-5 h-5 text-primary-600" />
            <span>默认学习阶段</span>
          </h2>
          <div className="flex items-center space-x-3">
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
            className="flex items-center space-x-2 px-8 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-primary-600 to-purple-600 shadow-lg disabled:opacity-50"
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
