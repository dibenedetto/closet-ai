import { API_BASE, asError, jsonOrThrow } from './client'

export type Condition = 'nuovo' | 'buono' | 'usurato' | 'danneggiato'

export interface Item {
  id: number
  name: string
  category: string | null
  color: string | null
  image_path: string | null
  price: number | null
  /** Data acquisto in formato YYYY-MM-DD, oppure null */
  purchase_date: string | null
  /** Confidenza softmax del classificatore (0–1), null se mock o assente */
  classification_confidence: number | null
  /** Descrizione narrativa generata da LLM, null se non ancora generata */
  description: string | null
  /** Condizione (`nuovo`/`buono`/`usurato`/`danneggiato`), null se mai diagnosticato */
  condition: Condition | null
  /** Quando il capo è stato ritirato dal guardaroba (donato/venduto/...). */
  retired_at: string | null
  /** Timestamp ISO-8601 di creazione (UTC) */
  created_at: string
}

export interface CreateItemInput {
  name: string
  category?: string
  color?: string
  price?: number
  /** YYYY-MM-DD */
  purchase_date?: string
  image: File
}

export interface ListItemsOptions {
  skip?: number
  limit?: number
}

export async function listItems(opts: ListItemsOptions = {}): Promise<Item[]> {
  const params = new URLSearchParams()
  if (opts.skip != null) params.set('skip', String(opts.skip))
  if (opts.limit != null) params.set('limit', String(opts.limit))
  const qs = params.toString()
  const url = qs ? `${API_BASE}/items?${qs}` : `${API_BASE}/items`
  return jsonOrThrow<Item[]>(await fetch(url))
}

export async function getItem(id: number): Promise<Item> {
  return jsonOrThrow<Item>(await fetch(`${API_BASE}/items/${id}`))
}

export async function createItem(input: CreateItemInput): Promise<Item> {
  const fd = new FormData()
  fd.append('name', input.name)
  if (input.category) fd.append('category', input.category)
  if (input.color) fd.append('color', input.color)
  if (input.price != null) fd.append('price', String(input.price))
  if (input.purchase_date) fd.append('purchase_date', input.purchase_date)
  fd.append('image', input.image)
  return jsonOrThrow<Item>(
    await fetch(`${API_BASE}/items`, { method: 'POST', body: fd }),
  )
}

export async function deleteItem(id: number): Promise<void> {
  const r = await fetch(`${API_BASE}/items/${id}`, { method: 'DELETE' })
  if (!r.ok) throw await asError(r)
}

export async function reclassifyItem(id: number): Promise<Item> {
  return jsonOrThrow<Item>(
    await fetch(`${API_BASE}/items/${id}/reclassify`, { method: 'POST' }),
  )
}

export function itemImageUrl(id: number): string {
  return `${API_BASE}/items/${id}/image`
}
