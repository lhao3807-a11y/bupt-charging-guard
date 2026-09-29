<script setup lang="ts">
/**
 * FilterCard —— 栅格化筛选表单 + 查询/重置（component-inventory.md §2）
 *
 * 用法：默认插槽放 el-form-item，`actions` 插槽可覆盖默认的查询/重置按钮。
 * 图标走官方图标集（第 2 周收口，任务 6.4）：「重置」用 `icon-reset`
 * 而非 `icon-refresh` —— 前者语义是「恢复初始值」，后者是「重新拉数据」。
 */
import AppIcon from '@/components/common/AppIcon.vue'

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
          <AppIcon name="icon-search" :size="14" />
          <span>查询</span>
        </el-button>
        <el-button @click="emit('reset')">
          <AppIcon name="icon-reset" :size="14" />
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
