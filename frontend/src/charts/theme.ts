import { registerTheme } from 'echarts/core'
import { readDesignToken } from './week2'

let registered = false

/** All statistics panels share the same design-token-based ECharts theme. */
export function ensureChartTheme(read = readDesignToken): string {
  const name = 'bupt-guard'
  if (registered) return name
  const token = (key: string) => {
    const value = read(key).trim()
    if (!value) throw new Error(`设计令牌缺失：${key}`)
    return value
  }
  registerTheme(name, {
    color: ['danger', 'caution', 'warning', 'success'].map((state) =>
      token(`--state-${state}-solid`),
    ),
    backgroundColor: 'transparent',
    textStyle: { color: token('--text-secondary'), fontFamily: token('--font-family-base') },
    tooltip: {
      renderMode: 'html',
      backgroundColor: token('--bg-container'),
      borderColor: token('--border-base'),
      borderWidth: 1,
      confine: true,
      extraCssText: `font-variant-numeric: ${token('--font-variant-numeric')}; box-shadow: ${token('--shadow-lg')}`,
      textStyle: { color: token('--text-primary'), fontFamily: token('--font-family-mono') },
    },
  })
  registered = true
  return name
}
