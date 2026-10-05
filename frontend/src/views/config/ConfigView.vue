<script setup lang="ts">
import { computed, inject, onMounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfigValueEditor from './ConfigValueEditor.vue'
import { isConfigKey, useConfigEditor } from '@/composables/useConfigEditor'
import { CONFIG_KEYS, WEEK2_DATA_SOURCE } from '@/data/week2'
import type { SystemConfig } from '@/types/contract'

const editor = useConfigEditor(inject(WEEK2_DATA_SOURCE, undefined))
const {
  available,
  writable,
  data,
  loading,
  error,
  drafts,
  saving,
  confirming,
  notice,
  dirty,
  changes,
  canSave,
  confirmationText,
  reload,
  undo,
  prepareSave,
  cancelSave,
  confirmSave,
} = editor
const missing = computed(() =>
  data.value === null
    ? []
    : CONFIG_KEYS.filter((key) => !data.value!.some((row) => row.key === key)),
)
function setDraft(key: string, value: number | undefined) {
  if (isConfigKey(key) && writable && !saving.value && !confirming.value) drafts[key] = value
}
const rowClassName = ({ row }: { row: SystemConfig }) =>
  changes.value.some((change) => change.key === row.key) ? 'config-row--changed' : ''
function dialogVisible(visible: boolean) {
  if (!visible) cancelSave()
}
onMounted(reload)
</script>

<template>
  <div class="page-container">
    <PageHeader title="系统参数配置" description="调整充满超时与异常占位久停的判定阈值">
      <template #actions>
        <el-button
          :disabled="!available || dirty || saving || confirming"
          :loading="loading"
          @click="reload"
          ><AppIcon name="icon-refresh" :size="14" /> 刷新</el-button
        >
        <el-button :disabled="!dirty || saving || confirming" @click="undo"
          ><AppIcon name="icon-reset" :size="14" /> 撤销改动</el-button
        >
        <el-button type="primary" :disabled="!canSave" :loading="saving" @click="prepareSave"
          >保存并生效</el-button
        >
      </template>
    </PageHeader>
    <el-alert
      v-if="!available"
      title="参数数据待接入"
      description="待读取接口交付后展示实际参数。当前没有参数值，保存不可用。"
      type="info"
      :closable="false"
      show-icon
    />
    <el-alert
      v-else-if="!writable"
      title="参数保存待接入"
      description="当前仅可查看参数，保存接口接入后开放编辑。"
      type="info"
      :closable="false"
      show-icon
    />
    <el-alert
      v-else
      title="修改阈值将影响规则②与③的判定，请在适当时机调整"
      type="warning"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="notice"
      class="config-notice"
      :type="notice.tone"
      :title="notice.text"
      :closable="false"
      show-icon
    />
    <el-alert
      v-if="missing.length"
      class="config-notice"
      type="warning"
      :title="`缺少参数：${missing.join('、')}`"
      description="部分判定阈值缺失，请联系管理员核对配置。"
      :closable="false"
      show-icon
    />

    <el-card class="config-card" shadow="never">
      <template #header
        >判定阈值 <span class="config-card__hint">正整数 · 单位为分钟</span></template
      >
      <section v-if="loading" aria-label="参数加载中" aria-busy="true">
        <el-skeleton :rows="8" animated />
      </section>
      <el-alert
        v-else-if="error"
        title="参数加载失败，请点击刷新重试"
        type="error"
        :closable="false"
        show-icon
      />
      <EmptyState v-else-if="!available" description="等待参数数据接入" illustration="no-data" />
      <el-table
        v-else
        :data="data ?? []"
        :row-class-name="rowClassName"
        aria-label="系统判定参数"
        stripe
      >
        <el-table-column prop="key" label="参数键" min-width="240"
          ><template #default="{ row }"
            ><span class="mono">{{ row.key }}</span></template
          ></el-table-column
        >
        <el-table-column prop="value" label="参数值" min-width="240">
          <template #default="{ row }">
            <ConfigValueEditor
              v-if="isConfigKey(row.key)"
              :config-key="row.key"
              :original="row.value"
              :drafts="drafts"
              :disabled="!writable || saving || confirming"
              @update="setDraft(row.key, $event)"
            />
            <span v-else class="mono">{{ row.value }}（只读）</span>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="说明" min-width="300"
          ><template #default="{ row }">{{ row.note || '—' }}</template></el-table-column
        >
        <template #empty
          ><EmptyState compact description="暂无参数，判定阈值尚未配置" illustration="no-data"
        /></template>
      </el-table>
      <div v-if="dirty" class="config-changes" role="status">
        <div>有未保存的改动</div>
        <ul v-if="changes.length">
          <li v-for="change in changes" :key="change.key">
            <span class="mono">{{ change.key }}：{{ change.before }} → {{ change.after }}</span>
            分钟
          </li>
        </ul>
        <div v-else>请先修正参数值，再保存。</div>
      </div>
    </el-card>
    <ConfirmDialog
      :model-value="confirming"
      title="确认调整判定阈值"
      :message="confirmationText"
      tone="warning"
      confirm-text="确认保存"
      :submitting="saving"
      @update:model-value="dialogVisible"
      @confirm="confirmSave"
    />
  </div>
</template>

<style scoped>
.config-card,
.config-notice {
  margin-top: var(--space-4);
}
.config-card__hint {
  margin-left: var(--space-3);
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}
.config-changes {
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--state-warning-border);
  border-radius: var(--radius-sm);
  background: var(--state-warning-bg);
  color: var(--state-warning-text);
  font-size: var(--font-size-sm);
}
.config-changes ul {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-4);
}
.config-card :deep(.config-row--changed td) {
  background: var(--brand-primary-bg);
}
</style>
