/* eslint-disable vue/one-component-per-file -- These components stub only the Element Plus rendering boundary. */
import { createRenderer, defineComponent, h, inject, nextTick, provide } from 'vue'
import type { Component, InjectionKey, PropType } from 'vue'
import { WEEK2_DATA_SOURCE } from '@/data/week2'
import type { Week2DataSource } from '@/data/week2'

export interface HostNode {
  type: string
  text: string
  props: Record<string, unknown>
  children: HostNode[]
  parent: HostNode | null
}
const node = (type: string, text = ''): HostNode => ({ type, text, props: {}, children: [], parent: null })
const renderer = createRenderer<HostNode, HostNode>({
  createElement: node,
  createText: (text) => node('#text', text),
  createComment: (text) => node('#comment', text),
  insert(child, parent, anchor = null) {
    if (child.parent) child.parent.children = child.parent.children.filter((item) => item !== child)
    child.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    if (index < 0) parent.children.push(child)
    else parent.children.splice(index, 0, child)
  },
  remove(child) { if (child.parent) child.parent.children = child.parent.children.filter((item) => item !== child) },
  setText(el, text) { el.text = text },
  setElementText(el, text) { el.text = text; el.children = [] },
  parentNode: (child) => child.parent,
  nextSibling(child) {
    const siblings = child.parent?.children ?? []
    return siblings[siblings.indexOf(child) + 1] ?? null
  },
  patchProp(el, key, _previous, value) { el.props[key] = value },
})
const TABLE_ROWS: InjectionKey<() => Array<Record<string, unknown>>> = Symbol('table-rows')

export function mountView(view: Component, source?: Week2DataSource) {
  const app = renderer.createApp(view)
  if (source) app.provide(WEEK2_DATA_SOURCE, source)
  const wrapperNames = ['ElCard', 'ElButtonGroup', 'ElForm', 'ElFormItem', 'ElSkeleton', 'ElSkeletonItem', 'ElTag']
  for (const name of wrapperNames) app.component(name, defineComponent({
    inheritAttrs: false,
    setup(_props, { attrs, slots }) {
      return () => h('div', attrs, [slots.header?.(), slots.default?.(), slots.footer?.()])
    },
  }))
  app.component('ElButton', defineComponent({
    inheritAttrs: false,
    setup(_props, { attrs, slots }) { return () => h('button', attrs, slots.default?.()) },
  }))
  app.component('ElAlert', defineComponent({
    inheritAttrs: false,
    props: { title: String, description: String },
    setup(props, { attrs }) { return () => h('div', { ...attrs, role: 'alert' }, [props.title, props.description]) },
  }))
  app.component('ElDialog', defineComponent({
    props: { modelValue: Boolean, title: String },
    setup(props, { slots }) { return () => props.modelValue ? h('dialog', [props.title, slots.default?.(), slots.footer?.()]) : null },
  }))
  app.component('ElSelect', defineComponent({
    inheritAttrs: false,
    props: { modelValue: [String, Number] },
    emits: ['update:modelValue', 'change'],
    setup(props, { attrs, slots, emit }) {
      return () => h('select', { ...attrs, value: props.modelValue, onChange: (value: unknown) => {
        emit('update:modelValue', value); emit('change', value)
      } }, slots.default?.())
    },
  }))
  app.component('ElOption', defineComponent({
    props: { label: String, value: [String, Number] },
    setup(props) { return () => h('option', { value: props.value }, props.label) },
  }))
  app.component('ElInputNumber', defineComponent({
    inheritAttrs: false,
    props: { modelValue: Number },
    emits: ['update:modelValue'],
    setup(props, { attrs, emit }) {
      return () => h('input', { ...attrs, value: props.modelValue, onInput: (value: unknown) => emit('update:modelValue', value) })
    },
  }))
  app.component('ElTable', defineComponent({
    props: { data: Array as PropType<Array<Record<string, unknown>>> },
    setup(props, { attrs, slots }) {
      provide(TABLE_ROWS, () => props.data ?? [])
      return () => h('table', attrs, props.data?.length ? slots.default?.() : slots.empty?.())
    },
  }))
  app.component('ElTableColumn', defineComponent({
    props: { prop: String, label: String },
    setup(props, { slots }) {
      const rows = inject(TABLE_ROWS, () => [])
      return () => h('column', [props.label, ...rows().map((row, index) => h('cell',
        slots.default?.({ row, $index: index }) ?? String(row[props.prop ?? ''] ?? '')))])
    },
  }))
  const root = node('root')
  app.mount(root)
  function all(type: string, from = root): HostNode[] {
    return [...(from.type === type ? [from] : []), ...from.children.flatMap((child) => all(type, child))]
  }
  const text = (from = root): string => from.text + from.children.map((child) => text(child)).join('')
  const button = (label: string) => all('button').find((item) => text(item).trim() === label)!
  const click = async (label: string) => {
    const el = button(label)
    if (!el) throw new Error(`Missing button: ${label}`)
    if (el.props.disabled) throw new Error(`Disabled button: ${label}`)
    ;(el.props.onClick as () => void)?.()
    await flush()
  }
  return { app, root, all, text, button, click }
}
export async function flush() { for (let i = 0; i < 5; i++) await Promise.resolve(); await nextTick() }
