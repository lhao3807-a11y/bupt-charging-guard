import { afterEach, describe, expect, it, vi } from 'vitest'
import { navRoutes } from '@/router'
import { flush, mountView } from '@/test/memoryHost'
import PreviewView from './PreviewView.vue'

vi.mock('vue-router', () => ({
  createWebHistory: vi.fn(),
  createRouter: () => ({ afterEach: vi.fn() }),
}))

const unmounts: Array<() => void> = []

afterEach(() => {
  unmounts.splice(0).forEach((unmount) => unmount())
  vi.useRealTimers()
})

describe('latest-frame preview', () => {
  it('enables the navigation and polls the latest still image', async () => {
    vi.useFakeTimers()
    const view = mountView(PreviewView)
    unmounts.push(() => view.app.unmount())
    await flush()

    const previewRoute = navRoutes.find((route) => route.path === '/preview')
    expect(previewRoute?.meta?.reserved).toBeUndefined()
    expect(view.text()).toContain('每 3 秒读取一次')
    expect(view.text()).toContain('不接实时视频流')
    const image = () => view.all('img').find((item) => String(item.props.src).includes('/api/frame/latest'))
    const firstUrl = image()?.props.src
    expect(String(firstUrl)).toMatch(/^\/api\/frame\/latest\?ts=/)
    await vi.advanceTimersByTimeAsync(3_000)
    await flush()
    expect(image()?.props.src).not.toBe(firstUrl)
    vi.useRealTimers()
  })
})
