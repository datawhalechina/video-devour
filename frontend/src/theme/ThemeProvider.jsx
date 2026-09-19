import { useLayoutEffect, useState } from 'react'
import { THEMES, ThemeContext } from './themeContext'

const GLASS_KEY = 'videodevour-glass-transparency'
const normalizeGlass = value => value !== null && value !== '' && Number.isFinite(Number(value)) ? Math.max(0, Math.min(100, Number(value))) : 60
const readGlass = () => { try { return normalizeGlass(localStorage.getItem(GLASS_KEY)) } catch { return 60 } }

const STORAGE_KEY = 'videodevour-ui-theme'
const validTheme = value => THEMES.some(theme => theme.id === value)
const readTheme = () => {
  try { const value = localStorage.getItem(STORAGE_KEY); return validTheme(value) ? value : 'lake' }
  catch { return 'lake' }
}
export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(readTheme)
  const [transparency, setTransparencyState] = useState(readGlass)
  const [glassSaved, setGlassSaved] = useState(true)
  const [saved, setSaved] = useState(true)
  useLayoutEffect(() => { document.documentElement.dataset.uiTheme = theme }, [theme])
  useLayoutEffect(() => {
    const style = document.documentElement.style
    style.setProperty('--glass-alpha', String(1 - transparency / 100))
    style.setProperty('--panel-alpha', String(1 - transparency / 100))
    style.setProperty('--caption-alpha', String(1 - transparency / 100))
  }, [transparency])
  const setTransparency = value => {
    const next = normalizeGlass(value)
    setTransparencyState(next)
    try { localStorage.setItem(GLASS_KEY, String(next)); setGlassSaved(true) } catch { setGlassSaved(false) }
  }
  useLayoutEffect(() => {
    const sync = event => {
      if (event.key === GLASS_KEY) { setTransparencyState(normalizeGlass(event.newValue)); setGlassSaved(true) }
      if (event.key === STORAGE_KEY) { setThemeState(validTheme(event.newValue) ? event.newValue : 'lake'); setSaved(true) }
    }
    window.addEventListener('storage', sync)
    return () => window.removeEventListener('storage', sync)
  }, [])
  const setTheme = next => {
    if (!validTheme(next)) return
    setThemeState(next)
    try { localStorage.setItem(STORAGE_KEY, next); setSaved(true) } catch { setSaved(false) }
  }
  return <ThemeContext.Provider value={{ theme, setTheme, saved, transparency, setTransparency, glassSaved }}>{children}</ThemeContext.Provider>
}
