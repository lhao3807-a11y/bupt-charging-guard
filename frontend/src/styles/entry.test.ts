import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('application CSS cascade', () => {
  it('loads design overrides after Element Plus defaults and before component overrides', () => {
    const entry = readFileSync(new URL('../main.ts', import.meta.url), 'utf8')
    const imports = [...entry.matchAll(/^import ['"]([^'"]+\.css)['"]/gm)].map((match) => match[1])
    const defaults = imports.indexOf('element-plus/dist/index.css')
    const design = imports.indexOf('@/styles/tokens.css')
    const components = imports.indexOf('@/styles/global.css')
    expect(defaults).toBeGreaterThanOrEqual(0)
    expect(design).toBeGreaterThan(defaults)
    expect(components).toBeGreaterThan(design)
  })
})
// @vitest-environment node
