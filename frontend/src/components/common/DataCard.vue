<script setup lang="ts">
/**
 * DataCard —— 标题栏（标题 + 总数）+ 表格 + 分页（component-inventory.md §2）
 *
 * 分页条用响应里的 `total`（契约 §6.4），不做前端估算。
 */
const props = withDefaults(
  defineProps<{
    title: string
    /** 总条数，来自接口响应 total */
    total?: number
    page?: number
    size?: number
    loading?: boolean
    /** 是否显示分页（空数据时可隐藏） */
    showPagination?: boolean
  }>(),
  {
    total: 0,
    page: 1,
    size: 20,
    loading: false,
    showPagination: true,
  },
)

const emit = defineEmits<{
  'update:page': [value: number]
  'update:size': [value: number]
  'page-change': [page: number, size: number]
}>()

function handleCurrentChange(p: number) {
  emit('update:page', p)
  emit('page-change', p, props.size)
}

function handleSizeChange(s: number) {
  emit('update:size', s)
  emit('page-change', 1, s)
}
</script>

<template>
  <el-card class="data-card" shadow="never">
    <template #header>
      <div class="data-card__header">
        <div class="data-card__title">
          {{ title }}
          <span v-if="total > 0" class="data-card__total">共 {{ total }} 条</span>
        </div>
        <div class="data-card__tools">
          <slot name="tools" />
        </div>
      </div>
    </template>

    <slot />

    <div v-if="showPagination && total > 0" class="data-card__footer">
      <el-pagination
        :current-page="page"
        :page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
    </div>
  </el-card>
</template>

<style scoped>
.data-card :deep(.el-card__body) {
  padding: 0;
}

.data-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.data-card__title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.data-card__total {
  margin-left: var(--space-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-regular);
  color: var(--text-tertiary);
}

.data-card__tools {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.data-card__footer {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--border-light);
}
</style>
