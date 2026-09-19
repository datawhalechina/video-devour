import { createContext, useContext } from 'react'
export const THEMES = [
  { id: 'lake', name: '湖蓝晨光', description: '顶部导航 · 清爽通透', image: '/lake/background.png' },
  { id: 'coast', name: '海岸暖光', description: '侧边导航 · 温暖沉浸', image: '/coast/background.png' },
]

export const ThemeContext = createContext(null)
export const useTheme = () => useContext(ThemeContext)
