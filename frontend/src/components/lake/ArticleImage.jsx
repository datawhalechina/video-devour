import { useState } from 'react'
import { ImageOff } from 'lucide-react'

export default function ArticleImage({ src, alt, ...props }) {
  const [failedSrc, setFailedSrc] = useState(null)
  if (failedSrc === src) return <span className="lake-missing-image" role="img" aria-label={`${alt || '文章配图'}，文件不可用`}><ImageOff size={22} /><span>{alt || '文章配图'}<small>原始图片文件不可用</small></span></span>
  return <img {...props} src={src} alt={alt || ''} loading="lazy" onError={() => setFailedSrc(src)} />
}
