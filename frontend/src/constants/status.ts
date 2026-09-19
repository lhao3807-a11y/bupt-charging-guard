/**
 * 违规/状态 → 设计令牌映射 —— 严按 docs/design/design-tokens.md §3.3
 *
 * **不许在此文件之外自选颜色**，也不许把十六进制写在组件里：
 * 全部返回 CSS 变量名，真正取值由 tokens.css 提供。
 */

import { NOTIFY_STATUS, PILE_STATUS, RULE_HIT } from '@/types/contract'
import type { NotifyStatus, PileStatus } from '@/types/contract'

/** 状态色四档前缀。 */
export type TokenPrefix = 'danger' | 'caution' | 'warning' | 'success' | 'info'

/** 状态令牌组：bg 底 / border 边 / text 字 / solid 实心。 */
export interface StateTokens {
  bg: string
  border: string
  text: string
  solid: string
}

/** 由前缀生成四档 CSS 变量名。 */
export function stateTokens(prefix: TokenPrefix): StateTokens {
  return {
    bg: `var(--state-${prefix}-bg)`,
    border: `var(--state-${prefix}-border)`,
    text: `var(--state-${prefix}-text)`,
    solid: `var(--state-${prefix}-solid)`,
  }
}

/** 违规类型 → 令牌前缀（design-tokens.md §3.3①）。 */
export const RULE_HIT_PREFIX: Record<number, TokenPrefix> = {
  [RULE_HIT.FUEL_OCCUPY]: 'danger', // 红
  [RULE_HIT.ABNORMAL_PARK]: 'caution', // 橙
  [RULE_HIT.FULL_NOT_MOVED]: 'warning', // 黄
  [RULE_HIT.NORMAL]: 'success', // 绿
}

/** 违规类型 → 中文名（与契约 §3.3 注释一致）。 */
export const RULE_HIT_LABEL: Record<number, string> = {
  [RULE_HIT.FUEL_OCCUPY]: '燃油占位',
  [RULE_HIT.ABNORMAL_PARK]: '异常占位',
  [RULE_HIT.FULL_NOT_MOVED]: '充满未移车',
  [RULE_HIT.NORMAL]: '正常充电',
}

/** 提醒状态 → 令牌前缀（design-tokens.md §3.3②）。 */
export const NOTIFY_STATUS_PREFIX: Record<NotifyStatus, TokenPrefix> = {
  [NOTIFY_STATUS.未提醒]: 'warning', // 黄（待处理）
  [NOTIFY_STATUS.已提醒]: 'success', // 绿
  [NOTIFY_STATUS.失败]: 'danger', // 红
}

/** 充电桩状态 → 令牌前缀（design-tokens.md §3.3③）。 */
export const PILE_STATUS_PREFIX: Record<PileStatus, TokenPrefix> = {
  [PILE_STATUS.空闲]: 'info', // 中性灰
  [PILE_STATUS.充电中]: 'primary' as TokenPrefix, // 主色蓝（特殊，见下）
  [PILE_STATUS.已充满]: 'caution', // 橙
}

/** 桩状态「充电中」用品牌主色，不属于状态色五档，单独给。 */
export const PRIMARY_TOKENS: StateTokens = {
  bg: 'var(--brand-primary-bg)',
  border: 'var(--brand-primary-border)',
  text: 'var(--brand-primary)',
  solid: 'var(--brand-primary)',
}

/** 违规类型取令牌组。 */
export function ruleHitTokens(ruleHit: number): StateTokens {
  return stateTokens(RULE_HIT_PREFIX[ruleHit] ?? 'info')
}

/** 提醒状态取令牌组。 */
export function notifyStatusTokens(status: NotifyStatus): StateTokens {
  return stateTokens(NOTIFY_STATUS_PREFIX[status] ?? 'info')
}

/** 桩状态取令牌组（「充电中」走品牌主色）。 */
export function pileStatusTokens(status: PileStatus): StateTokens {
  return status === PILE_STATUS.充电中
    ? PRIMARY_TOKENS
    : stateTokens(PILE_STATUS_PREFIX[status] ?? 'info')
}

/** 车型标签令牌（design-tokens.md §3.3④，取真实车牌底色）。 */
export const PLATE_TOKENS = {
  新能源: {
    bg: 'var(--plate-new-energy-bg)',
    border: 'var(--plate-new-energy-border)',
    text: 'var(--plate-new-energy-text)',
  },
  燃油: {
    bg: 'var(--plate-fuel-bg)',
    border: 'var(--plate-fuel-border)',
    text: 'var(--plate-fuel-text)',
  },
} as const

/** 按车型取车牌底色令牌。 */
export function plateTokens(vtype: string) {
  return vtype === '新能源' ? PLATE_TOKENS.新能源 : PLATE_TOKENS.燃油
}
