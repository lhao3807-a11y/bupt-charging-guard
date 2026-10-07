import { CONFIG_KEYS } from '@/data/week2'
import type { ConfigChange, StatisticsData, Week2DataSource } from '@/data/week2'
import type { ChargingPile, PileStatus, SystemConfig } from '@/types/contract'
import { http } from './http'

const PILE_PAGE_SIZE = 200

interface PilePage {
  items: ChargingPile[]
  total: number
  page: number
  size: number
}

interface RuleCount {
  rule_hit: number
  count: number
}

interface StatsResponse {
  by_rule: RuleCount[]
  by_date: Array<{ date: string; by_rule: RuleCount[] }>
  by_pile: Array<{ pile_id: string | null; count: number }>
}

interface ConfigPage {
  items: Array<{ key: string; value: string; note: string | null }>
  total: number
}

const violationCounts = (rows: RuleCount[]) => ({
  1: rows.find((row) => row.rule_hit === 1)?.count ?? 0,
  2: rows.find((row) => row.rule_hit === 2)?.count ?? 0,
  3: rows.find((row) => row.rule_hit === 3)?.count ?? 0,
})

export const week2DataSource: Required<Week2DataSource> = {
  async loadPiles(status: PileStatus | undefined): Promise<ChargingPile[]> {
    const params = { page: 1, size: PILE_PAGE_SIZE, status }
    const first = await http.get<PilePage>('/api/piles', { params })
    const result = [...first.data.items]
    const pageCount = Math.ceil(first.data.total / PILE_PAGE_SIZE)
    for (let page = 2; page <= pageCount; page++) {
      const response = await http.get<PilePage>('/api/piles', {
        params: { ...params, page },
      })
      result.push(...response.data.items)
    }
    return result
  },

  async loadStatistics(days: 7 | 30): Promise<StatisticsData> {
    const response = await http.get<StatsResponse>('/api/stats', { params: { days } })
    return {
      counts: violationCounts(response.data.by_rule),
      trend: response.data.by_date.map((point) => ({
        date: point.date,
        counts: violationCounts(point.by_rule),
      })),
      piles: response.data.by_pile.map((point) => ({
        pileId: point.pile_id,
        count: point.count,
      })),
    }
  },

  async loadConfig(): Promise<SystemConfig[]> {
    const response = await http.get<ConfigPage>('/api/config')
    return response.data.items.map((item) => ({ ...item, note: item.note ?? '' }))
  },

  async saveConfig(changes: readonly ConfigChange[]): Promise<void> {
    const payload = Object.fromEntries(
      changes
        .filter((change) => CONFIG_KEYS.includes(change.key))
        .map(({ key, after }) => [key, after]),
    )
    await http.put<ConfigPage>('/api/config', payload)
  },
}
