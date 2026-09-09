import { useState } from 'react'
import { Brain, Network, Smartphone } from 'lucide-react'

// 附加产物选项：默认全不勾选，勾选后任务完成时自动生成；选择记忆在 localStorage
const STORAGE_KEY = 'vd_extras'

const EXTRA_OPTIONS = [
  { key: 'mindmap', label: '思维导图', icon: Brain },
  { key: 'graph', label: '知识图谱', icon: Network },
  { key: 'card', label: '学习卡片', icon: Smartphone },
]

export function getSelectedExtras() {
  try {
    const v = JSON.parse(localStorage.getItem(STORAGE_KEY))
    return Array.isArray(v) ? v.filter(k => EXTRA_OPTIONS.some(o => o.key === k)) : []
  } catch {
    return []
  }
}

export default function ExtrasPicker() {
  const [selected, setSelected] = useState(getSelectedExtras)

  const toggle = (key) => {
    setSelected(prev => {
      const next = prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)) } catch { /* ignore */ }
      return next
    })
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {EXTRA_OPTIONS.map(({ key, label, icon: Icon }) => {
        const active = selected.includes(key)
        return (
          <button
            key={key}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(key)}
            title={active ? '点击取消，完成后不生成' : '点击勾选，报告完成后自动生成'}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg border-2 text-sm font-medium transition ${
              active
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-gray-200 text-gray-500 hover:border-gray-300'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span>{label}</span>
            <span className={`text-xs ${active ? 'text-primary-500' : 'text-gray-300'}`}>
              {active ? '✓' : '+'}
            </span>
          </button>
        )
      })}
    </div>
  )
}
