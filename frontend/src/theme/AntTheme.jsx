import { StyleProvider, px2remTransformer } from '@ant-design/cssinjs'
import { App as AntApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useTheme } from './themeContext'

const remTransformer = px2remTransformer({ rootValue: 16, mediaQuery: true })

export default function AntTheme({ children }) {
  const { theme } = useTheme()
  const coast = theme === 'coast'
  return <StyleProvider transformers={[remTransformer]}><ConfigProvider locale={zhCN} theme={{
    token: {
      colorPrimary: '#222832', colorText: '#242832',
      colorTextSecondary: coast ? '#79736e' : '#6b7889',
      colorBgContainer: coast ? '#fffdf9' : '#fbfdff',
      colorBgElevated: coast ? '#fffcf7' : '#fafdff',
      colorBorder: coast ? '#dfd9d2' : '#d8e2ec',
      borderRadius: 12, controlHeight: 46, fontSize: 14,
      fontFamily: '-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif',
      boxShadowSecondary: '0 .75rem 2.25rem rgba(35,40,48,.12)',
    },
    components: {
      Select: { optionSelectedBg: coast ? '#eee6dc' : '#e7eff7', optionSelectedColor: '#222832', optionHeight: 42 },
      Input: { activeShadow: '0 0 0 .1875rem rgba(80,105,130,.09)' },
    },
  }}><AntApp style={{height:'100%'}}>{children}</AntApp></ConfigProvider></StyleProvider>
}
