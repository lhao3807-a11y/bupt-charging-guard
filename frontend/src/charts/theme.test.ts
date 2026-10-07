import { beforeEach, describe, expect, it, vi } from 'vitest'

const { registerTheme } = vi.hoisted(() => ({ registerTheme: vi.fn() }))
vi.mock('echarts/core', () => ({ registerTheme }))

import { ensureChartTheme } from './theme'

describe('shared statistics theme', () => {
  beforeEach(() => registerTheme.mockClear())

  it('registers semantic colors once and reuses the theme name', () => {
    const read = (name: string) => `token:${name}`
    const name = ensureChartTheme(read)
    expect(ensureChartTheme(read)).toBe(name)
    expect(registerTheme).toHaveBeenCalledTimes(1)
    expect(registerTheme).toHaveBeenCalledWith(
      name,
      expect.objectContaining({
        color: [
          'token:--state-danger-solid',
          'token:--state-caution-solid',
          'token:--state-warning-solid',
          'token:--state-success-solid',
        ],
      }),
    )
  })
})
