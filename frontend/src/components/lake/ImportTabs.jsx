import { NavLink } from 'react-router-dom'
import { Link2, Upload } from 'lucide-react'
export default function ImportTabs() {
  return <nav className="lake-import-tabs" aria-label="视频来源"><NavLink to="/link"><Link2 size={17} />视频链接</NavLink><NavLink to="/upload"><Upload size={17} />本地上传</NavLink></nav>
}
