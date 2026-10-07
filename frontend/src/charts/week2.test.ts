import { describe, expect, it } from 'vitest'
import { buildStatisticsCharts, violationTotal } from './week2'
import type { StatisticsData } from '@/data/week2'

const data: StatisticsData = {
  counts: { 1: 2, 2: 3, 3: 4 },
  trend: [{ date: '2026-10-04', counts: { 1: 2, 2: 3, 3: 4 } }],
  piles: [
    { pileId: 'PILE-001', count: 5 },
    { pileId: null, count: 4 },
  ],
}
const token = (name: string) => `token:${name}`
describe('statistics chart configuration', () => {
  it('counts violations without inventing a separate summary total', () => {
    expect(violationTotal(data)).toBe(9)
  })
  it('creates bar and line series in danger, caution, warning order using design tokens', () => {
    const charts = buildStatisticsCharts(data, token)!
    expect(charts.distribution.color).toBeUndefined()
    expect(charts.distribution.xAxis).toMatchObject({
      data: ['燃油车占位', '异常占位', '充满未移车'],
    })
    expect(charts.distribution.series).toMatchObject([
      {
        type: 'bar',
        data: [
          { value: 2, itemStyle: { color: 'token:--state-danger-solid' } },
          { value: 3, itemStyle: { color: 'token:--state-caution-solid' } },
          { value: 4, itemStyle: { color: 'token:--state-warning-solid' } },
        ],
      },
    ])
    expect(charts.trend.series).toMatchObject([
      { name: '燃油车占位', type: 'line', data: [2] },
      { name: '异常占位', type: 'line', data: [3] },
      { name: '充满未移车', type: 'line', data: [4] },
    ])
  })
  it('uses the brand palette for pile shares and keeps unbound records visible', () => {
    const charts = buildStatisticsCharts(data, token)!
    expect(charts.share.color).toBeUndefined()
    expect(charts.share.series).toMatchObject([
      {
        type: 'pie',
        radius: ['50%', '70%'],
        data: [
          { name: 'PILE-001', value: 5, itemStyle: { color: 'token:--brand-primary' } },
          { name: '未关联桩', value: 4, itemStyle: { color: 'token:--brand-primary-light-3' } },
        ],
      },
    ])
    expect(charts.share.tooltip).toMatchObject({ renderMode: 'html' })
  })
  it('keeps tooltip numbers readable and inside the chart panel', () => {
    const charts = buildStatisticsCharts(data, token)!
    for (const option of Object.values(charts)) {
      expect(option.tooltip).toMatchObject({
        confine: true,
        extraCssText: expect.stringContaining('font-variant-numeric: token:--font-variant-numeric'),
        textStyle: { fontFamily: 'token:--font-family-mono' },
      })
    }
  })
  it('returns no charts when real data contains no violations', () => {
    expect(
      buildStatisticsCharts({ counts: { 1: 0, 2: 0, 3: 0 }, trend: [], piles: [] }, token),
    ).toBeNull()
  })
  it('does not fall back to hardcoded colors when a required token is missing', () => {
    expect(() => buildStatisticsCharts(data, () => '')).toThrow('设计令牌缺失')
  })
  it('leaves the source data untouched while building all three chart options', () => {
    const before = JSON.stringify(data)
    buildStatisticsCharts(data, token)
    expect(JSON.stringify(data)).toBe(before)
  })
})
