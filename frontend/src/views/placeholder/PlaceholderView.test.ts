import { describe, expect, it } from 'vitest'
import { mountView } from '@/test/memoryHost'
import PlaceholderView from './PlaceholderView.vue'

describe('reserved page copy', () => {
  it('reflects the opened still-frame preview and the week-three capture integration plan', () => {
    const view = mountView(PlaceholderView, undefined, {
      title: '实时识别预览',
      reserved: true,
      milestone: '第 3 周',
    })

    expect(view.text()).toContain('静态截图预览已开放')
    expect(view.text()).toContain('真实采集联调计划第 3 周完成')
    expect(view.text()).not.toContain('第 1 周')
    view.app.unmount()
  })
})
