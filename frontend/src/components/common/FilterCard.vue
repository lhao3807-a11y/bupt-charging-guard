<script setup lang="ts">
/**
 * FilterCard —— 栅格化筛选表单 + 查询/重置（component-inventory.md §2）
 *
 * 用法：默认插槽放 el-form-item，`actions` 插槽可覆盖默认的查询/重置按钮。
 */
withDefaults(
  defineProps<{
    loading?: boolean
    /** 是否显示默认的查询/重置按钮 */
    showDefaultActions?: boolean
  }>(),
  { loading: false, showDefaultActions: true },
)

const emit = defineEmits<{
  search: []
  reset: []
}>()
</script>

<template>
  <el-card class="filter-card" shadow="never">
    <el-form class="filter-card__form" :disabled="loading" @submit.prevent>
      <slot />
      <el-form-item v-if="showDefaultActions" class="filter-card__actions">
        <el-button type="primary" :loading="loading" @click="emit('search')">
          <el-icon><Search /></el-icon>
          <span>查询</span>
        </el-button>
        <el-button @click="emit('reset')">
          <el-icon><RefreshLeft /></el-icon>
          <span>重置</span>
        </el-button>
        <slot name="actions" />
      </el-form-item>
    </el-form>
  </el-card>
</template>

<style scoped>
.filter-card {
  margin-bottom: var(--space-4);
}

.filter-card :deep(.el-card__body) {
  padding: var(--space-4) var(--space-5) 0;
}

.filter-card__form {
  display: flex;
  flex-wrap: wrap;
  gap: 0 var(--space-4);
  align-items: flex-start;
}

.filter-card__form :deep(.el-form-item) {
  margin-bottom: var(--space-4);
}

.filter-card__actions {
  margin-left: auto;
}
</style>
