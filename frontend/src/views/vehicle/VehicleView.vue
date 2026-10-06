<script setup lang="ts">
/**
 * 第 1 页 · 车辆信息管理（契约 §1.1 #1）—— 风格样板页
 *
 * 表格列 = `vehicle` **全字段**（契约 §1.1 约定：表格列以对应表字段为准，不另发明）：
 *   车牌号 / 车型 / 车主 / 手机号 / 录入时间 + 操作列
 *
 * 车牌号、手机号、时间一律等宽字族 + tabular-nums（component-inventory.md §5）。
 * 车牌号是主键，**编辑态只读**。
 *
 * 数据来源：契约 §6.6 车辆 CRUD，筛选及分页均由服务端完成。
 */
import { computed, onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import DataCard from '@/components/common/DataCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FilterCard from '@/components/common/FilterCard.vue'
import FormDialog from '@/components/common/FormDialog.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PlateTag from '@/components/domain/PlateTag.vue'
import { VTYPE } from '@/types/contract'
import type { VType } from '@/types/contract'
import { useVehicleStore } from '@/stores/vehicle'
import { formatDateTime, maskPhone } from '@/utils/format'
import { ElMessage } from 'element-plus'

const store = useVehicleStore()

const vtypeOptions = [VTYPE.新能源, VTYPE.燃油]

const filters = computed(() => store.filters)

/* ------------------------------------------------------------------ 弹窗 */

const formVisible = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)

const form = reactive({
  plate: '',
  vtype: VTYPE.新能源 as VType,
  owner: '',
  phone: '',
})

const formTitle = computed(() => (formMode.value === 'create' ? '新增车辆' : '编辑车辆'))
const plateReadonly = computed(() => formMode.value === 'edit')

function openCreate() {
  formMode.value = 'create'
  form.plate = ''
  form.vtype = VTYPE.新能源
  form.owner = ''
  form.phone = ''
  formVisible.value = true
}

function openEdit(row: {
  plate: string
  vtype: VType
  owner: string | null
  phone: string | null
}) {
  formMode.value = 'edit'
  form.plate = row.plate
  form.vtype = row.vtype
  form.owner = row.owner ?? ''
  form.phone = row.phone ?? ''
  formVisible.value = true
}

const PLATE_RE = /^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$/
const PHONE_RE = /^1[3-9]\d{9}$/

function validate(): string | null {
  if (!PLATE_RE.test(form.plate.trim())) {
    return '车牌号格式不正确（示例：京A12345 / 京AD12345）'
  }
  if (!form.owner.trim()) return '请填写车主'
  if (!PHONE_RE.test(form.phone.trim())) return '手机号格式不正确（11 位，1 开头）'
  return null
}

async function handleSubmit() {
  if (submitting.value) return
  const err = validate()
  if (err) {
    ElMessage.warning(err)
    return
  }

  submitting.value = true
  try {
    if (formMode.value === 'create') {
      await store.create({
        plate: form.plate.trim(),
        vtype: form.vtype,
        owner: form.owner.trim(),
        phone: form.phone.trim(),
      })
      ElMessage.success(`已新增车辆 ${form.plate.trim()}`)
    } else {
      await store.update(form.plate, {
        vtype: form.vtype,
        owner: form.owner.trim(),
        phone: form.phone.trim(),
      })
      ElMessage.success(`已更新车辆 ${form.plate}`)
    }
    formVisible.value = false
  } catch {
    // HTTP 拦截器提示；保留表单供修正或重试。
  } finally {
    submitting.value = false
  }
}

/* ------------------------------------------------------------------ 删除 */

const confirmVisible = ref(false)
const pendingPlate = ref('')

const confirmMessage = computed(
  () =>
    `确认删除车辆 ${pendingPlate.value}？删除后该车的违规记录仍会保留，` +
    `但不再关联手机号，后续无法自动发送提醒。`,
)

function askRemove(row: { plate: string }) {
  pendingPlate.value = row.plate
  confirmVisible.value = true
}

const removing = ref(false)
async function handleRemove() {
  if (removing.value) return
  removing.value = true
  try {
    await store.remove(pendingPlate.value)
    ElMessage.success(`已删除车辆 ${pendingPlate.value}`)
    confirmVisible.value = false
  } catch {
    // HTTP 拦截器提示；保留确认弹窗。
  } finally {
    removing.value = false
  }
}

async function handleLoad() {
  await store.load().catch(() => undefined)
}
async function handleSearch() {
  await store.search().catch(() => undefined)
}
async function handleReset() {
  store.resetFilters()
  await handleSearch()
}
async function handlePageChange(p: number, s: number) {
  await store.changePage(p, s).catch(() => undefined)
}
onMounted(handleLoad)
</script>

