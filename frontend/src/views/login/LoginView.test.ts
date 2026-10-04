import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRenderer, defineComponent, h, nextTick } from 'vue'
import LoginView from './LoginView.vue'

/* eslint-disable vue/one-component-per-file -- Local Element Plus boundary stubs for the component regression tests. */

// A memory host runs the actual Vue component, event listeners and lifecycle
// without requiring a browser. Only the Element Plus form-validation boundary is stubbed.
interface HostNode {
  type: string
  props: Record<string, unknown>
  children: HostNode[]
  parent: HostNode | null
}
const node = (type: string): HostNode => ({ type, props: {}, children: [], parent: null })
const renderer = createRenderer<HostNode, HostNode>({
  createElement: node,
  createText: () => node('#text'),
  createComment: () => node('#comment'),
  insert(child, parent, anchor = null) {
    child.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    if (index < 0) parent.children.push(child)
    else parent.children.splice(index, 0, child)
  },
  remove(child) {
    if (child.parent) child.parent.children = child.parent.children.filter((item) => item !== child)
  },
  setText() {},
  setElementText() {},
  parentNode: (child) => child.parent,
  nextSibling(child) {
    const siblings = child.parent?.children ?? []
    return siblings[siblings.indexOf(child) + 1] ?? null
  },
  patchProp(element, key, _previous, value) { element.props[key] = value },
})

const unmounts: Array<() => void> = []
function mountLogin(validate = vi.fn().mockResolvedValue(true)) {
  const app = renderer.createApp(LoginView)
  app.component('ElForm', defineComponent({
    inheritAttrs: false,
    setup(_props, { attrs, slots, expose }) {
      expose({ validate })
      return () => h('form', attrs, slots.default?.())
    },
  }))
  app.component('ElButton', defineComponent({
    inheritAttrs: false,
    props: { nativeType: { type: String, default: 'button' } },
    setup(props, { attrs, slots }) {
      return () => h('button', { ...attrs, type: props.nativeType }, slots.default?.())
    },
  }))
  for (const name of ['ElFormItem', 'ElInput', 'ElCheckbox', 'ElAlert']) {
    app.component(name, defineComponent({
      setup(_props, { attrs, slots }) { return () => h('div', attrs, slots.default?.()) },
    }))
  }
  const root = node('root')
  app.mount(root)
  const find = (type: string, from = root): HostNode | undefined => {
    if (from.type === type && (type !== 'button' || from.props.type === 'submit')) return from
    for (const child of from.children) {
      const result = find(type, child)
      if (result) return result
    }
  }
  const submit = () => (find('form')!.props.onSubmit as (event: unknown) => unknown)({ preventDefault() {} })
  const click = () => {
    // A native submit button dispatches click, followed by the form's submit.
    const handler = find('button')!.props.onClick as (() => unknown) | undefined
    handler?.()
    return submit()
  }
  unmounts.push(() => app.unmount())
  return { app, validate, submit, click, button: () => find('button')! }
}
async function flush() { await Promise.resolve(); await Promise.resolve(); await nextTick() }

beforeEach(() => {
  vi.useFakeTimers()
  vi.stubGlobal('window', { setTimeout, clearTimeout })
})
afterEach(() => {
  unmounts.splice(0).forEach((unmount) => unmount())
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('login visual skeleton', () => {
  it('a native submit button validates and starts its loading state exactly once', async () => {
    const login = mountLogin()
    await login.click()
    await flush()
    expect(login.validate).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(1)
    expect(login.button().props.disabled).toBe(true)
  })

  it('ignores another submit while validation is still pending', async () => {
    const login = mountLogin(vi.fn(() => new Promise(() => {})))
    login.submit()
    login.submit()
    await flush()
    expect(login.validate).toHaveBeenCalledTimes(1)
  })

  it('allows correction after failed validation without scheduling a submission', async () => {
    const login = mountLogin(vi.fn().mockRejectedValue(new Error('invalid')))
    await login.submit()
    await flush()
    expect(vi.getTimerCount()).toBe(0)
    expect(login.button().props.disabled).toBe(false)
  })

  it('cancels the pending loading timer when leaving the page', async () => {
    const login = mountLogin()
    await login.submit()
    await flush()
    login.app.unmount()
    expect(vi.getTimerCount()).toBe(0)
    unmounts.pop()
  })

  it('does not schedule a submission if validation finishes after leaving the page', async () => {
    let resolveValidation!: (valid: boolean) => void
    const login = mountLogin(vi.fn(() => new Promise<boolean>((resolve) => { resolveValidation = resolve })))
    login.submit()
    login.app.unmount()
    unmounts.pop()
    resolveValidation(true)
    await flush()
    expect(vi.getTimerCount()).toBe(0)
  })
})
