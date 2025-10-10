import { useMemo } from 'react'
import { AlertCircle, Info, AlertTriangle, CheckCircle, MessageSquare } from 'lucide-react'

/**
 * 提示框块组件
 */
function CalloutBlock({ attributes, children, element }) {
  const { calloutType = 'info' } = element

  const config = useMemo(() => {
    switch (calloutType) {
      case 'warning':
        return {
          icon: AlertTriangle,
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-400',
          iconColor: 'text-yellow-600',
          textColor: 'text-yellow-900',
        }
      case 'error':
        return {
          icon: AlertCircle,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-400',
          iconColor: 'text-red-600',
          textColor: 'text-red-900',
        }
      case 'success':
        return {
          icon: CheckCircle,
          bgColor: 'bg-green-50',
          borderColor: 'border-green-400',
          iconColor: 'text-green-600',
          textColor: 'text-green-900',
        }
      case 'quote':
        return {
          icon: MessageSquare,
          bgColor: 'bg-purple-50',
          borderColor: 'border-purple-400',
          iconColor: 'text-purple-600',
          textColor: 'text-purple-900',
        }
      default: // info
        return {
          icon: Info,
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-400',
          iconColor: 'text-blue-600',
          textColor: 'text-blue-900',
        }
    }
  }, [calloutType])

  const Icon = config.icon

  return (
    <div
      {...attributes}
      className={`flex items-start space-x-3 p-4 my-4 rounded-lg border-l-4 ${config.bgColor} ${config.borderColor}`}
    >
      <div contentEditable={false} className="flex-shrink-0 pt-0.5">
        <Icon className={`w-5 h-5 ${config.iconColor}`} />
      </div>
      <div className={`flex-1 text-base leading-relaxed ${config.textColor}`}>
        {children}
      </div>
    </div>
  )
}

export default CalloutBlock

