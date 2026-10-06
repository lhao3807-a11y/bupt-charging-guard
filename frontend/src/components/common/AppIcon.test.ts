/**
 * 官方图标集「逐处收口」守卫（任务 6.4 的机器可查断言）
 *
 * 为什么要写这条：任务书 6.4 的验收是「16 个正式图标落到前端，替换 Element Plus 临时图标」，
 * 而 2026-10-04 的合并审查留了一句准确的话 ——
 * **「不能把『文件已复制』等同于『逐处替换』」**。
 * 把 18 个 SVG 拷进 `src/assets/icons/` 很容易，难的是证明每一个都真的被用在业务位置。
 * 本文件的判据就是那句原话的机械化：**图标目录里的每个文件，都必须在 `src` 里被按名字引用过**。
 *
 * 两条边界（避免这条断言变成自欺）：
 *  1. **不扫 `assets/icons/` 自身**，否则「文件存在」就自动等于「被引用」。
 *  2. **不扫测试文件**，否则在被测文件里写个字符串就能让它变绿。
 * 另外配一条反例，证明这个判据不是恒真（恒真的断言等于没有断言）。
 */
// @vitest-environment node
import { readFileSync, readdirSync } from 'node:fs'
import { join, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

/** 图标文件所在目录（`frontend/src/assets/icons/`）。 */
const ICON_DIR = fileURLToPath(new URL('../../assets/icons/', import.meta.url))
/** 本文件位置即 `src/` —— 扫描范围是整个 `src`。 */
const SRC_DIR = fileURLToPath(new URL('../../', import.meta.url))

/** 递归收集 `src` 下所有 `.ts` / `.vue`（排除测试文件与图标目录自身）。 */
function collectSources(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      const relative = full.slice(SRC_DIR.length).split(sep).join('/')
      if (relative === 'assets/icons') continue // 边界①：不能自己证明自己
      out.push(...collectSources(full))
      continue
    }
    if (!/\.(ts|vue)$/.test(entry.name)) continue
    if (entry.name.endsWith('.test.ts')) continue // 边界②：测试文件不算引用
    out.push(full)
  }
  return out
}

function readAll(paths: string[]): string {
  return paths.map((path) => readFileSync(path, 'utf8')).join('\n')
}

/** 判据本体：返回「在 src 里找不到任何引用」的图标名。单独拆出来是为了能被反例打到。 */
function unreferenced(icons: string[], sources: string): string[] {
  return icons.filter((name) => !sources.includes(name))
}

const iconNames = readdirSync(ICON_DIR)
  .filter((name) => name.endsWith('.svg'))
  .map((name) => name.replace(/\.svg$/, ''))
  .sort()
const sourcePaths = collectSources(SRC_DIR)
const sourceText = readAll(sourcePaths)

describe('官方图标集逐处收口（任务 6.4）', () => {
  it('keeps exactly the 18 delivered icon files in the frontend', () => {
    expect(iconNames).toHaveLength(18)
    expect(iconNames).toContain('icon-edit')
    expect(iconNames).toContain('icon-delete')
    expect(iconNames).toContain('icon-send')
    expect(iconNames).toContain('icon-rule-fuel-occupy')
    expect(iconNames).toContain('icon-rule-abnormal-park')
    expect(iconNames).toContain('icon-rule-full-not-moved')
    expect(iconNames).toContain('icon-rule-normal')
  })

  it('references every icon somewhere in src, so none of them is just a copied file', () => {
    expect(sourcePaths.length).toBeGreaterThan(10)
    expect(unreferenced(iconNames, sourceText)).toEqual([])
  })

  it('has no Element Plus icon import left, in code or in the entry', () => {
    const importers = sourcePaths.filter((path) =>
      /from\s+['"]@element-plus\/icons-vue['"]/.test(readFileSync(path, 'utf8')),
    )
    expect(importers).toEqual([])
  })

  it('would catch an icon that nobody uses (so the check above is not vacuous)', () => {
    expect(unreferenced(['icon-nav-vehicle', 'icon-not-shipped-yet'], sourceText)).toEqual([
      'icon-not-shipped-yet',
    ])
  })
})
