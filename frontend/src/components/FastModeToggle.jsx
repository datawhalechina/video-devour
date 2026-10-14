import { useState } from 'react'
import { Zap } from 'lucide-react'

// 极速模式：跳过抽帧与 VLM 画面分析，ASR 后直接出纯文字报告（更快、不加图）。
// 选择记忆在 localStorage（与附加产物 ExtrasPicker 同款模式）。
const STORAGE_KEY = 'vd_fast_mode'

export function getFastMode() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export default function FastModeToggle({ onChange }) {
  const [enabled, setEnabled] = useState(getFastMode)

  const toggle = () => {
    setEnabled(prev => {
      const next = !prev
      try { localStorage.setItem(STORAGE_KEY, next ? '1' : '0') } catch { /* ignore */ }
      onChange && onChange(next)
      return next
    })
  }

  return (
    <button
      type="button"
      aria-pressed={enabled}
      onClick={toggle}
      title={enabled
        ? '极速模式已开启：不抽帧、不加图，ASR 后直接出纯文字报告。点击关闭'
        : '开启极速模式：跳过画面分析（抽帧/VLM），只做 ASR 转写并出纯文字报告，速度更快'}
      className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg border-2 text-sm font-medium transition ${
        enabled
          ? 'border-amber-400 bg-amber-50 text-amber-600'
          : 'border-gray-200 text-gray-500 hover:border-gray-300'
      }`}
    >
      <Zap className="w-4 h-4" />
      <span>极速模式</span>
      <span className={`text-xs ${enabled ? 'text-amber-500' : 'text-gray-300'}`}>
        {enabled ? '✓' : '+'}
      </span>
    </button>
  )
}
