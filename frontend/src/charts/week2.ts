import type { EChartsOption } from 'echarts'
import { RULE_HIT_LABEL } from '@/constants/status'
import type { StatisticsData } from '@/data/week2'

export const RULE_ORDER = [1, 2, 3] as const
export function violationTotal(data: StatisticsData): number {
  return RULE_ORDER.reduce((sum, rule) => sum + data.counts[rule], 0)
}
export function readDesignToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
export function buildStatisticsCharts(data: StatisticsData, read = readDesignToken): {
  distribution: EChartsOption; trend: EChartsOption; share: EChartsOption
} | null {
  if (violationTotal(data) === 0) return null
  const token = (name: string) => {
    const value = read(name).trim()
    if (!value) throw new Error(`设计令牌缺失：${name}`)
    return value
  }
  const palette = ['danger', 'caution', 'warning', 'success'].map((state) => token(`--state-${state}-solid`))
  const base: EChartsOption = {
    color: palette,
    backgroundColor: 'transparent',
    textStyle: { color: token('--text-secondary'), fontFamily: token('--font-family-base') },
    tooltip: { renderMode: 'richText', backgroundColor: token('--bg-container'), borderColor: token('--border-base'), textStyle: { color: token('--text-primary') } },
    legend: { bottom: 0, textStyle: { color: token('--text-secondary') } },
    grid: { left: 8, right: 8, top: 24, bottom: 48, containLabel: true },
  }
  const axis = {
    axisLabel: { color: token('--text-tertiary'), fontFamily: token('--font-family-mono') },
    axisTick: { show: false },
    axisLine: { lineStyle: { color: token('--border-base') } },
  }
  const valueAxis = { ...axis, type: 'value' as const, minInterval: 1, splitLine: { lineStyle: { color: token('--border-light'), type: 'dashed' as const } } }
  return {
    distribution: {
      ...base,
      xAxis: { ...axis, type: 'category', data: RULE_ORDER.map((rule) => RULE_HIT_LABEL[rule]) },
      yAxis: valueAxis,
      series: [{ type: 'bar', barMaxWidth: 48, label: { show: true, position: 'top', color: token('--text-secondary') }, data: RULE_ORDER.map((rule, index) => ({ value: data.counts[rule], itemStyle: { color: palette[index], borderRadius: [4, 4, 0, 0] } })) }],
    },
    trend: {
      ...base,
      tooltip: { ...base.tooltip, trigger: 'axis' },
      xAxis: { ...axis, type: 'category', data: data.trend.map((point) => point.date), boundaryGap: false },
      yAxis: valueAxis,
      series: RULE_ORDER.map((rule, index) => ({ name: RULE_HIT_LABEL[rule], type: 'line', showSymbol: false, itemStyle: { color: palette[index] }, data: data.trend.map((point) => point.counts[rule]) })),
    },
    share: {
      ...base,
      color: ['--brand-primary', '--brand-primary-light-3', '--brand-primary-light-5', '--brand-primary-light-7'].map(token),
      series: [{ type: 'pie', radius: ['50%', '70%'], center: ['50%', '45%'], label: { color: token('--text-secondary'), formatter: '{b}: {c}' }, data: data.piles.map((pile) => ({ name: pile.pileId ?? '未关联桩', value: pile.count })) }],
    },
  }
}
