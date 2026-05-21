// Base URL delle API. In dev (`npm run dev`) lascia il default `/api/v1`, che
// passa per il proxy Vite verso il backend FastAPI su :8000. In produzione si
// imposta `VITE_API_BASE_URL` con un URL assoluto.
export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export async function asError(r: Response): Promise<ApiError> {
  let detail: string
  try {
    const body = (await r.json()) as { detail?: unknown }
    detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body)
  } catch {
    detail = await r.text().catch(() => r.statusText)
  }
  return new ApiError(r.status, detail)
}

export async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) throw await asError(r)
  return (await r.json()) as T
}
