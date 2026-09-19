<script setup lang="ts">
/**
 * FormDialog —— 新增/编辑弹窗（component-inventory.md §2：宽 520px / 圆角 --radius-lg）
 *
 * 只管外壳与提交状态，表单字段由默认插槽给（各页字段不同）。
 * `mode='edit'` 时业务自行把主键设为只读。
 */
withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    /** 提交中：禁用按钮 + loading */
    submitting?: boolean
    /** 确认按钮文案 */
    confirmText?: string
    width?: string
  }>(),
  { submitting: false, confirmText: '确定', width: '520px' },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: []
}>()

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <slot />

    <template #footer>
      <el-button :disabled="submitting" @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="emit('submit')">
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>
