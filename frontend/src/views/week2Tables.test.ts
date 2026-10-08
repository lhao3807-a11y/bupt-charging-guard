import { createPinia, setActivePinia } from 'pinia'
import type { Component } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http } from '@/api/http'
import { flush, mountView } from '@/test/memoryHost'
import RecordsView from './records/RecordsView.vue'
import VehicleView from './vehicle/VehicleView.vue'
import { ElMessage } from 'element-plus'

vi.mock('@/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.mocked(http.get).mockResolvedValue({ data: { items: [], total: 0, page: 1, size: 20 } })
})

describe('week two tables', () => {
  it.each([
    [VehicleView, '车辆列表'],
    [RecordsView, '违规记录列表'],
  ])('gives the %s table an accessible name', async (view: Component, name: string) => {
    const mounted = mountView(view)
    await flush()
    expect(mounted.all('table')[0]?.props['aria-label']).toBe(name)
    mounted.app.unmount()
  })

  it('explains a demo reminder without developer jargon', async () => {
    const notify = vi.spyOn(ElMessage, 'success').mockImplementation(vi.fn())
    vi.mocked(http.get).mockResolvedValue({
      data: {
        items: [{
          id: 7, plate: '京AD12345', vtype: '新能源', pile_id: 'PILE-001',
          rule_hit: 3, occur_time: '2026-10-01T10:00:00', notify_status: '未提醒',
        }],
        total: 1, page: 1, size: 20,
      },
    })
    vi.mocked(http.post).mockResolvedValue({ data: { notify_status: '已提醒' } })
    const mounted = mountView(RecordsView)
    await flush()
    await mounted.click('发送提醒')
    await flush()
    expect(http.post).toHaveBeenCalled()
    expect(notify).toHaveBeenCalledWith('已向 京AD12345 发送提醒（演示环境，未真实下发）')
    mounted.app.unmount()
    notify.mockRestore()
  })

  it('gives the full timestamp column enough width for one line', async () => {
    vi.mocked(http.get).mockResolvedValue({
      data: {
        items: [{ plate: '京AD12345', vtype: '新能源', owner: '张三', phone: null, created_at: '2026-10-01T10:00:00' }],
        total: 1, page: 1, size: 20,
      },
    })
    const mounted = mountView(VehicleView)
    await flush()
    const columns = mounted.all('column')
    const timestamp = columns.find((column) => mounted.text(column).startsWith('录入时间'))
    expect(Number(timestamp?.props.width)).toBeGreaterThanOrEqual(210)
    expect(mounted.all('span', timestamp).find((cell) => mounted.text(cell).includes('2026-10-01'))?.props.style).toMatchObject({ 'white-space': 'nowrap' })
    mounted.app.unmount()
  })
})
