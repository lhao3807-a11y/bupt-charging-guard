<script setup lang="ts">
/**
 * 第 3 页 · 充电状态展示（契约 §1.1 #3，数据来源 `charging_pile` 表，模拟数据）
 *
 * 第 1 周交付「占位路由 + 明确的缺口清单」（PLAN_4WEEKS 任务 1.8）。
 * 按契约 §1.1 本页第 1 周范围是「做」，完整实现（统计卡 + 卡片/表格切换）
 * 排在有效工时富余时，或与 H 讨论后调整优先级。
 */
import PlaceholderView from '@/views/placeholder/PlaceholderView.vue'

const dependencies = [
  'charging_pile 表（pile_id / status / bound_plate / start_time / end_time）',
  '桩状态色映射：空闲 info 灰 / 充电中 主色蓝 / 已充满 caution 橙',
  '契约未定义充电桩查询接口，需先改 CONTRACT.md 再升版本',
]
</script>

<template>
  <PlaceholderView
    title="充电状态展示"
    description="充电桩运行状态总览（数据来源：charging_pile 表，模拟数据）"
    milestone="第 1 周（契约 §1.1 范围内）"
    :dependencies="dependencies"
  />
</template>
