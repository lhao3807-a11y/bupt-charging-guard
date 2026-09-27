import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { http } from '@/api/http'
import { useRecordsStore } from './records'
import { useVehicleStore } from './vehicle'

vi.mock('@/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

const vehicle = {
  plate: '京AD12345',
  vtype: '新能源' as const,
  owner: null,
  phone: null,
  created_at: '2026-09-01T09:00:00',
}
const page = (items: unknown[] = [], total = items.length, current = 1) => ({
  data: { items, total, page: current, size: 20 },
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.resetAllMocks()
  vi.mocked(http.get).mockResolvedValue(page())
})

describe('records server queries', () => {
  it('submits every filter, preserves rule zero and date-only bounds across pages', async () => {
    const store = useRecordsStore()
    Object.assign(store.filters, {
      plate: ' 京A ',
      vtype: '新能源',
      pile_id: ' PILE-001 ',
      rule_hit: 0,
      notify_status: '未提醒',
      timeRange: ['2026-09-19', '2026-09-19'],
    })
    await store.search()
    store.filters.plate = '未提交的新条件'
    await store.changePage(2, 20)
    expect(http.get).toHaveBeenLastCalledWith('/api/records', {
      params: {
        page: 2,
        size: 20,
        plate: '京A',
        vtype: '新能源',
        pile_id: 'PILE-001',
        rule_hit: 0,
        notify_status: '未提醒',
        start_time: '2026-09-19',
        end_time: '2026-09-19',
      },
    })
  })

  it('uses server rows and filtered total without filtering the current page again', async () => {
    const row = { id: 42, plate: '京A12345', rule_hit: 3 }
    vi.mocked(http.get).mockResolvedValue(page([row], 45))
    const store = useRecordsStore()
    store.filters.plate = '京A'
    await store.search()
    store.filters.plate = '尚未查询'
    expect(store.filteredItems).toEqual([row])
    expect(store.total).toBe(45)
  })

  it('omits Element Plus cleared enum values and resets page and filters', async () => {
    const store = useRecordsStore()
    Object.assign(store.filters, { rule_hit: '', notify_status: '', vtype: '' })
    await store.search()
    expect(http.get).toHaveBeenLastCalledWith('/api/records', { params: { page: 1, size: 20 } })
    store.filters.plate = '京A'
    await store.search()
    store.resetFilters()
    await store.search()
    expect(http.get).toHaveBeenLastCalledWith('/api/records', { params: { page: 1, size: 20 } })
    expect(store.hasFilters).toBe(false)
  })

  it('ignores an older response arriving after a newer query', async () => {
    let resolveOld!: (value: ReturnType<typeof page>) => void
    vi.mocked(http.get).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve
        }),
    )
    const store = useRecordsStore()
    const old = store.load()
    vi.mocked(http.get).mockResolvedValue(page([{ id: 2 }], 1))
    await store.search()
    resolveOld(page([{ id: 1 }], 100))
    await old
    expect(store.rawItems).toEqual([{ id: 2 }])
    expect(store.total).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('clears stale rows and reports a failed query', async () => {
    const store = useRecordsStore()
    vi.mocked(http.get).mockRejectedValue(new Error('offline'))
    await expect(store.load()).rejects.toThrow('offline')
    expect(store.loading).toBe(false)
    expect(store.error).toBe(true)
  })

  it('refreshes filtered counts after notifying the last record on a page', async () => {
    const store = useRecordsStore()
    store.page = 2
    vi.mocked(http.post).mockResolvedValue({ data: { notify_status: '已提醒' } })
    vi.mocked(http.get)
      .mockResolvedValueOnce(page([], 20, 2))
      .mockResolvedValueOnce(page([{ id: 1 }], 20))
    await store.sendNotify(42)
    expect(http.post).toHaveBeenCalledWith('/api/notify', { id: 42, notify_status: '已提醒' })
    expect(store.page).toBe(1)
    expect(store.total).toBe(20)
  })
})

describe('vehicles persisted by API', () => {
  it('loads server pages and keeps applied filters while editing the form', async () => {
    const store = useVehicleStore()
    Object.assign(store.filters, { plate: ' 京A ', owner: ' 吕浩 ', vtype: '新能源' })
    vi.mocked(http.get).mockResolvedValue(page([vehicle], 41))
    await store.search()
    store.filters.owner = '草稿'
    await store.changePage(2, 20)
    expect(http.get).toHaveBeenLastCalledWith('/api/vehicles', {
      params: { page: 2, size: 20, plate: '京A', owner: '吕浩', vtype: '新能源' },
    })
    expect(store.items).toEqual([vehicle])
    expect(store.total).toBe(41)
  })

  it('creates on the server without manufacturing a timestamp', async () => {
    const store = useVehicleStore()
    const payload = {
      plate: vehicle.plate,
      vtype: vehicle.vtype,
      owner: '吕浩',
      phone: '13800000002',
    }
    vi.mocked(http.post).mockResolvedValue({ data: vehicle })
    await store.create(payload)
    expect(http.post).toHaveBeenCalledWith('/api/vehicles', payload)
    expect(http.get).toHaveBeenCalled()
  })

  it('updates only editable fields with an encoded plate path', async () => {
    const store = useVehicleStore()
    const payload = { vtype: vehicle.vtype, owner: '吕浩', phone: '13800000002' }
    vi.mocked(http.put).mockResolvedValue({ data: vehicle })
    await store.update(vehicle.plate, payload)
    expect(http.put).toHaveBeenCalledWith(
      `/api/vehicles/${encodeURIComponent(vehicle.plate)}`,
      payload,
    )
  })

  it('does not mutate displayed data when deletion fails', async () => {
    const store = useVehicleStore()
    store.items = [vehicle]
    vi.mocked(http.delete).mockRejectedValue(new Error('offline'))
    await expect(store.remove(vehicle.plate)).rejects.toThrow('offline')
    expect(store.items).toEqual([vehicle])
  })

  it('accepts DELETE 204 and returns to the last valid page', async () => {
    const store = useVehicleStore()
    store.page = 2
    vi.mocked(http.delete).mockResolvedValue({ status: 204 })
    vi.mocked(http.get)
      .mockResolvedValueOnce(page([], 20, 2))
      .mockResolvedValueOnce(page([vehicle], 20))
    await store.remove(vehicle.plate)
    expect(http.delete).toHaveBeenCalledWith(`/api/vehicles/${encodeURIComponent(vehicle.plate)}`)
    expect(store.page).toBe(1)
    expect(store.items).toEqual([vehicle])
  })

  it('propagates duplicate-create failure without adding a local row', async () => {
    const store = useVehicleStore()
    vi.mocked(http.post).mockRejectedValue(new Error('车牌号已存在'))
    await expect(
      store.create({ plate: vehicle.plate, vtype: vehicle.vtype, owner: '', phone: '' }),
    ).rejects.toThrow('车牌号已存在')
    expect(store.items).toEqual([])
  })
})
