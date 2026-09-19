/**
 * 违规记录 store（第 2 页 · Demo 验收项）
 *
 * 筛选在**前端**做：契约 §6.4 的 `GET /api/records` 仅接受 `page` / `size`，
 * 没有筛选参数。为了让「筛选项 + 用响应 total 分页」两个要求同时成立且不越契约，
 * 采用「拉取当前页 → 前端过滤 → 分页条仍显示服务端 total」的口径，
 * 并在页面上如实标注「筛选仅作用于当前页」。
 *
 * 若后续要让筛选走服务端，须先改 CONTRACT.md §6.4 再升版本 —— 不得私自加参数。
 */
import { defineStore } from 'pinia'

import { fetchRecords, notify as notifyApi } from '@/api'
import { NOTIFY_STATUS } from '@/types/contract'
import type { NotifyStatus, ViolationRecord } from '@/types/contract'

/** 第 2 页筛选项（component-inventory.md §4.2）。 */
export interface RecordFilters {
  plate: string
  vtype: string
  pile_id: string
  rule_hit: number | null
  notify_status: NotifyStatus | null
  /** `[start, end]` ISO 字符串，来自 el-date-picker daterange */
  timeRange: [string, string] | null
}

export function emptyFilters(): RecordFilters {
  return {
    plate: '',
    vtype: '',
    pile_id: '',
    rule_hit: null,
    notify_status: null,
    timeRange: null,
  }
}

function inRange(value: string, range: [string, string] | null): boolean {
  if (!range) return true
  const t = new Date(value).getTime()
  const start = new Date(range[0]).getTime()
  // 结束日按「当天 23:59:59」包含，否则选同一天查不到数据
  const end = new Date(range[1]).getTime() + 24 * 60 * 60 * 1000 - 1
  return t >= start && t <= end
}

export const useRecordsStore = defineStore('records', {
  state: () => ({
    /** 服务端本页原始数据 */
    rawItems: [] as ViolationRecord[],
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    filters: emptyFilters(),
  }),

  getters: {
    /** 应用筛选后的行（筛选仅作用于当前页）。 */
    filteredItems(state): ViolationRecord[] {
      const f = state.filters
      const plate = f.plate.trim().toUpperCase()
      const pileId = f.pile_id.trim().toUpperCase()

      return state.rawItems.filter((r) => {
        if (plate && !r.plate.toUpperCase().includes(plate)) return false
        if (f.vtype && r.vtype !== f.vtype) return false
        if (pileId && !(r.pile_id ?? '').toUpperCase().includes(pileId)) return false
        if (f.rule_hit !== null && r.rule_hit !== f.rule_hit) return false
        if (f.notify_status !== null && r.notify_status !== f.notify_status) return false
        if (!inRange(r.occur_time, f.timeRange)) return false
        return true
      })
    },

    hasFilters(state): boolean {
      const f = state.filters
      return Boolean(
        f.plate.trim() ||
          f.vtype ||
          f.pile_id.trim() ||
          f.rule_hit !== null ||
          f.notify_status !== null ||
          f.timeRange,
      )
    },
  },

  actions: {
    async load() {
      this.loading = true
      try {
        const resp = await fetchRecords({ page: this.page, size: this.size })
        this.rawItems = resp.items
        this.total = resp.total
        this.page = resp.page
        this.size = resp.size
      } finally {
        this.loading = false
      }
    },

    /** 筛选条件变化后重新查询（页码归 1）。 */
    async search() {
      this.page = 1
      await this.load()
    },

    async changePage(page: number, size: number) {
      this.page = page
      this.size = size
      await this.load()
    },

    resetFilters() {
      this.filters = emptyFilters()
    },

    /** 发送提醒（契约 §6.3），成功后回调由页面刷新。 */
    async sendNotify(id: number, status: NotifyStatus = NOTIFY_STATUS.已提醒) {
      const resp = await notifyApi({ id, notify_status: status })
      // 就地更新本页数据，避免整页重刷导致滚动位置丢失
      const row = this.rawItems.find((r) => r.id === id)
      if (row) row.notify_status = resp.notify_status
      return resp
    },
  },
})
