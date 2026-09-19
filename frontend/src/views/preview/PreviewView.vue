<script setup lang="ts">
/**
 * 第 6 页 · 实时识别预览 —— **契约 §1.1 明确第 1 周不做，仅预留导航占位**。
 *
 * 正常情况下导航项为 `disabled`，点不进来；此处作为兜底路由存在，
 * 万一被直接访问 URL 也要给出明确说明，不留白屏。
 */
import PlaceholderView from '@/views/placeholder/PlaceholderView.vue'

const dependencies = [
  '预留端点 GET /api/frame/latest（契约 §6.5，第 1 周不实现）',
  'el-image + el-skeleton 占位，轮询刷新最近一帧',
]
</script>

<template>
  <PlaceholderView
    title="实时识别预览"
    description="最近一帧识别截图（轮询刷新，不接实时视频流）"
    milestone="第 3 周（PLAN_4WEEKS §3）"
    reserved
    :dependencies="dependencies"
  />
</template>
