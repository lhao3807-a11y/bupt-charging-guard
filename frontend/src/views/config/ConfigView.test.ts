import { afterEach, describe, expect, it, vi } from 'vitest'
import { mountView, flush } from '@/test/memoryHost'
import ConfigView from './ConfigView.vue'

const rows = () => [
  { key: 'full_timeout_min', value: '30', note: '充满超时阈值' },
  { key: 'abnormal_park_min', value: '40', note: '异常占位久停阈值' },
]
const unmounts: Array<() => void> = []
function mount(source?: Parameters<typeof mountView>[1]) {
  const view = mountView(ConfigView, source)
  unmounts.push(() => view.app.unmount())
  return view
}
afterEach(() => unmounts.splice(0).forEach((unmount) => unmount()))
describe('configuration view', () => {
  it('disables saving and shows no hardcoded threshold when not connected', async () => {
    const view = mount()
    await flush()
    expect(view.text()).toContain('参数数据待接入')
    expect(view.all('input')).toHaveLength(0)
    expect(view.button('保存并生效').props.disabled).toBe(true)
  })
  it('requires confirmation with the actual before/after values and preserves a cancelled draft', async () => {
    const write = vi.fn().mockResolvedValue(undefined)
    const view = mount({ loadConfig: vi.fn().mockResolvedValue(rows()), saveConfig: write })
    await flush()
    ;(view.all('input')[0]!.props.onInput as (value: number) => void)(45)
    await flush()
    await view.click('保存并生效')
    expect(view.text()).toContain('30 → 45')
    expect(write).not.toHaveBeenCalled()
    await view.click('取消')
    expect(view.all('input')[0]!.props.value).toBe(45)
    expect(write).not.toHaveBeenCalled()
    await view.click('撤销改动')
    expect(view.all('input')[0]!.props.value).toBe(30)
  })
  it('keeps a missing threshold absent and treats unknown parameters as readonly', async () => {
    const view = mount({
      loadConfig: vi
        .fn()
        .mockResolvedValue([rows()[0], { key: 'extra', value: '100', note: '只读' }]),
      saveConfig: vi.fn(),
    })
    await flush()
    expect(view.all('input')).toHaveLength(1)
    expect(view.text()).toContain('缺少参数：abnormal_park_min')
    expect(view.text()).toContain('100')
  })
  it('allows reading with no write connection but disables all editing', async () => {
    const view = mount({ loadConfig: vi.fn().mockResolvedValue(rows()) })
    await flush()
    expect(view.text()).toContain('参数保存待接入')
    expect(view.all('input').every((el) => el.props.disabled === true)).toBe(true)
    expect(view.button('保存并生效').props.disabled).toBe(true)
  })
  it('displays save failures inline and keeps the user input', async () => {
    const view = mount({
      loadConfig: vi.fn().mockResolvedValue(rows()),
      saveConfig: vi.fn().mockRejectedValue(new Error('offline')),
    })
    await flush()
    ;(view.all('input')[0]!.props.onInput as (value: number) => void)(45)
    await flush()
    await view.click('保存并生效')
    await view.click('确认保存')
    expect(view.text()).toContain('保存未能确认')
    expect(view.all('input')[0]!.props.value).toBe(45)
  })
})
