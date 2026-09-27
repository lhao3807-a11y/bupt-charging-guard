/** 车辆数据唯一来源：契约 §6.6 的持久化接口。 */
import { defineStore } from 'pinia'
import { createVehicle, deleteVehicle, fetchVehicles, updateVehicle } from '@/api'
import type { Vehicle, VehicleCreate, VehicleQuery, VehicleUpdate, VType } from '@/types/contract'

const emptyFilters = () => ({ plate: '', vtype: '' as VType | '', owner: '' })
export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    items: [] as Vehicle[],
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    error: false,
    requestId: 0,
    filters: emptyFilters(),
    appliedQuery: {} as VehicleQuery,
  }),
  getters: {
    hasFilters: (state): boolean => Object.keys(state.appliedQuery).length > 0,
  },
  actions: {
    async load() {
      const id = ++this.requestId
      this.loading = true
      this.error = false
      try {
        const resp = await fetchVehicles({ ...this.appliedQuery, page: this.page, size: this.size })
        if (id !== this.requestId) return
        const lastPage = Math.max(1, Math.ceil(resp.total / resp.size))
        if (resp.page > lastPage) {
          this.page = lastPage
          await this.load()
          return
        }
        this.items = resp.items
        this.total = resp.total
        this.page = resp.page
        this.size = resp.size
      } catch (error) {
        if (id !== this.requestId) return
        this.items = []
        this.total = 0
        this.error = true
        throw error
      } finally {
        if (id === this.requestId) this.loading = false
      }
    },
    async search() {
      const f = this.filters
      const query: VehicleQuery = {}
      if (f.plate.trim()) query.plate = f.plate.trim()
      if (f.owner.trim()) query.owner = f.owner.trim()
      if (f.vtype) query.vtype = f.vtype
      this.appliedQuery = query
      this.page = 1
      await this.load()
    },
    resetFilters() {
      this.filters = emptyFilters()
    },
    async changePage(page: number, size: number) {
      this.page = page
      this.size = size
      await this.load()
    },
    async create(payload: VehicleCreate) {
      const row = await createVehicle(payload)
      this.page = 1
      await this.load().catch(() => undefined)
      return row
    },
    async update(plate: string, payload: VehicleUpdate) {
      const row = await updateVehicle(plate, payload)
      await this.load().catch(() => undefined)
      return row
    },
    async remove(plate: string) {
      await deleteVehicle(plate)
      await this.load().catch(() => undefined)
    },
  },
})
