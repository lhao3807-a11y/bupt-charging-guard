<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncSource } from '@/composables/useAsyncSource'
import { pileStatusTokens } from '@/constants/status'
import { WEEK2_DATA_SOURCE } from '@/data/week2'
import { PILE_STATUS } from '@/types/contract'
import type { ChargingPile, PileStatus } from '@/types/contract'
import { formatDateTime } from '@/utils/format'

const source = inject(WEEK2_DATA_SOURCE, undefined)
const { available, data, loading, error, load } = useAsyncSource<ChargingPile[], PileStatus | undefined>(source?.loadPiles)
const selectedStatus = ref<PileStatus | ''>('')
const view = ref<'cards' | 'table'>('cards')
const statuses = Object.values(PILE_STATUS)
const counts = computed(() => data.value === null || loading.value ? null : Object.fromEntries(
  statuses.map((status) => [status, data.value!.filter((pile) => pile.status === status).length]),
))
const emptyText = computed(() => selectedStatus.value ? '没有符合状态筛选的充电桩' : '暂无充电桩')
const tagStyle = (status: PileStatus) => {
  const tokens = pileStatusTokens(status)
  return { bg: tokens.bg, border: tokens.border, color: tokens.text }
}
const reload = () => load(selectedStatus.value || undefined)
onMounted(reload)
</script>

<template>
  <div class="page-container">
    <PageHeader title="充电状态展示" description="查看充电桩状态、绑定车辆与充电时间">
      <template #actions><el-button :disabled="!available" :loading="loading" @click="reload"><AppIcon name="icon-refresh" :size="14" /> 刷新</el-button></template>
    </PageHeader>
    <el-alert v-if="!available" title="充电桩数据待接入" description="界面已准备就绪，待充电桩查询接口交付后启用。当前没有可展示的桩状态。" type="info" :closable="false" show-icon />
    <el-alert v-else title="充电状态为模拟数据，预留 OCPP 适配层" type="info" :closable="false" show-icon />
    <section class="pile-summary" aria-label="当前筛选结果统计">
      <el-card v-for="status in statuses" :key="status" shadow="never">
        <div class="pile-summary__label" :style="{ color: pileStatusTokens(status).text }">{{ status }}</div>
        <strong class="pile-summary__value mono" :style="{ color: pileStatusTokens(status).text }">{{ counts?.[status] ?? '—' }}</strong>
        <span class="pile-summary__unit">个 · 当前结果</span>
      </el-card>
    </section>
    <el-card shadow="never">
      <template #header>
        <div class="pile-toolbar">
          <div class="pile-toolbar__filter"><span>状态</span><el-select v-model="selectedStatus" aria-label="充电桩状态筛选" :disabled="!available || loading" @change="reload"><el-option label="全部" value="" /><el-option v-for="status in statuses" :key="status" :label="status" :value="status" /></el-select></div>
          <el-button-group aria-label="展示方式"><el-button :type="view === 'cards' ? 'primary' : 'default'" :aria-pressed="view === 'cards'" @click="view = 'cards'">卡片视图</el-button><el-button :type="view === 'table' ? 'primary' : 'default'" :aria-pressed="view === 'table'" @click="view = 'table'">列表视图</el-button></el-button-group>
        </div>
      </template>
      <section v-if="loading" class="pile-grid" aria-label="充电桩加载中" aria-busy="true">
        <el-skeleton v-for="index in 6" :key="index" animated><template #template><el-skeleton-item variant="h3" /><el-skeleton-item v-for="line in 3" :key="line" variant="text" /></template></el-skeleton>
      </section>
      <el-alert v-else-if="error" title="充电桩加载失败，请点击刷新重试" type="error" :closable="false" show-icon />
      <EmptyState v-else-if="!available" description="等待充电桩数据接入" illustration="no-data" />
      <EmptyState v-else-if="!data?.length" :description="emptyText" :illustration="selectedStatus ? 'search-empty' : 'no-data'" />
      <div v-else-if="view === 'cards'" class="pile-grid">
        <article v-for="pile in data" :key="pile.pile_id" class="pile-card" :style="{ borderTopColor: pileStatusTokens(pile.status).solid }">
          <div class="pile-card__header"><h2 class="mono">{{ pile.pile_id }}</h2><StatusTag :text="pile.status" v-bind="tagStyle(pile.status)" /></div>
          <dl><div><dt>绑定车牌</dt><dd class="mono">{{ pile.bound_plate ?? '未绑定' }}</dd></div><div><dt>开始时间</dt><dd class="mono">{{ formatDateTime(pile.start_time) }}</dd></div><div><dt>结束时间</dt><dd class="mono">{{ formatDateTime(pile.end_time) }}</dd></div></dl>
        </article>
      </div>
      <el-table v-else :data="data" aria-label="充电桩状态列表" stripe>
        <el-table-column prop="pile_id" label="桩 ID" min-width="140"><template #default="{ row }"><span class="mono">{{ row.pile_id }}</span></template></el-table-column>
        <el-table-column prop="status" label="状态" min-width="110"><template #default="{ row }"><StatusTag :text="row.status" v-bind="tagStyle(row.status)" /></template></el-table-column>
        <el-table-column prop="bound_plate" label="绑定车牌" min-width="160"><template #default="{ row }"><span class="mono">{{ row.bound_plate ?? '未绑定' }}</span></template></el-table-column>
        <el-table-column prop="start_time" label="开始时间" min-width="190"><template #default="{ row }"><span class="mono">{{ formatDateTime(row.start_time) }}</span></template></el-table-column>
        <el-table-column prop="end_time" label="结束时间" min-width="190"><template #default="{ row }"><span class="mono">{{ formatDateTime(row.end_time) }}</span></template></el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.pile-summary, .pile-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-4); }
.pile-summary { margin: var(--space-4) 0; }
.pile-summary__label { font-size: var(--font-size-sm); margin-bottom: var(--space-2); }
.pile-summary__value { font-size: var(--font-size-xl); font-weight: var(--font-weight-semibold); }
.pile-summary__unit { margin-left: var(--space-2); color: var(--text-tertiary); font-size: var(--font-size-xs); }
.pile-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; }
.pile-toolbar__filter { display: flex; align-items: center; gap: var(--space-3); font-size: var(--font-size-sm); }
.pile-toolbar__filter :deep(.el-select) { width: 160px; }
.pile-card { padding: var(--space-4); border: 1px solid var(--border-base); border-top-width: 4px; border-radius: var(--radius-md); }
.pile-card__header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.pile-card h2 { margin: 0; font-size: var(--font-size-md); }
.pile-card dl { margin: var(--space-4) 0 0; font-size: var(--font-size-sm); }
.pile-card dl div { display: flex; justify-content: space-between; gap: var(--space-2); margin-top: var(--space-3); }
.pile-card dt { color: var(--text-tertiary); flex-shrink: 0; }
.pile-card dd { margin: 0; overflow-wrap: anywhere; text-align: right; }
.pile-grid :deep(.el-skeleton__item) { margin-bottom: var(--space-3); }
@media (max-width: 1100px) { .pile-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 720px) { .pile-grid, .pile-summary { grid-template-columns: 1fr; } }
</style>
