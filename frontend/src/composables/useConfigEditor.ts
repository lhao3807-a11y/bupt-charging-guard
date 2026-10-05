import { computed, getCurrentScope, onScopeDispose, reactive, ref, shallowRef, watch } from 'vue'
import { useAsyncSource } from './useAsyncSource'
import { CONFIG_KEYS } from '@/data/week2'
import type { ConfigChange, ConfigKey, Week2DataSource } from '@/data/week2'
import type { SystemConfig } from '@/types/contract'

export function isConfigKey(key: string): key is ConfigKey {
  return CONFIG_KEYS.some((known) => known === key)
}
const positiveInteger = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value > 0
export const configValueError = (value: unknown): string | undefined =>
  positiveInteger(value) ? undefined : '请输入大于 0 的整数'
const parsedValue = (value: string) => (positiveInteger(Number(value)) ? Number(value) : undefined)

export function useConfigEditor(source?: Week2DataSource) {
  const state = useAsyncSource<SystemConfig[], void>(source?.loadConfig?.bind(source))
  const drafts = reactive<Partial<Record<ConfigKey, number | undefined>>>({})
  const saving = ref(false)
  const confirming = ref(false)
  const pending = shallowRef<readonly ConfigChange[]>([])
  const notice = ref<{ tone: 'success' | 'error' | 'warning'; text: string } | null>(null)
  let disposed = false
  if (getCurrentScope())
    onScopeDispose(() => {
      disposed = true
    })

  function restoreDrafts() {
    for (const key of CONFIG_KEYS) delete drafts[key]
    for (const row of state.data.value ?? [])
      if (isConfigKey(row.key)) drafts[row.key] = parsedValue(row.value)
  }
  watch(state.data, restoreDrafts, { flush: 'sync' })
  const dirty = computed(() =>
    (state.data.value ?? []).some(
      (row) => isConfigKey(row.key) && drafts[row.key] !== parsedValue(row.value),
    ),
  )
  const validation = computed(() => {
    const result: Partial<Record<ConfigKey, string>> = {}
    for (const row of state.data.value ?? [])
      if (isConfigKey(row.key)) {
        const message = configValueError(drafts[row.key])
        if (message) result[row.key] = message
      }
    return result
  })
  const changes = computed<ConfigChange[]>(() =>
    (state.data.value ?? []).flatMap((row) => {
      if (!isConfigKey(row.key)) return []
      const after = drafts[row.key]
      return positiveInteger(after) && after !== parsedValue(row.value)
        ? [{ key: row.key, before: row.value, after }]
        : []
    }),
  )
  const writable = !!source?.saveConfig && state.available
  const canSave = computed(
    () =>
      writable &&
      !disposed &&
      state.data.value !== null &&
      dirty.value &&
      !Object.keys(validation.value).length &&
      !state.loading.value &&
      !saving.value &&
      !confirming.value,
  )
  const confirmationText = computed(
    () =>
      pending.value
        .map((change) => `${change.key}：${change.before} → ${change.after} 分钟`)
        .join('；') + '。调整将影响规则②或③的判定，请确认调整时机。',
  )

  async function reload() {
    if (dirty.value || saving.value || confirming.value) return false
    return state.load(undefined)
  }
  function undo() {
    if (saving.value || confirming.value) return
    restoreDrafts()
    notice.value = null
  }
  function prepareSave() {
    if (!canSave.value) return false
    pending.value = changes.value.map((change) => Object.freeze({ ...change }))
    confirming.value = true
    notice.value = null
    return true
  }
  function cancelSave() {
    if (saving.value) return
    confirming.value = false
    pending.value = []
  }
  async function confirmSave() {
    if (!confirming.value || saving.value || !source?.saveConfig || disposed) return false
    saving.value = true
    const snapshot = pending.value
    try {
      await source.saveConfig(snapshot)
      if (disposed) return false
      confirming.value = false
      pending.value = []
      const reloaded = await state.load(undefined)
      if (disposed) return false
      notice.value = reloaded
        ? { tone: 'success', text: '参数已保存，已重新读取当前值' }
        : { tone: 'warning', text: '保存请求已完成，但重新读取失败，请刷新核对当前值' }
      return reloaded
    } catch {
      if (disposed) return false
      confirming.value = false
      pending.value = []
      notice.value = { tone: 'error', text: '保存未能确认，已保留输入，请检查连接后重试' }
      return false
    } finally {
      if (!disposed) saving.value = false
    }
  }
  return {
    ...state,
    drafts,
    saving,
    confirming,
    notice,
    dirty,
    validation,
    changes,
    writable,
    canSave,
    confirmationText,
    reload,
    undo,
    prepareSave,
    cancelSave,
    confirmSave,
  }
}
