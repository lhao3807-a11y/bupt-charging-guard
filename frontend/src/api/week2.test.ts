import { beforeEach, describe, expect, it, vi } from 'vitest'

const { get, put } = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }))
vi.mock('./http', () => ({ http: { get, put } }))

import { week2DataSource } from './week2'

describe('week-two HTTP data source', () => {
  beforeEach(() => {
    get.mockReset()
    put.mockReset()
  })

  it('loads every filtered pile page so the list and status totals are complete', async () => {
    const first = { pile_id: 'P-001', status: '充电中', bound_plate: null, start_time: null, end_time: null }
    const last = { pile_id: 'P-201', status: '充电中', bound_plate: null, start_time: null, end_time: null }
    get
      .mockResolvedValueOnce({ data: { items: [first], total: 201, page: 1, size: 200 } })
      .mockResolvedValueOnce({ data: { items: [last], total: 201, page: 2, size: 200 } })

    await expect(week2DataSource.loadPiles('充电中')).resolves.toEqual([first, last])
    expect(get).toHaveBeenNthCalledWith(1, '/api/piles', {
      params: { page: 1, size: 200, status: '充电中' },
    })
    expect(get).toHaveBeenNthCalledWith(2, '/api/piles', {
      params: { page: 2, size: 200, status: '充电中' },
    })
  })

  it('maps contract statistics into the three chart series without losing per-pile counts', async () => {
    get.mockResolvedValue({
      data: {
        total: 6,
        by_rule: [
          { rule_hit: 0, label: '正常', count: 1 },
          { rule_hit: 1, label: '燃油占位', count: 2 },
          { rule_hit: 2, label: '异常占位', count: 3 },
          { rule_hit: 3, label: '充满未移车', count: 1 },
        ],
        by_date: [
          {
            date: '2026-10-07',
            count: 6,
            by_rule: [
              { rule_hit: 0, label: '正常', count: 1 },
              { rule_hit: 1, label: '燃油占位', count: 2 },
              { rule_hit: 2, label: '异常占位', count: 3 },
              { rule_hit: 3, label: '充满未移车', count: 1 },
            ],
          },
        ],
        by_pile: [
          { pile_id: 'P-001', count: 4 },
          { pile_id: null, count: 2 },
        ],
        days: 7,
      },
    })

    await expect(week2DataSource.loadStatistics(7)).resolves.toEqual({
      counts: { 1: 2, 2: 3, 3: 1 },
      trend: [{ date: '2026-10-07', counts: { 1: 2, 2: 3, 3: 1 } }],
      piles: [
        { pileId: 'P-001', count: 4 },
        { pileId: null, count: 2 },
      ],
    })
    expect(get).toHaveBeenCalledWith('/api/stats', { params: { days: 7 } })
  })

  it('reads and writes the config contract using the page payload and numeric updates', async () => {
    get.mockResolvedValue({
      data: { items: [{ key: 'full_timeout_min', value: '30', note: null }], total: 1 },
    })
    await expect(week2DataSource.loadConfig()).resolves.toEqual([
      { key: 'full_timeout_min', value: '30', note: '' },
    ])

    await week2DataSource.saveConfig([
      { key: 'full_timeout_min', before: '30', after: 45 },
      { key: 'abnormal_park_min', before: '40', after: 50 },
    ])
    expect(put).toHaveBeenCalledWith('/api/config', {
      full_timeout_min: 45,
      abnormal_park_min: 50,
    })
  })
})
