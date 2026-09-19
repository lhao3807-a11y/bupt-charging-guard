/**
 * 契约类型定义 —— 唯一事实源 docs/CONTRACT.md v1.2
 *
 * 本文件**手写对齐契约 §4 / §5**，不从后端代码生成。
 * 契约任何结构变动 → 先改 CONTRACT.md → 升版本号 → 再改这里。
 */

/* ------------------------------------------------------------------ 枚举 */

/** 车型，由绿牌/蓝牌判定（契约 §3.1）。 */
export const VTYPE = {
  新能源: '新能源',
  燃油: '燃油',
} as const
export type VType = (typeof VTYPE)[keyof typeof VTYPE]

/** 充电桩运行状态（契约 §3.2）。 */
export const PILE_STATUS = {
  空闲: '空闲',
  充电中: '充电中',
  已充满: '已充满',
} as const
export type PileStatus = (typeof PILE_STATUS)[keyof typeof PILE_STATUS]

/** 提醒状态（契约 §3.3）。 */
export const NOTIFY_STATUS = {
  未提醒: '未提醒',
  已提醒: '已提醒',
  失败: '失败',
} as const
export type NotifyStatus = (typeof NOTIFY_STATUS)[keyof typeof NOTIFY_STATUS]

/**
 * 违规规则编号（契约 §3.3）。
 * 1 燃油占位 / 2 异常占位 / 3 充满未移车 / 0 正常
 */
export const RULE_HIT = {
  /** 燃油车占位（蓝牌占充电位）—— 最严重 */
  FUEL_OCCUPY: 1,
  /** 异常占位（新能源未充电且久停） */
  ABNORMAL_PARK: 2,
  /** 充满未移车（充满超时未离场） */
  FULL_NOT_MOVED: 3,
  /** 正常充电（不提醒） */
  NORMAL: 0,
} as const
export type RuleHit = (typeof RULE_HIT)[keyof typeof RULE_HIT]

/* ------------------------------------------------------- 契约 §4 识别结果 */

/** 识别请求入参；`frame_ref` 为相对 `algo/samples/frames/` 的文件名。 */
export interface FrameRef {
  frame_ref: string
}

/** 识别结果，真实 CV 与识别桩 stub 返回同一结构（契约 §4）。 */
export interface RecognitionResult {
  plate: string
  vtype: VType
  /** 识别置信度，0~1 */
  confidence: number
  /** `[x, y, w, h]` */
  bbox: [number, number, number, number]
  /** ISO 8601 字符串 */
  frame_time: string
}

/* ------------------------------------------------- 契约 §5 违规记录 */

/** 违规记录，对应 `occupation_record`。 */
export interface ViolationRecord {
  /** 来自 `occupation_record.id`；新建时为 null */
  id: number | null
  plate: string
  vtype: VType
  /** 关联桩 ID */
  pile_id: string | null
  rule_hit: number
  occur_time: string
  notify_status: NotifyStatus
}

/* --------------------------------------------------- 契约 §6 请求 / 响应 */

/** `POST /api/notify` 请求体（v1.2 起入参含 `id`）。 */
export interface NotifyReq {
  id: number
  notify_status: NotifyStatus
}

/** `POST /api/notify` 响应体。 */
export interface NotifyResp {
  notify_status: NotifyStatus
}

/** `GET /api/records` 分页响应，`total` 供分页条使用（契约 §6.4）。 */
export interface RecordPage {
  items: ViolationRecord[]
  total: number
  page: number
  size: number
}

/** `GET /api/records` 查询参数。 */
export interface RecordQuery {
  page?: number
  size?: number
}

/** `GET /api/health` 响应体。 */
export interface HealthResp {
  status: string
}

/* --------------------------------------------------------- 契约 §3 数据表 */

/** `vehicle` 表（契约 §3.1）。 */
export interface Vehicle {
  plate: string
  vtype: VType
  owner: string
  phone: string
  created_at: string
}

/** `charging_pile` 表（契约 §3.2）。 */
export interface ChargingPile {
  pile_id: string
  status: PileStatus
  bound_plate: string | null
  start_time: string | null
  end_time: string | null
}

/** `system_config` 表（契约 §3.4）。 */
export interface SystemConfig {
  key: string
  value: string
  note: string
}
