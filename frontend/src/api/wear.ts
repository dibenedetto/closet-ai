import { API_BASE, asError, jsonOrThrow } from './client'

export interface WearEvent {
  id: number
  item_id: number
  /** YYYY-MM-DD */
  worn_on: string
  occasion: string | null
  created_at: string
}

export interface LogWearInput {
  /** YYYY-MM-DD; se omesso il backend usa oggi */
  worn_on?: string
  occasion?: string
}

export interface BatchWearInput extends LogWearInput {
  item_id: number
}

export async function logWear(itemId: number, input: LogWearInput = {}): Promise<WearEvent> {
  return jsonOrThrow<WearEvent>(
    await fetch(`${API_BASE}/items/${itemId}/wear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}

export async function batchLogWears(events: BatchWearInput[]): Promise<WearEvent[]> {
  return jsonOrThrow<WearEvent[]>(
    await fetch(`${API_BASE}/wear-events/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events }),
    }),
  )
}

export async function listWears(itemId: number): Promise<WearEvent[]> {
  return jsonOrThrow<WearEvent[]>(await fetch(`${API_BASE}/items/${itemId}/wears`))
}

export async function deleteWear(eventId: number): Promise<void> {
  const r = await fetch(`${API_BASE}/wear-events/${eventId}`, { method: 'DELETE' })
  if (!r.ok) throw await asError(r)
}
