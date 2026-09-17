import { App, Input } from 'antd'

export default function useTextPrompt() {
  const { modal } = App.useApp()
  return title => new Promise(resolve => {
    let value = ''
    modal.confirm({
      title, icon: null, centered: true, okText: '插入', cancelText: '取消',
      content: <Input autoFocus aria-label={title} placeholder="https://…" onChange={event => { value = event.target.value }} />,
      onOk: () => resolve(value.trim() || null),
      onCancel: () => resolve(null),
    })
  })
}
