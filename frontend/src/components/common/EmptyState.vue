<script setup lang="ts">
/**
 * EmptyState —— 空状态（component-inventory.md §2）
 *
 * 第 2 周改动（任务 6.3 / 6.4 的落地）：插画由 `el-empty` 自带图换成**设计侧正式素材**
 * （`docs/design/assets/illustrations/`，基准 160×120 等比缩放）。
 * 依据 `component-inventory.md` §6.5：「素材目录里的是正式版，前端实现时用素材替换」。
 *
 * ⚠️ 三张插画**语义不同**，必须按空态的**触发原因**选，不能一律用「暂无数据」：
 *   - `no-data`      通用：数据本身为空（台账没录、桩没配）
 *   - `no-record`    违规记录为空（规则 ④ 正常充电不落库，为空是正常状态）
 *   - `search-empty` 筛选条件把数据滤空了（引导「重置筛选」而非「去新增」）
 * 混用会让演示时看不出系统到底是否正常。
 */
import noData from '@/assets/illustrations/empty-state-no-data.svg'
import noRecord from '@/assets/illustrations/empty-state-no-record.svg'
import searchEmpty from '@/assets/illustrations/empty-state-search-empty.svg'

type IllustrationKey = 'no-data' | 'no-record' | 'search-empty'

const ILLUSTRATIONS: Record<IllustrationKey, string> = {
  'no-data': noData,
  'no-record': noRecord,
  'search-empty': searchEmpty,
}

const props = withDefaults(
  defineProps<{
    description?: string
    /** 紧凑模式：嵌在表格里时用小尺寸 */
    compact?: boolean
    /** 插画语义，按空态触发原因选，默认「暂无数据」 */
    illustration?: IllustrationKey
  }>(),
  { description: '暂无数据', compact: false, illustration: 'no-data' },
)
</script>

<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <img
      class="empty-state__art"
      :src="ILLUSTRATIONS[props.illustration]"
      :width="compact ? 96 : 160"
      :height="compact ? 72 : 120"
      alt=""
    />
    <p class="empty-state__desc">{{ props.description }}</p>
    <div v-if="$slots.default" class="empty-state__actions">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  padding: var(--space-6) 0;
  text-align: center;
}

.empty-state--compact {
  padding: var(--space-4) 0;
}

.empty-state__art {
  display: block;
  margin: 0 auto var(--space-3);
}

.empty-state__desc {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

.empty-state__actions {
  margin-top: var(--space-3);
}
</style>
