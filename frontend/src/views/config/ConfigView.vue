<script setup lang="ts">
/**
 * 第 5 页 · 系统参数配置（契约 §1.1 #5，数据来源 `system_config` 表）
 *
 * 第 1 周交付「占位路由 + 明确的缺口清单」（PLAN_4WEEKS 任务 1.8）。
 * 本页是 `full_timeout_min` / `abnormal_park_min` 的**唯一修改入口**，
 * 契约 §7 明令阈值严禁硬编码 —— 实现时必须读写 system_config，不可前端兜底默认值。
 */
import PlaceholderView from '@/views/placeholder/PlaceholderView.vue'

const dependencies = [
  'system_config 表（key / value / note）',
  '阈值：full_timeout_min（充满超时，默认 30）/ abnormal_park_min（异常占位久停，默认 30）',
  '契约未定义参数读写接口，需先改 CONTRACT.md 再升版本',
]
</script>

<template>
  <PlaceholderView
    title="系统参数配置"
    description="阈值参数的唯一修改入口（契约 §7：严禁硬编码）"
    milestone="第 2 周（PLAN_4WEEKS §3）"
    :dependencies="dependencies"
  />
</template>
