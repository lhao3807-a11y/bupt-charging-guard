<script setup lang="ts">
/**
 * PageHeader —— 页面标题 + 说明 + 右侧操作槽（component-inventory.md §2）
 */
defineProps<{
  title: string
  /** 一句话说明，来源/口径写这里 */
  description?: string
}>()
</script>

<template>
  <div class="page-header">
    <div class="page-header__main">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description" class="page-header__desc">{{ description }}</p>
    </div>
    <div class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.page-header__main {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--text-primary);
}

.page-header__desc {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  line-height: var(--line-height-base);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}
</style>
