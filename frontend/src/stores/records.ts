/** 违规记录：契约 §6.4 服务端筛选与分页。 */
import { defineStore } from 'pinia'
import { fetchRecords, notify as notifyApi } from '@/api'
import { NOTIFY_STATUS } from '@/types/contract'
import type { NotifyStatus, RecordQuery, ViolationRecord, VType } from '@/types/contract'

export interface RecordFilters {
  plate: string
  vtype: VType | ''
  pile_id: string
  rule_hit: number | '' | null | undefined
  notify_status: NotifyStatus | '' | null | undefined
  timeRange: [string, string] | null
}
export function emptyFilters(): RecordFilters {
  return { plate: '', vtype: '', pile_id: '', rule_hit: null, notify_status: null, timeRange: null }
}
export const useRecordsStore = defineStore('records', {
  state: () => ({
    rawItems: [] as ViolationRecord[],
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    error: false,
    requestId: 0,
    filters: emptyFilters(),
    appliedQuery: {} as RecordQuery,
  }),
  getters: {
    filteredItems: (state): ViolationRecord[] => state.rawItems,
    hasFilters: (state): boolean => Object.keys(state.appliedQuery).length > 0,
  },
  actions: {
    async load() {
      const id = ++this.requestId
      this.loading = true
      this.error = false
      try {
        const resp = await fetchRecords({ ...this.appliedQuery, page: this.page, size: this.size })
        if (id !== this.requestId) return
        const lastPage = Math.max(1, Math.ceil(resp.total / resp.size))
        if (resp.page > lastPage) {
          this.page = lastPage
          await this.load()
          return
        }
        this.rawItems = resp.items
        this.total = resp.total
        this.page = resp.page
        this.size = resp.size
      } catch (error) {
        if (id !== this.requestId) return
        this.rawItems = []
        this.total = 0
        this.error = true
        throw error
      } finally {
        if (id === this.requestId) this.loading = false
      }
    },
    async search() {
      const f = this.filters
      const query: RecordQuery = {}
      if (f.plate.trim()) query.plate = f.plate.trim()
      if (f.vtype) query.vtype = f.vtype
      if (f.pile_id.trim()) query.pile_id = f.pile_id.trim()
      if (typeof f.rule_hit === 'number') query.rule_hit = f.rule_hit
      if (f.notify_status) query.notify_status = f.notify_status
      if (f.timeRange) [query.start_time, query.end_time] = f.timeRange
      this.appliedQuery = query
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
    async sendNotify(id: number, status: NotifyStatus = NOTIFY_STATUS.已提醒) {
      const resp = await notifyApi({ id, notify_status: status })
      // 写入已成功；刷新失败显示加载错误，不要求用户重复提醒。
      await this.load().catch(() => undefined)
      return resp
    },
  },
})
