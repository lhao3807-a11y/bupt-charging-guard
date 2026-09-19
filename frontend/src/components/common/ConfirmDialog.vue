<script setup lang="ts">
/**
 * ConfirmDialog —— 危险操作二次确认（component-inventory.md §2：宽 420px）
 *
 * 文案需说明后果（component-inventory.md §4.1 标注 6 的要求），故 `message` 必填。
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    /** 必须说明「点了会发生什么」 */
    message: string
    /** danger = 删除类；warning = 有副作用但可逆 */
    tone?: 'danger' | 'warning'
    confirmText?: string
    submitting?: boolean
  }>(),
  { title: '操作确认', tone: 'danger', confirmText: '确认删除', submitting: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
}>()

/** 图标底取 --state-*-solid，深字或白字取优（design-tokens.md §3.2） */
const iconStyle = computed(() => ({
  background:
    props.tone === 'danger' ? 'var(--state-danger-solid)' : 'var(--state-warning-solid)',
  color: props.tone === 'danger' ? 'var(--text-inverse)' : 'var(--text-primary)',
}))

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    width="420px"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="confirm-dialog">
      <div class="confirm-dialog__icon" :style="iconStyle" aria-hidden="true">
        <el-icon :size="18"><WarningFilled /></el-icon>
      </div>
      <div class="confirm-dialog__message">{{ message }}</div>
    </div>

    <template #footer>
      <el-button :disabled="submitting" @click="close">取消</el-button>
      <el-button
        :type="tone === 'danger' ? 'danger' : 'warning'"
        :loading="submitting"
        @click="emit('confirm')"
      >
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.confirm-dialog {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.confirm-dialog__icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-pill);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.confirm-dialog__message {
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  color: var(--text-secondary);
  padding-top: var(--space-1);
}
</style>
