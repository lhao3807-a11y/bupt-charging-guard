/**
 * 路由表 —— 顺序与命名严格照 docs/CONTRACT.md §1.1「后台页面清单（6 页）」。
 *
 * | # | 页面 | 路径 | 第 1 周 | 第 2 周 |
 * |---|------|------|---------|---------|
 * | 1 | 车辆信息管理 | /vehicle | 做 | 做（切 `/api/vehicles`） |
 * | 2 | 违规记录查询 | /records | 做（Demo 验收项） | 做（服务端筛选） |
 * | 3 | 充电状态展示 | /piles | 占位路由 | 实现（依赖 `GET /api/piles`） |
 * | 4 | 报警统计 | /statistics | 占位路由 | 实现（依赖 `GET /api/stats`） |
 * | 5 | 系统参数配置 | /config | 占位路由 | 实现（依赖 `GET/PUT /api/config`） |
 * | 6 | 实时识别预览 | /preview | 不做，仅预留 | 线框解禁，前端仍 `disabled`（接口未就绪） |
 *
 * `meta.title` / `meta.icon` 同时供侧边导航与顶栏面包屑读取，避免两处各写一遍。
 * `meta.icon` 自第 2 周起写**设计侧官方图标名**（`docs/design/assets/icons/`），
 * 由 `@/components/common/AppIcon.vue` 渲染，不再用 Element Plus 图标名。
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

/** 侧边导航 6 项，顺序即契约 §1.1 的编号顺序。 */
export const navRoutes: RouteRecordRaw[] = [
  {
    path: '/vehicle',
    name: 'vehicle',
    component: () => import('@/views/vehicle/VehicleView.vue'),
    meta: { title: '车辆信息管理', icon: 'icon-nav-vehicle', order: 1 },
  },
  {
    path: '/records',
    name: 'records',
    component: () => import('@/views/records/RecordsView.vue'),
    meta: { title: '违规记录查询', icon: 'icon-nav-records', order: 2 },
  },
  {
    path: '/piles',
    name: 'piles',
    component: () => import('@/views/piles/PilesView.vue'),
    meta: { title: '充电状态展示', icon: 'icon-nav-pile-status', order: 3 },
  },
  {
    path: '/statistics',
    name: 'statistics',
    component: () => import('@/views/statistics/StatisticsView.vue'),
    meta: { title: '报警统计', icon: 'icon-nav-stats', order: 4 },
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('@/views/config/ConfigView.vue'),
    meta: { title: '系统参数配置', icon: 'icon-nav-config', order: 5 },
  },
  {
    path: '/preview',
    name: 'preview',
    component: () => import('@/views/preview/PreviewView.vue'),
    meta: {
      title: '实时识别预览',
      icon: 'icon-nav-preview',
      order: 6,
      // 第 2 周：**线框已解禁**（CONTRACT v1.5 §1.1），但 `GET /api/frame/latest`
      // 仍是预留端点（§6.5），故前端按 PLAN §3.1 任务 4.6 保持置灰，
      // 等接口就绪再解禁。这是设计侧与实现侧**有意保留的差异**，
      // 见 `docs/design/walkthrough.md` §9 待确认项。
      reserved: true,
    },
  },
]

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/records' },
  ...navRoutes,
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/placeholder/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta?.title as string | undefined) ?? ''
  document.title = title ? `${title} · 桩点北邮防占系统` : '桩点北邮防占系统'
})

export default router
