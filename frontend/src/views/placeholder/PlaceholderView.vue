<script setup lang="ts">
/**
 * PlaceholderView —— 未上线页面的统一占位。
 *
 * 用途有两点：
 *  1. 第 3/4/5 页在第 1 周的中间态（能点进、有标题、显示「开发中」，不留白屏）；
 *  2. 第 6 页旧占位入口：保留与当前静态截图预览、后续真实采集联调一致的说明。
 *
 * 明确列出「本周还差什么」，避免 Demo 时被误认为已完成。
 */
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    /** 该页依赖的接口 / 数据源，写清楚便于对齐契约 */
    dependencies?: string[]
    /** 是否展示第 6 页采集联调的预留说明 */
    reserved?: boolean
    /** 里程碑归属，如「第 2 周」 */
    milestone?: string
  }>(),
  { description: '', dependencies: () => [], reserved: false, milestone: '' },
)
</script>

<template>
  <div class="page-container">
    <PageHeader :title="props.title" :description="props.description">
      <template #actions>
        <StatusTag :prefix="props.reserved ? 'info' : 'warning'">
          {{ props.reserved ? '第 2 周线框已解禁' : '开发中' }}
        </StatusTag>
      </template>
    </PageHeader>

    <el-card shadow="never">
      <EmptyState :description="props.reserved ? '静态截图预览已开放，真实采集待接入' : '本页尚未实现'">
        <div class="placeholder__body">
          <el-alert
            v-if="props.reserved"
            type="info"
            :closable="false"
            title="静态截图预览已开放；真实采集联调计划第 3 周完成。"
            class="placeholder__alert"
          />

          <div v-if="props.milestone" class="placeholder__row">
            <span class="placeholder__label">计划完成</span>
            <StatusTag prefix="info">{{ props.milestone }}</StatusTag>
          </div>

          <div v-if="props.dependencies.length" class="placeholder__deps">
            <div class="placeholder__label">依赖</div>
            <ul class="placeholder__list">
              <li v-for="d in props.dependencies" :key="d" class="mono">{{ d }}</li>
            </ul>
          </div>
        </div>
      </EmptyState>
    </el-card>
  </div>
</template>

<style scoped>
.placeholder__body {
  margin-top: var(--space-2);
  text-align: left;
}

.placeholder__alert {
  margin-bottom: var(--space-4);
}

.placeholder__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.placeholder__deps {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
}

.placeholder__label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  flex-shrink: 0;
  line-height: 22px;
}

.placeholder__list {
  margin: 0;
  padding-left: var(--space-5);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.placeholder__list li {
  line-height: 22px;
}
</style>
