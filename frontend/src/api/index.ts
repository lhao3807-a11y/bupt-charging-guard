/**
 * 契约 §6 五个端点的封装。
 *
 * | 方法 | 路径 | 说明 |
 * |---|---|---|
 * | POST | /api/recognize | 输入帧 → 识别结果（stub 读标注） |
 * | POST | /api/judge | 识别结果 → 违规判定 |
 * | POST | /api/notify | 违规 → 短信沙箱（写库+日志） |
 * | GET  | /api/records | 后台查询违规记录（分页） |
 * | GET  | /api/health | 冒烟/健康检查 |
 */

import { http } from '@/api/http'
import type {
  FrameRef,
  HealthResp,
  NotifyReq,
  NotifyResp,
  RecognitionResult,
  RecordPage,
  RecordQuery,
  ViolationRecord,
} from '@/types/contract'

/** `POST /api/recognize` —— 输入帧 → 识别结果（契约 §6.1）。 */
export async function recognize(payload: FrameRef): Promise<RecognitionResult> {
  const { data } = await http.post<RecognitionResult>('/api/recognize', payload)
  return data
}

/**
 * `POST /api/judge` —— 识别结果 → 违规判定（契约 §6.2）。
 *
 * 命中即落库并返回带 `id` 的记录；**规则 ④（正常充电）返回 `null`**。
 */
export async function judge(payload: RecognitionResult): Promise<ViolationRecord | null> {
  const { data } = await http.post<ViolationRecord | null>('/api/judge', payload)
  return data
}

/** `POST /api/notify` —— 短信沙箱，按记录 id 更新提醒状态（契约 §6.3）。 */
export async function notify(payload: NotifyReq): Promise<NotifyResp> {
  const { data } = await http.post<NotifyResp>('/api/notify', payload)
  return data
}

/** `GET /api/records` —— 分页查询违规记录，按 `occur_time` 倒序（契约 §6.4）。 */
export async function fetchRecords(query: RecordQuery = {}): Promise<RecordPage> {
  const { data } = await http.get<RecordPage>('/api/records', { params: query })
  return data
}

/** `GET /api/health` —— 冒烟/健康检查。 */
export async function health(): Promise<HealthResp> {
  const { data } = await http.get<HealthResp>('/api/health')
  return data
}
