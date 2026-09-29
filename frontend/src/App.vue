<script setup lang="ts">
/**
 * 应用根组件：只决定「套不套后台骨架」。
 *
 * `meta.blank` 的页面（目前只有登录页，任务 6.6）**不套 AppShell** ——
 * 登录页没有侧边导航、顶栏与页脚，套上会多出一圈后台外壳。
 * 其余页面照旧渲染 `<AppShell />`，由它内部的 `<router-view>` 承载。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'

const route = useRoute()

const isBlank = computed(() => Boolean(route.meta?.blank))
</script>

<template>
  <router-view v-if="isBlank" />
  <AppShell v-else />
</template>
