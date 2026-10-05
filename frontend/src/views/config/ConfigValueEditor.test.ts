/* eslint-disable vue/one-component-per-file -- Each fixture controls a separate table-cell test. */
import { describe, expect, it } from 'vitest'
import { defineComponent, h, reactive } from 'vue'
import { mountView, flush } from '@/test/memoryHost'
import ConfigValueEditor from './ConfigValueEditor.vue'
import type { ConfigKey } from '@/data/week2'

describe('configuration value inside a cached table row', () => {
  it('updates the displayed draft without needing the parent table row to rerender', async () => {
    const drafts = reactive<Partial<Record<ConfigKey, number | undefined>>>({
      full_timeout_min: 30,
    })
    const cachedCell = h(ConfigValueEditor, {
      configKey: 'full_timeout_min',
      original: '30',
      drafts,
      disabled: false,
    })
    const view = mountView(defineComponent({ setup: () => () => cachedCell }))
    try {
      expect(view.all('input')[0]!.props.value).toBe(30)
      drafts.full_timeout_min = 45
      await flush()
      expect(view.all('input')[0]!.props.value).toBe(45)
      drafts.full_timeout_min = undefined
      await flush()
      expect(view.all('input')[0]!.props.value).toBeUndefined()
      expect(view.text()).toContain('请输入大于 0 的整数')
    } finally {
      view.app.unmount()
    }
  })
  it('normalizes a cleared numeric widget to an absent draft without a default', async () => {
    const drafts = reactive<Partial<Record<ConfigKey, number | undefined>>>({
      full_timeout_min: 30,
    })
    const view = mountView(
      defineComponent({
        setup: () => () =>
          h(ConfigValueEditor, {
            configKey: 'full_timeout_min',
            original: '30',
            drafts,
            disabled: false,
            onUpdate: (value: number | undefined) => {
              drafts.full_timeout_min = value
            },
          }),
      }),
    )
    try {
      ;(view.all('input')[0]!.props.onInput as (value: null) => void)(null)
      await flush()
      expect(drafts.full_timeout_min).toBeUndefined()
      expect(view.all('input')[0]!.props.value).toBeUndefined()
      expect(view.text()).toContain('请输入大于 0 的整数')
    } finally {
      view.app.unmount()
    }
  })
})
