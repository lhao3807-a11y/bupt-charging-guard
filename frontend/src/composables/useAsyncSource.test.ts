import { describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useAsyncSource } from './useAsyncSource'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { resolve, promise }
}

describe('optional week two data source', () => {
  it('has no invented data and makes no call when no source is connected', async () => {
    const source = useAsyncSource<number[], string>(undefined)
    await source.load('空闲')
    expect(source.available).toBe(false)
    expect(source.data.value).toBeNull()
    expect(source.loading.value).toBe(false)
    expect(source.error.value).toBe('')
  })

  it('distinguishes a loaded empty list from an unconnected source', async () => {
    const source = useAsyncSource(vi.fn().mockResolvedValue([]))
    await source.load(undefined)
    expect(source.available).toBe(true)
    expect(source.data.value).toEqual([])
  })

  it('accepts only the latest result when filter requests finish out of order', async () => {
    const first = deferred<number[]>()
    const second = deferred<number[]>()
    const read = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const source = useAsyncSource<number[], string>(read)
    const a = source.load('空闲')
    const b = source.load('已充满')
    second.resolve([2])
    await b
    first.resolve([1])
    await a
    expect(source.data.value).toEqual([2])
    expect(source.loading.value).toBe(false)
  })

  it('clears stale data on failure and allows an explicit retry', async () => {
    const read = vi
      .fn()
      .mockResolvedValueOnce([1])
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce([2])
    const source = useAsyncSource<number[], void>(read)
    await source.load(undefined)
    await source.load(undefined)
    expect(source.data.value).toBeNull()
    expect(source.error.value).toBe('offline')
    expect(source.loading.value).toBe(false)
    await source.load(undefined)
    expect(source.data.value).toEqual([2])
    expect(source.error.value).toBe('')
  })

  it('ignores a response after the view scope is disposed', async () => {
    const pending = deferred<number[]>()
    const scope = effectScope()
    const source = scope.run(() => useAsyncSource<number[], void>(() => pending.promise))!
    const request = source.load(undefined)
    scope.stop()
    pending.resolve([1])
    await request
    expect(source.data.value).toBeNull()
  })
})
