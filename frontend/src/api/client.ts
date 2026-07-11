// Base URL delle API. In dev (`npm run dev`) lascia il default `/api/v1`, che
// passa per il proxy Vite verso il backend FastAPI su :8000. In produzione si
// imposta `VITE_API_BASE_URL` con un URL assoluto.
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export async function asError(r: Response): Promise<ApiError> {
  const raw = await r.text().catch(() => '')
  let detail = raw || r.statusText || 'Richiesta non riuscita.'
  if (raw) {
    try {
      const body = JSON.parse(raw) as { detail?: unknown }
      detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body)
    } catch {
      // Le risposte non JSON sono già leggibili in `raw`.
    }
  }
  return new ApiError(r.status, detail)
}

export async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) throw await asError(r)
  return (await r.json()) as T
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'La risorsa richiesta non è più disponibile.'
    if (error.status === 409) return error.detail
    if (error.status === 413) return 'Il file supera il limite massimo di 10 MB.'
    if (error.status === 422) return 'Controlla i dati inseriti e riprova.'
    if (error.status >= 500) return 'Il servizio non è disponibile in questo momento. Riprova tra poco.'
    return error.detail
  }
  if (error instanceof TypeError) {
    return 'Non riesco a raggiungere ClosetAI. Verifica che il backend sia avviato.'
  }
  return error instanceof Error ? error.message : String(error)
}
