import { afterEach, describe, expect, it, vi } from 'vitest'
import { mountView, flush } from '@/test/memoryHost'
import type { ChargingPile } from '@/types/contract'
import PilesView from './PilesView.vue'

const unmounts: Array<() => void> = []
function mount(source?: Parameters<typeof mountView>[1]) {
  const view = mountView(PilesView, source)
  unmounts.push(() => view.app.unmount())
  return view
}
afterEach(() => unmounts.splice(0).forEach((unmount) => unmount()))
const piles: ChargingPile[] = [
  { pile_id: 'PILE-001', status: '空闲', bound_plate: '京AD12345', start_time: null, end_time: null },
  { pile_id: 'PILE-002', status: '充电中', bound_plate: '京AD24680', start_time: '2026-10-04T10:00:00', end_time: null },
  { pile_id: 'PILE-003', status: '已充满', bound_plate: null, start_time: null, end_time: null },
]
describe('charging piles view', () => {
  it('shows waiting rather than zero counts when the backend is not connected', async () => {
    const view = mount()
    await flush()
    expect(view.text()).toContain('待接入')
    expect(view.all('article')).toHaveLength(0)
    expect(view.button('刷新').props.disabled).toBe(true)
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['—', '—', '—'])
  })
  it('renders three states and preserves a bound plate on an idle pile', async () => {
    const view = mount({ loadPiles: vi.fn().mockResolvedValue(piles) })
    await flush()
    expect(view.all('article')).toHaveLength(3)
    expect(view.text()).toContain('京AD12345')
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['1', '1', '1'])
    expect(view.text()).not.toContain('待接入')
    await view.click('列表视图')
    expect(view.all('article')).toHaveLength(0)
    expect(view.all('table')).toHaveLength(1)
    expect(view.text()).toContain('桩 ID')
    expect(view.text()).toContain('结束时间')
    expect(view.text()).toContain('京AD12345')
  })
  it('passes the selected state to its read boundary and uses a real empty state', async () => {
    const read = vi.fn().mockResolvedValueOnce(piles).mockResolvedValueOnce([])
    const view = mount({ loadPiles: read })
    await flush()
    ;(view.all('select')[0]!.props.onChange as (value: string) => void)('已充满')
    await flush()
    expect(read).toHaveBeenLastCalledWith('已充满')
    expect(view.text()).toContain('没有符合状态筛选的充电桩')
    expect(view.all('strong').map((el) => view.text(el))).toEqual(['0', '0', '0'])
  })
  it('shows a loading skeleton and then a retryable failure, without stale cards', async () => {
    let reject!: (cause: Error) => void
    const view = mount({ loadPiles: () => new Promise((_resolve, fail) => { reject = fail }) })
    await flush()
    expect(view.all('section').some((el) => el.props['aria-label'] === '充电桩加载中')).toBe(true)
    reject(new Error('offline'))
    await flush()
    expect(view.text()).toContain('充电桩加载失败')
    expect(view.button('刷新').props.disabled).toBe(false)
    expect(view.all('article')).toHaveLength(0)
  })
})
