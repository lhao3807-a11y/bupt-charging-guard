<script setup lang="ts">
/** 第 6 页：按契约轮询最近更新的截图，不建立视频流。 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const POLL_INTERVAL_MS = 3_000
const frameUrl = ref('')
const loading = ref(true)
const failed = ref(false)
const refreshedAt = ref('')
let pollTimer: ReturnType<typeof setInterval> | undefined

function refreshFrame() {
  loading.value = true
  failed.value = false
  frameUrl.value = `/api/frame/latest?ts=${Date.now()}`
}

function handleFrameLoad() {
  loading.value = false
  refreshedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function handleFrameError() {
  loading.value = false
  failed.value = true
}

onMounted(() => {
  refreshFrame()
  pollTimer = setInterval(refreshFrame, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="page-container preview-page">
    <PageHeader title="实时识别预览" description="查看采集目录中最近更新的一帧截图">
      <template #actions>
        <el-button :loading="loading" @click="refreshFrame">
          <AppIcon name="icon-refresh" :size="14" /> 刷新
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      title="截图轮询 · 不接实时视频流"
      description="每 3 秒读取一次最近更新的静态截图。接入采集端后，请将截图持续写入帧采集目录。"
      type="info"
      :closable="false"
      show-icon
    />

    <el-card class="preview-card" shadow="never">
      <template #header>
        <div class="preview-card__header">
          <span>最近一帧</span>
          <span class="preview-card__time" aria-live="polite">
            {{ refreshedAt ? `页面刷新于 ${refreshedAt}` : '等待截图' }}
          </span>
        </div>
      </template>

      <div class="preview-stage" :aria-busy="loading">
        <img
          v-if="frameUrl && !failed"
          class="preview-stage__image"
          :src="frameUrl"
          alt="最近采集的车辆识别截图"
          @load="handleFrameLoad"
          @error="handleFrameError"
        />
        <el-skeleton v-if="loading && !refreshedAt" :rows="8" animated class="preview-skeleton" />
        <EmptyState
          v-else-if="failed"
          description="暂时没有可用截图。请检查采集端和帧采集目录，再点击刷新。"
          illustration="no-data"
        >
          <el-button @click="refreshFrame">重试</el-button>
        </EmptyState>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.preview-page > .el-alert {
  margin-bottom: var(--space-4);
}

.preview-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.preview-card__time {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
}

.preview-stage {
  display: grid;
  min-height: 360px;
  place-items: center;
  overflow: hidden;
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}

.preview-stage__image {
  display: block;
  max-width: 100%;
  max-height: min(68vh, 720px);
  object-fit: contain;
}

.preview-skeleton {
  width: min(680px, 84%);
  padding: var(--space-6);
}
</style>
