<script setup lang="ts">
import { computed } from 'vue'
import { configValueError } from '@/composables/useConfigEditor'
import type { ConfigKey } from '@/data/week2'

// Keep the draft and validation reactive inside the editable table cell.
const props = defineProps<{
  configKey: ConfigKey
  original: string
  drafts: Partial<Record<ConfigKey, number | undefined>>
  disabled: boolean
}>()
const emit = defineEmits<{ update: [value: number | undefined] }>()
const value = computed(() => props.drafts[props.configKey])
const changed = computed(() => value.value !== Number(props.original))
const error = computed(() => configValueError(value.value))
const update = (next: number | null | undefined) => emit('update', next ?? undefined)
</script>

<template>
  <div class="config-value">
    <div class="config-value__number">
      <el-input-number
        :model-value="value"
        :min="1"
        :step="1"
        :controls="true"
        :aria-label="`${props.configKey} 分钟`"
        :disabled="props.disabled"
        @update:model-value="update"
      />
      <span class="config-value__unit">分钟</span>
    </div>
    <span v-if="error" class="config-value__error" role="alert">{{ error }}</span>
    <span class="config-value__original mono">{{ changed ? '原值' : '当前值' }}：{{ props.original }}</span>
  </div>
</template>

<style scoped>
.config-value {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.config-value__number {
  display: inline-flex;
  align-items: stretch;
}
.config-value :deep(.el-input-number) {
  width: 136px;
}
.config-value__unit {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-2);
  border: 1px solid var(--border-control);
  border-left: 0;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--fill-light);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
.config-value :deep(.el-input-number .el-input__wrapper) {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}
.config-value :deep(input) {
  font-family: var(--font-family-mono);
  font-variant-numeric: tabular-nums;
}
.config-value__error {
  color: var(--state-danger-text);
  width: 100%;
  font-size: var(--font-size-xs);
}
.config-value__original {
  color: var(--text-tertiary);
  width: 100%;
  font-size: var(--font-size-xs);
}
</style>
