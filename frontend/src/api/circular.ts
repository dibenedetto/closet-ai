import type { Condition } from './items'
import { API_BASE, jsonOrThrow } from './client'

export type ActionType = 'riparazione' | 'swap' | 'vendita' | 'donazione' | 'riciclo'

export interface ActionSuggestion {
  action_type: ActionType
  co2_saved_kg: number
  rationale: string
  priority: number
}

export interface DiagnoseResponse {
  item_id: number
  condition: Condition
  wear_count: number
  days_owned: number | null
  rationale: string
  /** Backend usato: "vlm-lora" | "clip-mlp" | "heuristic" */
  source: string
  confidence: number | null
  /** Difetto e tutorial valorizzati solo dal backend VLM (Approccio C) */
  defect: string | null
  tutorial: string | null
  suggestions: ActionSuggestion[]
}

export interface ItemAction {
  id: number
  item_id: number
  action_type: ActionType
  notes: string | null
  co2_saved_kg: number
  created_at: string
}

export interface ImpactStats {
  total_actions: number
  total_co2_saved_kg: number
  actions_by_type: Record<string, number>
  co2_by_type: Record<string, number>
  retired_items_count: number
  repaired_items_count: number
}

export interface RepairTutorial {
  defect: string
  category: string | null
  title: string
  difficulty: string
  time_minutes: number
  materials: string[]
  steps: string[]
  source: string
  llm_enrichment_available: boolean
}

export async function diagnoseItem(itemId: number): Promise<DiagnoseResponse> {
  return jsonOrThrow<DiagnoseResponse>(
    await fetch(`${API_BASE}/items/${itemId}/diagnose`, { method: 'POST' }),
  )
}

export async function setItemCondition(
  itemId: number,
  condition: Condition,
): Promise<DiagnoseResponse> {
  return jsonOrThrow<DiagnoseResponse>(
    await fetch(`${API_BASE}/items/${itemId}/condition`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ condition }),
    }),
  )
}

export async function registerAction(
  itemId: number,
  input: { action_type: ActionType; notes?: string; co2_saved_kg?: number },
): Promise<ItemAction> {
  return jsonOrThrow<ItemAction>(
    await fetch(`${API_BASE}/items/${itemId}/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}

export async function listActions(itemId: number): Promise<ItemAction[]> {
  return jsonOrThrow<ItemAction[]>(await fetch(`${API_BASE}/items/${itemId}/actions`))
}

export async function deleteAction(actionId: number): Promise<void> {
  const r = await fetch(`${API_BASE}/actions/${actionId}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}

export async function getImpactStats(): Promise<ImpactStats> {
  return jsonOrThrow<ImpactStats>(await fetch(`${API_BASE}/stats/impact`))
}

export async function listSupportedDefects(): Promise<string[]> {
  const body = await jsonOrThrow<{ defects: string[] }>(
    await fetch(`${API_BASE}/repair-tutorials/defects`),
  )
  return body.defects
}

export async function getRepairTutorial(
  defect: string,
  category?: string,
): Promise<RepairTutorial> {
  const params = new URLSearchParams({ defect })
  if (category) params.set('category', category)
  return jsonOrThrow<RepairTutorial>(
    await fetch(`${API_BASE}/repair-tutorials?${params.toString()}`),
  )
}
