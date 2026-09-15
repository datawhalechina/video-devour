import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Settings, X } from 'lucide-react'

/**
 * 配置引导（小白友好）：需要 LLM/VLM/ASR 的操作在点击时先检查配置。
 *
 * 未配置时不静默失败，而是弹出引导弹窗并可直接跳到「偏好设置」，
 * 避免用户点了按钮只看到报错却不知道去哪配。
 *
 * 用法：
 *   const { guardConfig } = useConfigGate()
 *   if (!(await guardConfig(['llm', 'vlm']))) return
 */
const ConfigGateContext = createContext(null)

// 每项能力的中文说明（缺失时展示，告诉用户为什么必须配）
const NEED_META = {
  llm: { label: 'LLM（大语言模型）', why: '用于生成大纲、报告与各类改写内容' },
  vlm: { label: 'VLM（视觉语言模型）', why: '用于挑选每个章节最具代表性的关键帧配图' },
  asr: { label: '在线语音识别', why: '用于把视频语音转写为文字（默认走云端识别）' },
}

const CAP_TTL = 30 * 1000      // 能力查询缓存 30 秒，避免每次点击都请求

let cache = { at: 0, data: null }

async function fetchCapabilities(force = false) {
  if (!force && cache.data && Date.now() - cache.at < CAP_TTL) return cache.data
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error('无法获取服务状态')
  const data = await res.json()
  cache = { at: Date.now(), data: data.capabilities || {} }
  return cache.data
}

/** 返回缺失的能力键（[] 表示都已配置） */
function missingFrom(caps, needs) {
  return needs.filter((key) => {
    const cap = caps[key] || {}
    if (key === 'asr') {
      // 离线模式未预加载属正常状态（任务执行时按需加载），不视为缺失
      return cap.mode !== 'offline' && cap.state !== 'available'
    }
    return cap.state !== 'available'
  })
}

export function ConfigGateProvider({ children }) {
  const navigate = useNavigate()
  const [missing, setMissing] = useState(null)
  const resolver = useRef(null)

  useEffect(() => () => { resolver.current = null }, [])

  const settle = useCallback((ok) => {
    setMissing(null)
    const fn = resolver.current
    resolver.current = null
    if (fn) fn(ok)
  }, [])

  const guardConfig = useCallback(async (needs) => {
    const required = (needs || []).filter((k) => NEED_META[k])
    if (!required.length) return true
    try {
      const caps = await fetchCapabilities()
      const lack = missingFrom(caps, required)
      if (!lack.length) return true
      await new Promise((resolve) => { resolver.current = resolve; setMissing(lack) })
      return false          // 已引导用户去配置，本次操作不继续
    } catch {
      return true           // 服务状态查不到时不阻塞用户（后端会给出具体报错）
    }
  }, [])

  const value = { guardConfig, invalidate: () => { cache = { at: 0, data: null } } }

  return (
    <ConfigGateContext.Provider value={value}>
      {children}
      {missing && (
        <div className="fixed inset-0 z-[300] bg-black/60 flex items-center justify-center p-4"
             onClick={() => settle(false)}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start gap-3 px-5 pt-5 pb-4">
              <span className="flex-shrink-0 w-9 h-9 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center">
                <AlertTriangle size={18} />
              </span>
              <div className="flex-1">
                <h3 className="text-base font-bold text-gray-900">先配置模型再使用</h3>
                <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                  这个功能需要调用 AI 模型，当前还缺少以下配置。填好之后回来点一次即可。
                </p>
              </div>
              <button onClick={() => settle(false)} className="p-1 rounded-lg text-gray-400 hover:bg-gray-100">
                <X size={16} />
              </button>
            </div>
            <ul className="px-5 pb-4 space-y-2">
              {missing.map((key) => (
                <li key={key} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0" />
                  <span><strong className="text-gray-800">{NEED_META[key].label}</strong>
                    <span className="text-gray-500"> — {NEED_META[key].why}</span></span>
                </li>
              ))}
            </ul>
            <div className="px-5 pb-5 flex items-center gap-2">
              <button onClick={() => { settle(false); navigate('/settings', { state: { from: 'config-gate' } }) }}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary-600 text-white text-sm font-bold hover:bg-primary-700">
                <Settings size={15} /> 前往偏好设置 <ArrowRight size={14} />
              </button>
              <button onClick={() => settle(false)}
                      className="px-4 py-2.5 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50">
                稍后再说
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfigGateContext.Provider>
  )
}

export function useConfigGate() {
  const ctx = useContext(ConfigGateContext)
  // Provider 之外（如独立测试页面）调用时降级为「不拦截」
  return ctx || { guardConfig: async () => true, invalidate: () => {} }
}

export default ConfigGateProvider
