/**
 * 展示层格式化工具。
 *
 * 时间一律走 `formatDateTime`，保证 6 页格式统一（contract 里是 ISO 8601 字符串）。
 */

/** ISO 8601 → `YYYY-MM-DD HH:mm:ss`；空值显示占位符。 */
export function formatDateTime(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return fallback
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  )
}

/** ISO 8601 → `YYYY-MM-DD`。 */
export function formatDate(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return fallback
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * 手机号脱敏：`138****6621`。
 *
 * ⚠️ 契约未规定此项，属**展示层**处理（仅改显示、不改字段）。
 * 见 component-inventory.md §4.1「待吕浩确认的 2 处」第 1 条。
 * 经与 H 讨论确认后如需关闭，把此函数改为直接返回原值即可。
 */
export function maskPhone(phone: string | null | undefined, fallback = '—'): string {
  if (!phone) return fallback
  const s = String(phone).trim()
  if (s.length < 7) return s
  return `${s.slice(0, 3)}****${s.slice(-4)}`
}

/** `[x, y, w, h]` → `x,y · w×h`，用于第 3/6 页展示 bbox。 */
export function formatBbox(bbox: number[] | null | undefined, fallback = '—'): string {
  if (!bbox || bbox.length !== 4) return fallback
  const [x, y, w, h] = bbox
  return `${x},${y} · ${w}×${h}`
}
