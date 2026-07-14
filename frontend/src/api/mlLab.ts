/** Client per la pagina tecnica ML Lab (stato reti, prova interattiva). */
import { API_BASE, asError, jsonOrThrow } from './client'

export interface ModelInfo {
  key: string
  name: string
  /** "own" (rete nostra) | "gen" (generativa) — codice colore in UI */
  nature: string
  task: string
  available: boolean
  architecture: string | null
  metrics: Record<string, unknown> | null
  labels: string[] | null
}

export interface DatasetInfo {
  key: string
  name: string
  available: boolean
  n_samples: number | null
  detail: string | null
}

export interface MlLabStatus {
  models: ModelInfo[]
  datasets: DatasetInfo[]
}

export interface ConditionPredictOut {
  condition: string
  confidence: number
  probabilities: Record<string, number>
}

export interface GapPredictIn {
  counts: Record<string, number>
  n_colors: number
  has_neutral: boolean
  ghost_ratio: number
}

export interface GapPredictOut {
  gaps: string[]
  labels: Record<string, string>
  probabilities: Record<string, number>
  balanced: boolean
  source: string
}

export async function getMlLabStatus(): Promise<MlLabStatus> {
  return jsonOrThrow<MlLabStatus>(await fetch(`${API_BASE}/ml/models`))
}

export async function predictCondition(image: File): Promise<ConditionPredictOut> {
  const fd = new FormData()
  fd.append('image', image)
  const r = await fetch(`${API_BASE}/ml/condition/predict`, { method: 'POST', body: fd })
  if (!r.ok) throw await asError(r)
  return (await r.json()) as ConditionPredictOut
}

export async function predictGap(input: GapPredictIn): Promise<GapPredictOut> {
  return jsonOrThrow<GapPredictOut>(
    await fetch(`${API_BASE}/ml/gap/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    }),
  )
}

export function confusionMatrixUrl(): string {
  return `${API_BASE}/ml/condition/confusion-matrix`
}
