/**
 * 车辆信息 store（第 1 页）
 *
 * 契约 **§6.6 已定义**车辆 CRUD 四端点（`GET/POST /api/vehicles`、`PUT/DELETE /api/vehicles/{plate}`），
 * 但**后端尚未实现**（实测 `GET/POST /api/vehicles` 均返回 404）。
 * 因此本 store **暂用 `localStorage` 做持久化**，作为明确标注的临时数据源，
 * 目的是先把 UI 与字段对齐做出来、能演示。
 *
 * ⚠️ **后端就绪后必须切换**（替换点见 `frontend/README.md` §6.2）：
 * 改为调用 `api/` 的 `/api/vehicles`，并移除页面顶部的黄色警示条。
 * 契约口径注意：`plate` 是主键不可改、重复新增返回 `409`、`DELETE` 返回 `204` 且**不级联删违规记录**。
 *
 * 种子数据照契约 §3.1 字段；`created_at` 用 ISO 8601。
 */
import { defineStore } from 'pinia'

import { VTYPE } from '@/types/contract'
import type { Vehicle, VType } from '@/types/contract'

const STORAGE_KEY = 'charging-guard:vehicles:v1'

/** 初始种子：覆盖新能源 / 燃油两类，便于演示车型标签取色。 */
function seedVehicles(): Vehicle[] {
  const base = new Date('2026-09-01T09:00:00').getTime()
  const at = (minutes: number) => new Date(base + minutes * 60_000).toISOString()

  return [
    {
      plate: '京AD12345',
      vtype: VTYPE.新能源 as VType,
      owner: '张伟',
      phone: '13800136621',
      created_at: at(0),
    },
    {
      plate: '京A88888',
      vtype: VTYPE.燃油 as VType,
      owner: '李强',
      phone: '13900139000',
      created_at: at(35),
    },
    {
      plate: '京AD66666',
      vtype: VTYPE.新能源 as VType,
      owner: '王芳',
      phone: '13700137001',
      created_at: at(96),
    },
  ]
}

function load(): Vehicle[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return seedVehicles()
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return seedVehicles()
    return parsed as Vehicle[]
  } catch {
    return seedVehicles()
  }
}

export const useVehicleStore = defineStore('vehicle', {
  state: () => ({
    items: [] as Vehicle[],
    loading: false,
    /** 车辆表主键是 plate，编辑态下不可改 */
    isLocalSource: true,
  }),

  getters: {
    total(state): number {
      return state.items.length
    },
  },

  actions: {
    init() {
      this.items = load()
    },

    persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.items))
    },

    /** 新增：车牌为主键，重复即拒绝。 */
    create(payload: Omit<Vehicle, 'created_at'>): void {
      if (this.items.some((v) => v.plate === payload.plate)) {
        throw new Error(`车牌号 ${payload.plate} 已存在`)
      }
      this.items.unshift({ ...payload, created_at: new Date().toISOString() })
      this.persist()
    },

    /**
     * 编辑：车牌是主键，**不允许改**（线框标注：编辑态只读）。
     * 只更新车型 / 车主 / 手机号。
     */
    update(plate: string, payload: Pick<Vehicle, 'vtype' | 'owner' | 'phone'>): void {
      const row = this.items.find((v) => v.plate === plate)
      if (!row) throw new Error(`车牌号 ${plate} 不存在`)
      row.vtype = payload.vtype
      row.owner = payload.owner
      row.phone = payload.phone
      this.persist()
    },

    /**
     * 删除。文案需说明后果：违规记录保留但不再关联手机号（component-inventory.md §4.1）。
     */
    remove(plate: string): void {
      this.items = this.items.filter((v) => v.plate !== plate)
      this.persist()
    },

    /** 恢复种子（演示前重置用）。 */
    resetToSeed() {
      this.items = seedVehicles()
      this.persist()
    },
  },
})
