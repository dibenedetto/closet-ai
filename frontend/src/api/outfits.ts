import type { Item } from './items'
import { API_BASE, jsonOrThrow } from './client'

export interface WeatherSummary {
  target_date: string // YYYY-MM-DD
  temperature_c: number
  precipitation_mm: number
  wind_kmh: number
  weather_code: number
  source: 'open-meteo' | 'fallback'
}

export interface OutfitSuggestion {
  items: Item[]
  score: number
  color_score: number
  weather_score: number
  ghost_bonus: number
  rationale: string
}

export interface OutfitSuggestResponse {
  target_date: string
  weather: WeatherSummary
  outfits: OutfitSuggestion[]
}

export interface SuggestOpts {
  date?: string
  count?: number
  lat?: number
  lon?: number
}

export async function suggestOutfits(opts: SuggestOpts = {}): Promise<OutfitSuggestResponse> {
  const params = new URLSearchParams()
  if (opts.date) params.set('date', opts.date)
  if (opts.count != null) params.set('count', String(opts.count))
  if (opts.lat != null) params.set('lat', String(opts.lat))
  if (opts.lon != null) params.set('lon', String(opts.lon))
  const qs = params.toString()
  const url = qs ? `${API_BASE}/outfits/suggest?${qs}` : `${API_BASE}/outfits/suggest`
  return jsonOrThrow<OutfitSuggestResponse>(await fetch(url))
}

export interface OutfitFeedbackInput {
  item_ids: number[]
  rating: 1 | -1
  occasion?: string
}

export interface OutfitFeedback {
  id: number
  item_ids: number[]
  rating: number
  occasion: string | null
  created_at: string
}

export async function submitOutfitFeedback(
  input: OutfitFeedbackInput,
): Promise<OutfitFeedback> {
  return jsonOrThrow<OutfitFeedback>(
    await fetch(`${API_BASE}/outfits/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}
