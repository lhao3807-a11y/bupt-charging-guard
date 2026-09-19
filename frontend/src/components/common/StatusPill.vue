<script setup lang="ts">
/**
 * StatusPill —— 胶囊：带圆点的状态徽标
 *
 * 规格（component-inventory.md §2）：高 24px / 圆角 --radius-pill / 字号 --font-size-xs
 * 圆点用 `-solid` 档（它自己就是色块），文字用 `-text` 档 —— 见 tokens.css §2 边界说明
 */
import { computed } from 'vue'

import type { TokenPrefix } from '@/constants/status'
import { stateTokens } from '@/constants/status'

const props = withDefaults(
  defineProps<{
    text?: string
    prefix?: TokenPrefix
    /** 显式覆盖（如「充电中」走品牌主色） */
    bg?: string
    border?: string
    color?: string
    /** 圆点色，默认取 prefix 的 -solid 档 */
    dot?: string
  }>(),
  {
    text: '',
    prefix: undefined,
    bg: undefined,
    border: undefined,
    color: undefined,
    dot: undefined,
  },
)

const style = computed(() => {
  const t = stateTokens(props.prefix ?? 'info')
  return {
    background: props.bg ?? t.bg,
    borderColor: props.border ?? t.border,
    color: props.color ?? t.text,
  }
})

const dotStyle = computed(() => ({
  background: props.dot ?? stateTokens(props.prefix ?? 'info').solid,
}))
</script>

<template>
  <span class="status-pill" :style="style">
    <span class="status-pill__dot" :style="dotStyle" aria-hidden="true" />
    <slot>{{ text }}</slot>
  </span>
</template>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  height: 24px;
  padding: 0 var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  font-size: var(--font-size-xs);
  line-height: 1;
  white-space: nowrap;
}

.status-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-pill);
  flex-shrink: 0;
}
</style>
