<script setup lang="ts">
/**
 * StatusTag —— 标签：车型 / 状态（浅底 + 描边 + 深字）
 *
 * 规格（component-inventory.md §2）：高 22px / 圆角 --radius-xs / 字号 --font-size-xs
 * 取色一律走 `-bg` / `-border` / `-text` 三档 —— **白底上用 text 档**（tokens.css §2）
 */
import { computed } from 'vue'

import type { TokenPrefix } from '@/constants/status'
import { stateTokens } from '@/constants/status'

const props = withDefaults(
  defineProps<{
    /** 直接给文字 */
    text?: string
    /** 状态色前缀；与 bg/border/color 三个 prop 互斥 */
    prefix?: TokenPrefix
    /** 显式三档（如车型标签走 --plate-*），优先于 prefix */
    bg?: string
    border?: string
    color?: string
  }>(),
  { text: '', prefix: undefined, bg: undefined, border: undefined, color: undefined },
)

const style = computed(() => {
  if (props.bg || props.border || props.color) {
    return { background: props.bg, borderColor: props.border, color: props.color }
  }
  const t = stateTokens(props.prefix ?? 'info')
  return { background: t.bg, borderColor: t.border, color: t.text }
})
</script>

<template>
  <span class="status-tag" :style="style">
    <slot>{{ text }}</slot>
  </span>
</template>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  line-height: 1;
  white-space: nowrap;
}
</style>
