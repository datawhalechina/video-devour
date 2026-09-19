import { useTheme } from '../../theme/themeContext'
import { useState } from 'react'
const covers = { lake: ['/lake/architecture.png', '/lake/ocean.png', '/lake/mountain.png'], coast: ['/lake/architecture.png', '/coast/reading.png', '/coast/sculpture.png'] }
export default function MediaCover({ video, index = 0, className = '' }) {
  const { theme } = useTheme()
  const [failedSource, setFailedSource] = useState(null)
  const source = video?.thumbnail_url || video?.thumbnail
  const fallback = covers[theme][index % covers[theme].length]
  const src = source && source !== failedSource ? source : fallback
  return <img className={`lake-cover ${className}`} src={src} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={() => { if (source && src === source) setFailedSource(source) }} />
}
