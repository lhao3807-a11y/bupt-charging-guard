/* eslint-disable vue/one-component-per-file -- 这里的宿主组件只是把 prop 透传给被测组件。 */
/**
 * RuleHitPill 规则图标守卫（任务 6.4）
 *
 * 规则图标（`icon-rule-*`）的业务位置是**第 2 页表格的规则列**（component-inventory.md §6.2
 * 写着「规则图标自带语义，可以直接给第 2 页表格的规则列用」）。
 * 这里锁住三件事，防止以后被「顺手改回圆点」：
 *  1. 四条规则各自渲染**对应**的图标 —— 判据不是「有没有图标」，而是
 *     渲染出来的图形内容与 `assets/icons/<该规则图标>.svg` 一致；
 *  2. 有图标时**不再画圆点**（图标 + 圆点同时出现就是重复装饰）；
 *  3. 文字仍在（图标是装饰，语义由文案承担 —— `mask` 渲染读不到 SVG 的 `aria-label`）。
 *
 * 踩过的坑（两个，别改回去）：
 *  1. `import.meta.glob(..., '?url')` 在 vitest 下会把小 SVG **内联成 data URL**，
 *     所以断言里**取不到文件名**，只能把 data URL 解码后比内容。
 *  2. 本文件跑在自定义的 memory-host 环境里（`vitest.config.ts`），
 *     `import.meta.url` **不是** `file:` 协议，`fileURLToPath` 会直接抛错 ——
 *     要读图标文件内容就用 `?raw` glob，不要用 `node:fs`。
 */
import { defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'

import { mountView } from '@/test/memoryHost'
import { RULE_HIT } from '@/types/contract'
import RuleHitPill from './RuleHitPill.vue'

/** 图标源码（`?raw`），用来取每个图标的比对基准。 */
const ICON_SOURCE = import.meta.glob('../../assets/icons/*.svg', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

const unmounts: Array<() => void> = []
afterEach(() => unmounts.splice(0).forEach((unmount) => unmount()))

/** `mountView` 只接受数据源，不给 props —— 用一个透传宿主把 ruleHit 递进去。 */
const Host = defineComponent({
  props: { ruleHit: { type: Number, required: true } },
  setup: (props) => () => h(RuleHitPill, { ruleHit: props.ruleHit }),
})

function mount(ruleHit: number) {
  const view = mountView(Host, undefined, { ruleHit })
  unmounts.push(() => view.app.unmount())
  return view
}

/** 取渲染树里 AppIcon 输出的 `--icon-url`，解码成可直接比对的字符串。 */
function renderedIcon(view: ReturnType<typeof mount>): string {
  const style = view
    .all('span')
    .map((el) => el.props.style as Record<string, string> | undefined)
    .find((candidate) => candidate?.['--icon-url'] !== undefined)
  expect(style).toBeDefined()
  return decodeURIComponent(String(style?.['--icon-url']))
}

/** 从图标源码里取它的 `aria-label` —— 每个规则图标的这条文案与规则语义一一对应。 */
function markerOf(icon: string): string {
  const svg = Object.entries(ICON_SOURCE).find(([path]) => path.endsWith(`/${icon}.svg`))?.[1]
  if (!svg) throw new Error(`图标 ${icon} 不在 assets/icons 里`)
  const label = svg.match(/aria-label="([^"]+)"/)?.[1]
  if (!label) throw new Error(`图标 ${icon} 里没有 aria-label，无法作为比对基准`)
  return label
}

const EXPECTED: Array<[number, string]> = [
  [RULE_HIT.FUEL_OCCUPY, 'icon-rule-fuel-occupy'],
  [RULE_HIT.ABNORMAL_PARK, 'icon-rule-abnormal-park'],
  [RULE_HIT.FULL_NOT_MOVED, 'icon-rule-full-not-moved'],
  [RULE_HIT.NORMAL, 'icon-rule-normal'],
]

describe('rule hit pill icons', () => {
  it.each(EXPECTED)('rule_hit = %i shows the matching %s', (ruleHit, icon) => {
    expect(renderedIcon(mount(ruleHit))).toContain(markerOf(icon))
  })

  it('draws four different icons, not one reused four times', () => {
    const rendered = EXPECTED.map(([ruleHit]) => renderedIcon(mount(ruleHit)))
    expect(new Set(rendered).size).toBe(EXPECTED.length)
  })

  it('replaces the dot instead of stacking a glyph on top of it', () => {
    const dots = mount(RULE_HIT.FUEL_OCCUPY)
      .all('span')
      .filter((el) => String(el.props.class ?? '').includes('status-pill__dot'))
    expect(dots).toEqual([])
  })

  it('still shows the rule wording, so the icon is decoration and not the only meaning', () => {
    expect(mount(RULE_HIT.FULL_NOT_MOVED).text()).toContain('充满未移车')
    expect(mount(RULE_HIT.NORMAL).text()).toContain('正常充电')
  })
})
