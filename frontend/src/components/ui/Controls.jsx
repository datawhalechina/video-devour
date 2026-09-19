import { Select } from 'antd'
import { ChevronDown } from 'lucide-react'

// Portaled menus escape the scroll panes and remain keyboard accessible.
export function WorkspaceSelect({ className = '', ...props }) {
  return <Select {...props} className={`workspace-select ${className}`} suffixIcon={<ChevronDown size={16} />} />
}
