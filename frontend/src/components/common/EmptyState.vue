<script setup lang="ts">
/**
 * EmptyState —— 空状态（component-inventory.md §2）
 *
 * 沿用 el-empty 的插画，但描述与操作槽由业务给，避免各页各写一套。
 */
withDefaults(
  defineProps<{
    description?: string
    /** 紧凑模式：嵌在卡片里时用小尺寸 */
    compact?: boolean
  }>(),
  { description: '暂无数据', compact: false },
)
</script>

<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <el-empty :description="description" :image-size="compact ? 72 : 100">
      <slot />
    </el-empty>
  </div>
</template>

<style scoped>
.empty-state {
  padding: var(--space-6) 0;
}

.empty-state--compact {
  padding: var(--space-4) 0;
}

.empty-state :deep(.el-empty__description) {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}
</style>
