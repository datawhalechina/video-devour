import { Slider } from 'antd'
import { Check } from 'lucide-react'
import { THEMES, useTheme } from './themeContext'

export default function ThemePicker() {
  const { theme, setTheme, saved, transparency, setTransparency } = useTheme()
  return <section className="theme-preferences" aria-labelledby="appearance-title">
    <h2 id="appearance-title">选择你的工作空间</h2>
    <p>两种氛围，同一份知识。切换即时生效，当前页面与输入保持不变。</p>
    <div className="theme-choice-grid">{THEMES.map(item => <button type="button" key={item.id} className={`theme-choice theme-choice-${item.id}`} aria-pressed={theme === item.id} onClick={() => setTheme(item.id)}>
      <span className="theme-preview" style={{ backgroundImage: `url(${item.image})` }} aria-hidden="true"><span className="theme-preview-shell"><i /><span><b /><em /><em /><em /></span></span></span>
      <span className="theme-choice-label"><strong>{item.name}</strong>{theme === item.id && <Check size={18} />}</span><small>{item.description}</small>
    </button>)}</div>
    <div className="glass-preferences">
      <div className="glass-preferences-heading"><h3 id="glass-transparency-label">玻璃透明度</h3><output>{transparency}%</output></div>
      <p>向右更通透，向左更清晰。统一调整背景与卡片，文字和图片保持不透明。</p>
      <Slider min={0} max={100} step={1} value={transparency} onChange={setTransparency} ariaLabelledByForHandle="glass-transparency-label" tooltip={{formatter: value => `${value}%`}} />
      <div className="glass-preferences-footer"><span>0% · 不透明</span><button type="button" onClick={() => setTransparency(60)}>恢复默认</button><span>100% · 全透明</span></div>
    </div>
    <p className="theme-save-note" role="status">{saved ? '主题选择已自动保存在此浏览器，无需点击保存设置。' : '主题已切换；当前浏览器无法保存偏好，刷新后可能恢复默认。'}</p>
  </section>
}
