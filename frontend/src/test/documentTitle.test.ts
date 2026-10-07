import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('first paint document title', () => {
  it('uses the same site name as router navigation', () => {
    const html = readFileSync('index.html', 'utf8')
    expect(html).toContain('<title>桩点北邮防占系统</title>')
  })
})
