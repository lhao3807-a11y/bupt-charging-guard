<script setup lang="ts">
/**
 * PlateTag —— 车型标签，取真实车牌底色（design-tokens.md §3.3④，已确认采纳）
 *   新能源 → 绿牌绿 --plate-new-energy-*；燃油 → 蓝牌蓝 --plate-fuel-*
 *
 * 注意：新能源的绿与「正常绿」同色系，这是有意为之 —— 车型是身份、不是状态，
 * 靠位置（固定列）与文案区分，不靠色相。
 */
import { computed } from 'vue'

import StatusTag from '@/components/common/StatusTag.vue'
import { plateTokens } from '@/constants/status'

const props = defineProps<{ vtype: string }>()

const tokens = computed(() => plateTokens(props.vtype))
</script>

<template>
  <StatusTag :bg="tokens.bg" :border="tokens.border" :color="tokens.text">{{ vtype }}</StatusTag>
</template>
