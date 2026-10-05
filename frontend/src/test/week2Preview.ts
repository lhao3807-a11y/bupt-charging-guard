/** Dev-only real-browser harness. This file is not imported by the production entry. */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import '@/styles/tokens.css'
import '@/styles/global.css'
import App from '@/App.vue'
import { navRoutes } from '@/router'
import { WEEK2_DATA_SOURCE } from '@/data/week2'
import type { Week2DataSource } from '@/data/week2'
import type { ChargingPile, SystemConfig } from '@/types/contract'

if (!import.meta.env.DEV) throw new Error('组件验证入口只用于开发环境')
const piles: ChargingPile[] = [
  {
    pile_id: 'TEST-001',
    status: '空闲',
    bound_plate: '京AD12345',
    start_time: '2026-10-05T09:00:00',
    end_time: null,
  },
  {
    pile_id: 'TEST-002',
    status: '充电中',
    bound_plate: '京AD24680',
    start_time: '2026-10-05T09:15:00',
    end_time: null,
  },
  {
    pile_id: 'TEST-003',
    status: '已充满',
    bound_plate: '京AD67890',
    start_time: '2026-10-05T08:00:00',
    end_time: '2026-10-05T09:30:00',
  },
]
const config: SystemConfig[] = [
  { key: 'full_timeout_min', value: '30', note: '规则③：充满后仍未移车的时间阈值' },
  { key: 'abnormal_park_min', value: '40', note: '规则②：未充电久停的时间阈值' },
]
const source: Week2DataSource = {
  async loadPiles(status) {
    return structuredClone(status ? piles.filter((pile) => pile.status === status) : piles)
  },
  async loadStatistics(days) {
    return {
      counts: { 1: 3, 2: 2, 3: 1 },
      trend: Array.from({ length: days }, (_, index) => ({
        date: `测试日 ${index + 1}`,
        counts: { 1: index === 1 ? 3 : 0, 2: index === 2 ? 2 : 0, 3: index === 3 ? 1 : 0 },
      })),
      piles: [
        { pileId: 'TEST-001', count: 3 },
        { pileId: 'TEST-002', count: 2 },
        { pileId: null, count: 1 },
      ],
    }
  },
  async loadConfig() {
    return structuredClone(config)
  },
  async saveConfig(changes) {
    for (const change of changes)
      config.find((row) => row.key === change.key)!.value = String(change.after)
  },
}
const router = createRouter({
  history: createWebHashHistory(),
  routes: [...navRoutes, { path: '/', redirect: '/piles' }],
})
router.afterEach((to) => {
  document.title = `${String(to.meta.title)} · 前端组件验证（测试数据）`
})
createApp(App)
  .use(createPinia())
  .use(router)
  .use(ElementPlus, { locale: zhCn })
  .provide(WEEK2_DATA_SOURCE, source)
  .mount('#app')
