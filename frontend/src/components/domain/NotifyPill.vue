<script setup lang="ts">
/**
 * NotifyPill —— 提醒状态徽标，严按 design-tokens.md §3.3② 映射
 *   未提醒 → warning 黄（待处理）
 *   已提醒 → success 绿
 *   失败   → danger 红
 */
import { computed } from 'vue'

import StatusPill from '@/components/common/StatusPill.vue'
import { stateTokens, NOTIFY_STATUS_PREFIX } from '@/constants/status'
import type { NotifyStatus } from '@/types/contract'

const props = defineProps<{ status: NotifyStatus }>()

const prefix = computed(() => NOTIFY_STATUS_PREFIX[props.status] ?? 'info')

const tokens = computed(() => stateTokens(prefix.value))
</script>

<template>
  <StatusPill
    :prefix="prefix"
    :text="status"
    :bg="tokens.bg"
    :border="tokens.border"
    :color="tokens.text"
    :dot="tokens.solid"
  />
</template>
