<script setup lang="ts">
/**
 * RuleHitPill —— 违规类型徽标，严按 design-tokens.md §3.3① 映射
 *   1 燃油占位 → danger 红（最高）
 *   2 异常占位 → caution 橙（中）
 *   3 充满未移车 → warning 黄（低）
 *   0 正常充电 → success 绿
 *
 * 文案复用 RULE_HIT_LABEL，页面里不要再写一遍字符串。
 */
import { computed } from 'vue'

import StatusPill from '@/components/common/StatusPill.vue'
import { RULE_HIT_LABEL, RULE_HIT_PREFIX, stateTokens } from '@/constants/status'

const props = defineProps<{ ruleHit: number }>()

const prefix = computed(() => RULE_HIT_PREFIX[props.ruleHit] ?? 'info')

const label = computed(() => RULE_HIT_LABEL[props.ruleHit] ?? `未知规则(${props.ruleHit})`)

const tokens = computed(() => stateTokens(prefix.value))
</script>

<template>
  <StatusPill
    :prefix="prefix"
    :text="label"
    :bg="tokens.bg"
    :border="tokens.border"
    :color="tokens.text"
    :dot="tokens.solid"
  />
</template>
