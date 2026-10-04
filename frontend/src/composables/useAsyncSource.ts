import { getCurrentScope, onScopeDispose, ref, shallowRef } from 'vue'

/** Optional read boundary: null means unavailable/unread, [] means a real empty result. */
export function useAsyncSource<T, Q>(read: ((query: Q) => Promise<T>) | undefined) {
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref('')
  let requestId = 0
  let disposed = false
  if (getCurrentScope()) onScopeDispose(() => { disposed = true; requestId++ })

  async function load(query: Q): Promise<boolean> {
    if (!read || disposed) return false
    const id = ++requestId
    loading.value = true
    error.value = ''
    try {
      const result = await read(query)
      if (id !== requestId) return false
      data.value = result
      return true
    } catch (cause) {
      if (id !== requestId) return false
      data.value = null
      error.value = cause instanceof Error ? cause.message : '读取失败，请重试'
      return false
    } finally {
      if (id === requestId) loading.value = false
    }
  }
  return { available: !!read, data, loading, error, load }
}
