import { API_BASE, jsonOrThrow } from './client'

export interface ItemStats {
  item_id: number
  wear_count: number
  /** YYYY-MM-DD oppure null */
  last_worn: string | null
  days_since_last_worn: number | null
  cost_per_wear: number | null
  is_ghost: boolean
  ghost_after_days: number
}

export interface TopItem {
  item_id: number
  name: string
  wear_count: number
}

export interface WardrobeStats {
  total_items: number
  total_wears: number
  avg_wears_per_item: number
  ghost_count: number
  ghost_after_days: number
  total_investment: number | null
  avg_cost_per_wear: number | null
  top_worn: TopItem[]
}

export interface GhostItem {
  item_id: number
  name: string
  category: string | null
  purchase_date: string | null
  days_owned: number | null
  price: number | null
}

export async function getItemStats(
  itemId: number,
  opts: { ghostAfterDays?: number } = {},
): Promise<ItemStats> {
  const params = new URLSearchParams()
  if (opts.ghostAfterDays != null) params.set('ghost_after_days', String(opts.ghostAfterDays))
  const qs = params.toString()
  const url = qs
    ? `${API_BASE}/items/${itemId}/stats?${qs}`
    : `${API_BASE}/items/${itemId}/stats`
  return jsonOrThrow<ItemStats>(await fetch(url))
}

export async function getWardrobeStats(
  opts: { ghostAfterDays?: number; topN?: number } = {},
): Promise<WardrobeStats> {
  const params = new URLSearchParams()
  if (opts.ghostAfterDays != null) params.set('ghost_after_days', String(opts.ghostAfterDays))
  if (opts.topN != null) params.set('top_n', String(opts.topN))
  const qs = params.toString()
  const url = qs ? `${API_BASE}/stats/wardrobe?${qs}` : `${API_BASE}/stats/wardrobe`
  return jsonOrThrow<WardrobeStats>(await fetch(url))
}

export async function getGhostItems(
  opts: { ghostAfterDays?: number } = {},
): Promise<GhostItem[]> {
  const params = new URLSearchParams()
  if (opts.ghostAfterDays != null) params.set('ghost_after_days', String(opts.ghostAfterDays))
  const qs = params.toString()
  const url = qs ? `${API_BASE}/stats/ghosts?${qs}` : `${API_BASE}/stats/ghosts`
  return jsonOrThrow<GhostItem[]>(await fetch(url))
}
