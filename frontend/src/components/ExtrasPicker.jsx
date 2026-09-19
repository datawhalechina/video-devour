import { Checkbox } from 'antd'
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

  return <div className="workspace-extras">{EXTRA_OPTIONS.map(({key,label,icon:Icon}) => <Checkbox key={key} checked={selected.includes(key)} onChange={() => toggle(key)}><Icon size={18}/><span>{label}</span></Checkbox>)}</div>
}
