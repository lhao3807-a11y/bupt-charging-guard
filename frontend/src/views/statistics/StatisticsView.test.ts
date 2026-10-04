import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mountView, flush } from '@/test/memoryHost'
import StatisticsView from './StatisticsView.vue'
import type { StatisticsData } from '@/data/week2'

vi.mock('vue-echarts', () => ({ default: defineComponent({
  name: 'ChartBoundary',
  props: { option: { type: Object, required: true }, autoresize: Boolean },
  setup(props) { return () => h('chart', { autoresize: props.autoresize }, JSON.stringify(props.option.series)) },
}) }))
const unmounts: Array<() => void> = []
const data: StatisticsData = { counts: { 1: 2, 2: 3, 3: 4 }, trend: [{ date: '2026-10-04', counts: { 1: 2, 2: 3, 3: 4 } }], piles: [{ pileId: 'PILE-001', count: 9 }] }
function mount(source?: Parameters<typeof mountView>[1]) {
  const view = mountView(StatisticsView, source)
  unmounts.push(() => view.app.unmount())
  return view
}
beforeEach(() => {
  vi.stubGlobal('document', { documentElement: {} })
  vi.stubGlobal('getComputedStyle', () => ({ getPropertyValue: (name: string) => name.includes('font') ? 'sans-serif' : 'rgb(22, 104, 227)' }))
})
afterEach(() => { unmounts.splice(0).forEach((unmount) => unmount()); vi.unstubAllGlobals() })
describe('statistics view', () => {
  it('keeps unavailable data distinct from an empty report', async () => {
    const view = mount()
    await flush()
    expect(view.text()).toContain('统计数据待接入')
    expect(view.all('chart')).toHaveLength(0)
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['—', '—', '—', '—'])
  })
  it('renders all three chart containers with resize and readable summaries', async () => {
    const view = mount({ loadStatistics: vi.fn().mockResolvedValue(data) })
    await flush()
    expect(view.all('chart')).toHaveLength(3)
    expect(view.all('chart').every((el) => el.props.autoresize === true)).toBe(true)
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['9', '2', '3', '4'])
    expect(view.text()).toContain('燃油占位 2 条，异常占位 3 条，充满未移车 4 条')
  })
  it('requests the selected period and avoids chart axes when the result is empty', async () => {
    const read = vi.fn().mockResolvedValueOnce(data).mockResolvedValueOnce({ counts: { 1: 0, 2: 0, 3: 0 }, trend: [], piles: [] })
    const view = mount({ loadStatistics: read })
    await flush()
    ;(view.all('select')[0]!.props.onChange as (value: number) => void)(30)
    await flush()
    expect(read).toHaveBeenLastCalledWith(30)
    expect(view.text()).toContain('所选时段暂无违规记录')
    expect(view.all('chart')).toHaveLength(0)
  })
  it('shows a retryable read failure without reporting zero violations', async () => {
    const view = mount({ loadStatistics: vi.fn().mockRejectedValue(new Error('offline')) })
    await flush()
    expect(view.text()).toContain('统计数据加载失败')
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['—', '—', '—', '—'])
    expect(view.button('刷新').props.disabled).toBe(false)
  })
})
