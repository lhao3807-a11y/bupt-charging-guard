/**
 * 路由表 —— 顺序与命名严格照 docs/CONTRACT.md §1.1「后台页面清单（6 页）」。
 *
 * | # | 页面 | 路径 | 第 1 周范围 |
 * |---|------|------|------------|
 * | 1 | 车辆信息管理 | /vehicle | 做 |
 * | 2 | 违规记录查询 | /records | 做（Demo 验收项） |
 * | 3 | 充电状态展示 | /piles | 做 |
 * | 4 | 报警统计 | /statistics | 做 |
 * | 5 | 系统参数配置 | /config | 做 |
 * | 6 | 实时识别预览 | /preview | 第 1 周不做，仅预留（disabled） |
 *
 * `meta.title` / `meta.icon` 同时供侧边导航与顶栏面包屑读取，避免两处各写一遍。
 */

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

/** 侧边导航 6 项，顺序即契约 §1.1 的编号顺序。 */
export const navRoutes: RouteRecordRaw[] = [
  {
    path: '/vehicle',
    name: 'vehicle',
    component: () => import('@/views/vehicle/VehicleView.vue'),
    meta: { title: '车辆信息管理', icon: 'Van', order: 1 },
  },
  {
    path: '/records',
    name: 'records',
    component: () => import('@/views/records/RecordsView.vue'),
    meta: { title: '违规记录查询', icon: 'Warning', order: 2 },
  },
  {
    path: '/piles',
    name: 'piles',
    component: () => import('@/views/piles/PilesView.vue'),
    meta: { title: '充电状态展示', icon: 'Odometer', order: 3 },
  },
  {
    path: '/statistics',
    name: 'statistics',
    component: () => import('@/views/statistics/StatisticsView.vue'),
    meta: { title: '报警统计', icon: 'PieChart', order: 4 },
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('@/views/config/ConfigView.vue'),
    meta: { title: '系统参数配置', icon: 'Setting', order: 5 },
  },
  {
    path: '/preview',
    name: 'preview',
    component: () => import('@/views/preview/PreviewView.vue'),
    meta: {
      title: '实时识别预览',
      icon: 'VideoCamera',
      order: 6,
      // 契约 §1.1：第 1 周不做，仅预留导航占位
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
