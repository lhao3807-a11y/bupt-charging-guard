<script setup lang="ts">
/**
 * 第 4 页 · 报警统计（契约 §1.1 #4，数据来源 `occupation_record` 按 rule_hit / 时间聚合）
 *
 * 第 1 周交付「占位路由 + 明确的缺口清单」（PLAN_4WEEKS 任务 1.8）。
 * 该项已确认选用 ECharts（component-inventory.md §3 末尾），
 * 完整实现（统计卡 + 柱/折线/饼 + 下钻）排在第 2 周按 PLAN_4WEEKS §3。
 */
import PlaceholderView from '@/views/placeholder/PlaceholderView.vue'

const dependencies = [
  'ECharts + vue-echarts，按需引入 Bar/Line/Pie，配色从 tokens.css 变量读取（禁写死 hex）',
  '序列顺序固定：danger 红 → caution 橙 → warning 黄 → success 绿',
  '契约未定义统计聚合接口，前端聚合不便时需先改 CONTRACT.md 再升版本',
]
</script>

<template>
  <PlaceholderView
    title="报警统计"
    description="违规记录按规则类型 / 时间 / 充电桩聚合分析"
    milestone="第 2 周（PLAN_4WEEKS §3）"
    :dependencies="dependencies"
  />
</template>
