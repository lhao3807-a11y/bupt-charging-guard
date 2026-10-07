import { AxiosError } from 'axios'
import { describe, expect, it } from 'vitest'
import { extractErrorMessage } from './http'

describe('HTTP error copy', () => {
  it('does not claim that a timeout means the service is stopped', () => {
    expect(extractErrorMessage(new AxiosError('timeout', 'ECONNABORTED'))).toBe(
      '请求超时，请稍后重试',
    )
  })
  it('keeps a connection error useful without exposing a development port', () => {
    expect(extractErrorMessage(new AxiosError('offline', 'ERR_NETWORK'))).toBe(
      '无法连接服务，请确认后端已启动',
    )
  })
})
