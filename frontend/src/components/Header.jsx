import { motion } from 'framer-motion'
import { Video, Upload, History, FileText } from 'lucide-react'

function Header({ currentView, onNavigate, onBackToUpload }) {
  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-5 max-w-7xl">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={onBackToUpload}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Video className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">VideoDevour</h1>
              <p className="text-xs text-gray-500">智能视频分析工具</p>
            </div>
          </motion.div>

          {/* Navigation */}
          <nav className="flex items-center space-x-3">
            <NavButton
              icon={<Upload className="w-5 h-5" />}
              label="上传视频"
              active={currentView === 'upload'}
              onClick={() => onNavigate('upload')}
            />
            <NavButton
              icon={<History className="w-5 h-5" />}
              label="历史记录"
              active={currentView === 'history'}
              onClick={() => onNavigate('history')}
            />
          </nav>
        </div>
      </div>
    </header>
  )
}

function NavButton({ icon, label, active, onClick }) {
  return (
    <motion.button
      onClick={onClick}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
        active
          ? 'bg-primary-500 text-white shadow-md'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </motion.button>
  )
}

export default Header

