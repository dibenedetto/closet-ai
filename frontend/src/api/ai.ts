/** Client per gli endpoint AI generativa (descrizione, coach, try-on, tutorial LLM). */
import type { Item } from './items'
import { API_BASE, asError, jsonOrThrow } from './client'
import type { RepairTutorial } from './circular'

export interface LlmStatus {
  configured: boolean
  model: string
  tryon_backend: string
}

export interface TryOnStatus {
  backend: string
  available: boolean
  model: string | null
}

export interface CoachOut {
  text: string
  facts: Record<string, unknown>
  model: string | null
  cached: boolean
}

export interface ItemDescriptionOut {
  item_id: number
  description: string | null
  generated: boolean
  model: string | null
}

export interface TryOnOut {
  item_id: number
  filename: string
  url: string
  backend: string
  prompt: string
  elapsed_ms: number
}

export async function getLlmStatus(): Promise<LlmStatus> {
  return jsonOrThrow<LlmStatus>(await fetch(`${API_BASE}/llm/status`))
}

export async function getTryOnStatus(): Promise<TryOnStatus> {
  return jsonOrThrow<TryOnStatus>(await fetch(`${API_BASE}/tryon/status`))
}

export async function describeItem(
  itemId: number,
  opts: { regenerate?: boolean } = {},
): Promise<ItemDescriptionOut> {
  const params = new URLSearchParams()
  if (opts.regenerate) params.set('regenerate', 'true')
  const qs = params.toString()
  const url = qs
    ? `${API_BASE}/items/${itemId}/describe?${qs}`
    : `${API_BASE}/items/${itemId}/describe`
  return jsonOrThrow<ItemDescriptionOut>(await fetch(url, { method: 'POST' }))
}

export async function getCoachMessage(
  ghostAfterDays: number = 30,
): Promise<CoachOut> {
  return jsonOrThrow<CoachOut>(
    await fetch(`${API_BASE}/stats/coach?ghost_after_days=${ghostAfterDays}`),
  )
}

export async function getEnrichedTutorial(
  defect: string,
  opts: { category?: string; color?: string; condition?: string } = {},
): Promise<RepairTutorial> {
  const params = new URLSearchParams({ defect })
  if (opts.category) params.set('category', opts.category)
  if (opts.color) params.set('color', opts.color)
  if (opts.condition) params.set('condition', opts.condition)
  return jsonOrThrow<RepairTutorial>(
    await fetch(`${API_BASE}/repair-tutorials/enrich?${params.toString()}`),
  )
}

export async function runTryOn(itemId: number, portrait: File): Promise<TryOnOut> {
  const fd = new FormData()
  fd.append('portrait', portrait)
  const r = await fetch(`${API_BASE}/items/${itemId}/try-on`, {
    method: 'POST',
    body: fd,
  })
  if (!r.ok) throw await asError(r)
  return (await r.json()) as TryOnOut
}

export function tryOnImageUrl(itemId: number, filename: string): string {
  return `${API_BASE}/items/${itemId}/try-on/${filename}`
}

// Re-export per comodità nei consumer.
export type { Item }