<template>
  <div class="page-container">
    <PageHeader title="车辆信息管理" description="维护绑定车辆的车主与手机号，是自动提醒的数据基础">
      <template #actions>
        <el-button :loading="store.loading" @click="handleLoad">
          <AppIcon name="icon-refresh" :size="14" />
          <span>刷新</span>
        </el-button>
        <el-button type="primary" @click="openCreate">
          <AppIcon name="icon-plus" :size="14" />
          <span>新增车辆</span>
        </el-button>
      </template>
    </PageHeader>

    <FilterCard :loading="store.loading" @search="handleSearch" @reset="handleReset">
      <el-form-item label="车牌号">
        <el-input
          v-model="filters.plate"
          class="mono"
          placeholder="如 京A12345"
          clearable
          style="width: 160px"
        />
      </el-form-item>

      <el-form-item label="车型">
        <el-select v-model="filters.vtype" placeholder="全部" clearable style="width: 120px">
          <el-option v-for="v in vtypeOptions" :key="v" :label="v" :value="v" />
        </el-select>
      </el-form-item>

      <el-form-item label="车主">
        <el-input v-model="filters.owner" placeholder="车主姓名" clearable style="width: 140px" />
      </el-form-item>
    </FilterCard>

    <DataCard
      title="车辆列表"
      :total="store.total"
      :page="store.page"
      :size="store.size"
      @page-change="handlePageChange"
    >
      <el-table
        v-loading="store.loading"
        :data="store.items"
        stripe
        style="width: 100%"
        empty-text=" "
      >
        <el-table-column label="车牌号" width="140">
          <template #default="{ row }">
            <span class="mono cell-strong">{{ row.plate }}</span>
          </template>
        </el-table-column>

        <el-table-column label="车型" width="110">
          <template #default="{ row }">
            <PlateTag :vtype="row.vtype" />
          </template>
        </el-table-column>

        <el-table-column label="车主" min-width="120">
          <template #default="{ row }">{{ row.owner }}</template>
        </el-table-column>

        <el-table-column label="手机号" width="160">
          <template #default="{ row }">
            <span class="mono">{{ maskPhone(row.phone) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="录入时间" width="190">
          <template #default="{ row }">
            <span class="mono">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="openEdit(row)">
              <AppIcon name="icon-edit" :size="14" />
              <span>编辑</span>
            </el-button>
            <el-button text type="danger" @click="askRemove(row)">
              <AppIcon name="icon-delete" :size="14" />
              <span>删除</span>
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <EmptyState
            compact
            :illustration="store.hasFilters ? 'search-empty' : 'no-data'"
            :description="
              store.error
                ? '车辆加载失败，请点击刷新重试'
                : store.hasFilters
                  ? '没有符合筛选条件的车辆'
                  : '暂无车辆，点击右上角「新增车辆」添加'
            "
          >
            <el-button type="primary" @click="openCreate">新增车辆</el-button>
          </EmptyState>
        </template>
      </el-table>
    </DataCard>

    <!-- 新增 / 编辑共用弹窗；编辑态车牌只读（主键） -->
    <FormDialog
      v-model="formVisible"
      :title="formTitle"
      :submitting="submitting"
      confirm-text="保存"
      @submit="handleSubmit"
    >
      <el-form label-width="80px" @submit.prevent>
        <el-form-item label="车牌号" required>
          <el-input
            v-model="form.plate"
            class="mono"
            :readonly="plateReadonly"
            :disabled="plateReadonly"
            placeholder="如 京AD12345"
            maxlength="8"
          />
          <div v-if="plateReadonly" class="form-hint">车牌号是主键，不可修改</div>
        </el-form-item>

        <el-form-item label="车型" required>
          <el-radio-group v-model="form.vtype">
            <el-radio-button v-for="v in vtypeOptions" :key="v" :value="v">{{ v }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="车主" required>
          <el-input v-model="form.owner" placeholder="车主姓名" maxlength="50" />
        </el-form-item>

        <el-form-item label="手机号" required>
          <el-input v-model="form.phone" class="mono" placeholder="11 位手机号" maxlength="20" />
        </el-form-item>
      </el-form>
    </FormDialog>

    <ConfirmDialog
      v-model="confirmVisible"
      title="删除车辆"
      :submitting="removing"
      :message="confirmMessage"
      confirm-text="确认删除"
      @confirm="handleRemove"
    />
  </div>
</template>

<style scoped>
.cell-strong {
  font-weight: var(--font-weight-medium);
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: var(--line-height-base);
  margin-top: var(--space-1);
}
</style>
