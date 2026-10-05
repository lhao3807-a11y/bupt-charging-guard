<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import AppIcon from '@/components/common/AppIcon.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { buildStatisticsCharts, violationTotal } from '@/charts/week2'
import { useAsyncSource } from '@/composables/useAsyncSource'
import { WEEK2_DATA_SOURCE } from '@/data/week2'
import type { StatisticsData } from '@/data/week2'

use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer])
const source = inject(WEEK2_DATA_SOURCE, undefined)
const { available, data, loading, error, load } = useAsyncSource<StatisticsData, 7 | 30>(
  source?.loadStatistics?.bind(source),
)
const days = ref<7 | 30>(7)
const reload = () => load(days.value)
const metrics = computed(() => [
  {
    label: '总违规数',
    value: data.value ? violationTotal(data.value) : null,
    color: 'var(--text-primary)',
  },
  { label: '燃油占位', value: data.value?.counts[1], color: 'var(--state-danger-text)' },
  { label: '异常占位', value: data.value?.counts[2], color: 'var(--state-caution-text)' },
  { label: '充满未移车', value: data.value?.counts[3], color: 'var(--state-warning-text)' },
])
const chartState = computed(() => {
  if (!data.value || loading.value) return { options: null, failed: false }
  try {
    return { options: buildStatisticsCharts(data.value), failed: false }
  } catch {
    return { options: null, failed: true }
  }
})
const panels = [
  { key: 'distribution', title: '违规类型分布', wide: false },
  { key: 'share', title: '按桩占比', wide: false },
  { key: 'trend', title: '每日违规趋势', wide: true },
] as const
const summary = computed(() =>
  data.value
    ? `燃油占位 ${data.value.counts[1]} 条，异常占位 ${data.value.counts[2]} 条，充满未移车 ${data.value.counts[3]} 条`
    : '',
)
onMounted(reload)
</script>

<template>
  <div class="page-container">
    <PageHeader title="报警统计" description="按违规类型、日期与充电桩查看记录分布">
      <template #actions>
        <el-select
          v-model="days"
          class="statistics-period"
          aria-label="统计时段"
          :disabled="!available || loading"
          @change="reload"
          ><el-option label="近 7 天" :value="7" /><el-option label="近 30 天" :value="30"
        /></el-select>
        <el-button :disabled="!available" :loading="loading" @click="reload"
          ><AppIcon name="icon-refresh" :size="14" /> 刷新</el-button
        >
      </template>
    </PageHeader>
    <el-alert
      v-if="!available"
      title="统计数据待接入"
      description="待统计聚合接口交付后启用。当前不展示统计数字或图表。"
      type="info"
      :closable="false"
      show-icon
    />
    <el-alert
      v-else-if="error"
      title="统计数据加载失败，请点击刷新重试"
      type="error"
      :closable="false"
      show-icon
    />
    <el-alert
      v-else-if="chartState.failed"
      title="图表主题加载失败，请刷新页面重试"
      type="error"
      :closable="false"
      show-icon
    />
    <section class="statistics-metrics" aria-label="所选时段违规统计">
      <el-card v-for="metric in metrics" :key="metric.label" shadow="never"
        ><div class="statistics-metrics__label">{{ metric.label }}</div>
        <strong class="mono" :style="{ color: metric.color }">{{
          loading ? '—' : (metric.value ?? '—')
        }}</strong
        ><span>条</span></el-card
      >
    </section>
    <div class="statistics-charts">
      <el-card
        v-for="panel in panels"
        :key="panel.key"
        shadow="never"
        :class="{ 'statistics-charts__wide': panel.wide }"
      >
        <template #header>{{ panel.title }}</template>
        <figure class="statistics-figure" :aria-label="panel.title">
          <el-skeleton v-if="loading" class="statistics-skeleton" animated aria-busy="true"
            ><template #template
              ><el-skeleton-item variant="rect" class="statistics-chart" /></template
          ></el-skeleton>
          <EmptyState
            v-else-if="!available"
            compact
            description="等待统计数据接入"
            illustration="no-record"
          />
          <EmptyState
            v-else-if="error || chartState.failed"
            compact
            description="暂时无法展示统计，请刷新重试"
            illustration="no-data"
          />
          <EmptyState
            v-else-if="!chartState.options || (panel.key === 'share' && !data?.piles.length)"
            compact
            description="所选时段暂无违规记录"
            illustration="no-record"
          />
          <template v-else>
            <VChart
              class="statistics-chart"
              :option="chartState.options[panel.key]"
              :autoresize="true"
            />
            <figcaption>
              {{ summary }}<template v-if="panel.key === 'trend'">；按每日记录展示趋势</template>
            </figcaption>
            <table
              v-if="panel.key === 'share'"
              class="statistics-data-table"
              aria-label="按桩违规数"
            >
              <caption>
                按桩违规明细
              </caption>
              <thead>
                <tr>
                  <th>桩 ID</th>
                  <th>违规数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pile in data?.piles" :key="pile.pileId ?? ''">
                  <td class="mono">{{ pile.pileId ?? '未关联桩' }}</td>
                  <td class="mono">{{ pile.count }}</td>
                </tr>
              </tbody>
            </table>
            <table
              v-else-if="panel.key === 'trend'"
              class="statistics-data-table"
              aria-label="每日违规趋势"
            >
              <caption>
                每日违规明细
              </caption>
              <thead>
                <tr>
                  <th>日期</th>
                  <th>燃油占位</th>
                  <th>异常占位</th>
                  <th>充满未移车</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="point in data?.trend" :key="point.date">
                  <td class="mono">{{ point.date }}</td>
                  <td class="mono">{{ point.counts[1] }}</td>
                  <td class="mono">{{ point.counts[2] }}</td>
                  <td class="mono">{{ point.counts[3] }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </figure>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.statistics-period {
  width: 128px;
}
.statistics-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
  margin: var(--space-4) 0;
}
.statistics-metrics__label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}
.statistics-metrics strong {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}
.statistics-metrics span {
  margin-left: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
.statistics-charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}
.statistics-charts__wide {
  grid-column: 1 / -1;
}
.statistics-figure {
  margin: 0;
  min-width: 0;
}
.statistics-chart {
  height: 320px;
  width: 100%;
}
.statistics-figure figcaption {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-base);
  text-align: center;
  margin-top: var(--space-3);
}
.statistics-data-table {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 1000px) {
  .statistics-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .statistics-charts {
    grid-template-columns: 1fr;
  }
}
</style>
