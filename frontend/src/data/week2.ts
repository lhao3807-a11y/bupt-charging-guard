import type { InjectionKey } from 'vue'
import type { ChargingPile, PileStatus, SystemConfig } from '@/types/contract'

export const CONFIG_KEYS = ['full_timeout_min', 'abnormal_park_min'] as const
export type ConfigKey = (typeof CONFIG_KEYS)[number]
export interface ConfigChange { key: ConfigKey; before: string; after: number }
export type ViolationCounts = Record<1 | 2 | 3, number>

/** Frontend domain data; deliberately does not specify the pending C2 wire response. */
export interface StatisticsData {
  counts: ViolationCounts
  trend: Array<{ date: string; counts: ViolationCounts }>
  piles: Array<{ pileId: string | null; count: number }>
}

/** Bind only after C1–C3 are confirmed; an HTTP adapter must translate the agreed contract. */
export interface Week2DataSource {
  loadPiles?: (status: PileStatus | undefined) => Promise<ChargingPile[]>
  loadStatistics?: (days: 7 | 30) => Promise<StatisticsData>
  loadConfig?: () => Promise<SystemConfig[]>
  saveConfig?: (changes: readonly ConfigChange[]) => Promise<void>
}
export const WEEK2_DATA_SOURCE: InjectionKey<Week2DataSource> = Symbol('week2-data-source')
