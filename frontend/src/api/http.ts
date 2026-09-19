/**
 * HTTP 客户端 —— 统一的 axios 实例。
 *
 * 开发期由 Vite proxy 把 `/api` 转发到 `127.0.0.1:8000`（见 vite.config.ts），
 * 所以 baseURL 留空即可；生产构建同样走同源相对路径。
 */

import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

/** 统一的错误文案提取，避免每处 catch 都写一遍。 */
export function extractErrorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      // FastAPI 校验错误：detail 是数组
      const first = detail[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
    if (err.code === 'ECONNABORTED') return '请求超时，请确认后端服务已启动'
    if (!err.response) return '无法连接后端服务，请确认已启动 127.0.0.1:8000'
    return `请求失败（HTTP ${err.response.status}）`
  }
  return err instanceof Error ? err.message : '未知错误'
}

// 响应拦截：统一弹出错误提示，调用方仍可 catch 做局部处理
http.interceptors.response.use(
  (resp) => resp,
  (err: unknown) => {
    ElMessage.error(extractErrorMessage(err))
    return Promise.reject(err)
  },
)
