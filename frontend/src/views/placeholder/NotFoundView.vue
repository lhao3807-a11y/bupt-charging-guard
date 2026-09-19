<script setup lang="ts">
/** 404 —— 兜底路由，不留白屏。 */
import { useRouter } from 'vue-router'

import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
</script>

<template>
  <div class="page-container">
    <el-card shadow="never">
      <EmptyState description="页面不存在">
        <el-button type="primary" @click="router.push('/records')">返回违规记录查询</el-button>
      </EmptyState>
    </el-card>
  </div>
</template>
