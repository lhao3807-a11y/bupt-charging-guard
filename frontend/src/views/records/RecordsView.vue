<script setup lang="ts">
/**
 * 第 2 页 · 违规记录查询 —— **Demo 验收项，最高优先级**
 *
 * 契约 §11 第 5 项：「后台『违规记录查询』页面能看到该条记录」。
 * 数据源 `GET /api/records`（契约 §6.4），分页条用响应里的 `total`。
 * 「发送提醒」调 `POST /api/notify`（契约 §6.3，v1.2 起入参含 `id`）。
 *
 * 筛选项见 component-inventory.md §4.2；违规/提醒色映射严按 design-tokens.md §3.3①②。
 */
import { computed, onMounted } from 'vue'

import DataCard from '@/components/common/DataCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilterCard from '@/components/common/FilterCard.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import NotifyPill from '@/components/domain/NotifyPill.vue'
import PlateTag from '@/components/domain/PlateTag.vue'
import RuleHitPill from '@/components/domain/RuleHitPill.vue'
import { NOTIFY_STATUS, VTYPE } from '@/types/contract'
import { useRecordsStore } from '@/stores/records'
import { formatDateTime } from '@/utils/format'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'

const store = useRecordsStore()

/** 筛选表单的本地副本，点「查询」才写回 store，避免边输边过滤看不清状态 */
const form = computed(() => store.filters)

const notifyingId = ref<number | null>(null)

const vtypeOptions = [VTYPE.新能源, VTYPE.燃油]
const notifyOptions = [NOTIFY_STATUS.未提醒, NOTIFY_STATUS.已提醒, NOTIFY_STATUS.失败]

/** 违规类型下拉（文案与 design-tokens.md §3.3① 一致） */
const ruleOptions = [
  { value: 1, label: '燃油占位' },
  { value: 2, label: '异常占位' },
  { value: 3, label: '充满未移车' },
  { value: 0, label: '正常充电' },
]

const filteredCount = computed(() => store.filteredItems.length)

onMounted(() => {
  void store.load()
})

async function handleSearch() {
  await store.search()
}

async function handleReset() {
  store.resetFilters()
  await store.search()
}

async function handlePageChange(page: number, size: number) {
  await store.changePage(page, size)
}

async function handleNotify(row: { id: number | null; plate: string }) {
  if (row.id === null) {
    ElMessage.warning('该记录尚无 id，无法发送提醒')
    return
  }
  notifyingId.value = row.id
  try {
    await store.sendNotify(row.id)
    ElMessage.success(`已向 ${row.plate} 发送提醒（沙箱）`)
  } catch {
    // 错误提示已由 http 拦截器统一弹出
  } finally {
    notifyingId.value = null
  }
}
</script>

<template>
  <div class="page-container">
    <PageHeader
      title="违规记录查询"
      description="数据来自 occupation_record 表；命中即落库，同桩同规则且未提醒的记录会被复用为一条"
    >
      <template #actions>
        <el-button :loading="store.loading" @click="store.load()">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
      </template>
    </PageHeader>

    <FilterCard :loading="store.loading" @search="handleSearch" @reset="handleReset">
      <el-form-item label="车牌">
        <el-input
          v-model="form.plate"
          class="mono"
          placeholder="如 京A12345"
          clearable
          style="width: 160px"
        />
      </el-form-item>

      <el-form-item label="车型">
        <el-select v-model="form.vtype" placeholder="全部" clearable style="width: 120px">
          <el-option v-for="v in vtypeOptions" :key="v" :label="v" :value="v" />
        </el-select>
      </el-form-item>

      <el-form-item label="桩 ID">
        <el-input
          v-model="form.pile_id"
          class="mono"
          placeholder="如 PILE-001"
          clearable
          style="width: 150px"
        />
      </el-form-item>

      <el-form-item label="命中规则">
        <el-select v-model="form.rule_hit" placeholder="全部" clearable style="width: 140px">
          <el-option v-for="r in ruleOptions" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
      </el-form-item>

      <el-form-item label="提醒状态">
        <el-select
          v-model="form.notify_status"
          placeholder="全部"
          clearable
          style="width: 120px"
        >
          <el-option v-for="s in notifyOptions" :key="s" :label="s" :value="s" />
        </el-select>
      </el-form-item>

      <el-form-item label="命中时间">
        <el-date-picker
          v-model="form.timeRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
      </el-form-item>
    </FilterCard>

    <el-alert
      v-if="store.hasFilters"
      class="records__hint"
      type="info"
      :closable="false"
      show-icon
      :title="`已启用筛选：本页 ${filteredCount} / ${store.rawItems.length} 条命中。⚠️ 契约 §6.4 已定义服务端筛选参数，但后端尚未实现，故当前筛选仅作用于本页；分页总数仍为服务端返回的全表 total。后端就绪后此提示条将移除。`"
    />

    <DataCard
      title="违规记录"
      :total="store.total"
      :page="store.page"
      :size="store.size"
      :loading="store.loading"
      :show-pagination="true"
      @page-change="handlePageChange"
    >
      <template #tools>
        <StatusTag prefix="info">共 {{ store.total }} 条</StatusTag>
      </template>

      <el-table
        v-loading="store.loading"
        :data="store.filteredItems"
        stripe
        style="width: 100%"
        empty-text=" "
      >
        <el-table-column prop="id" label="ID" width="80">
          <template #default="{ row }">
            <span class="tabular">{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="车牌" width="130">
          <template #default="{ row }">
            <span class="mono cell-strong">{{ row.plate }}</span>
          </template>
        </el-table-column>

        <el-table-column label="车型" width="100">
          <template #default="{ row }">
            <PlateTag :vtype="row.vtype" />
          </template>
        </el-table-column>

        <el-table-column label="桩 ID" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.pile_id ?? '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="命中规则" width="140">
          <template #default="{ row }">
            <RuleHitPill :rule-hit="row.rule_hit" />
          </template>
        </el-table-column>

        <el-table-column label="命中时间" min-width="180">
          <template #default="{ row }">
            <span class="mono">{{ formatDateTime(row.occur_time) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="提醒状态" width="110">
          <template #default="{ row }">
            <NotifyPill :status="row.notify_status" />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              :loading="notifyingId === row.id"
              :disabled="row.notify_status === NOTIFY_STATUS.已提醒"
              @click="handleNotify(row)"
            >
              发送提醒
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <EmptyState
            compact
            :description="
              store.hasFilters
                ? '当前页没有符合筛选条件的记录'
                : '暂无违规记录。先调用 POST /api/judge 产生一条，再回来刷新'
            "
          />
        </template>
      </el-table>
    </DataCard>
  </div>
</template>

<style scoped>
.records__hint {
  margin-bottom: var(--space-4);
}

.cell-strong {
  font-weight: var(--font-weight-medium);
}
</style>
