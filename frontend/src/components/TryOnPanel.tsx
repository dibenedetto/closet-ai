import { useEffect, useRef, useState } from 'react'

import { getTryOnStatus, runTryOn, tryOnImageUrl, type TryOnOut, type TryOnStatus } from '../api/ai'
import { itemImageUrl, type Item } from '../api/items'

export default function TryOnPanel({ item }: { item: Item }) {
  const [status, setStatus] = useState<TryOnStatus | null>(null)
  const [portrait, setPortrait] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<TryOnOut | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    getTryOnStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  useEffect(() => {
    if (!portrait) {
      setPreview(null)
      return
    }
    const url = URL.createObjectURL(portrait)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [portrait])

  if (!status || !status.available) {
    return null
  }

  async function onGenerate() {
    if (!portrait || busy) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await runTryOn(item.id, portrait))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ai-card" style={{ marginTop: 16 }}>
      <span className="ai-label">✨ AI · try-on virtuale</span>
      <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        Carica un tuo ritratto (jpg/png/webp ≤ 10MB): genera un'anteprima di
        come potrebbe starti il capo. Backend: <code>{status.backend}</code>
        {status.model && <> · modello <code>{status.model}</code></>}.
        L'operazione può richiedere alcuni minuti su CPU.
      </p>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 8 }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setPortrait(e.target.files?.[0] ?? null)}
          style={{ flex: 1, minWidth: 200 }}
        />
        <button onClick={() => void onGenerate()} disabled={!portrait || busy}>
          {busy ? 'Genero (può richiedere minuti)…' : '✨ Genera try-on'}
        </button>
        {portrait && (
          <button
            className="ghost"
            onClick={() => {
              setPortrait(null)
              setResult(null)
              if (fileInputRef.current) fileInputRef.current.value = ''
            }}
            disabled={busy}
          >
            Reset
          </button>
        )}
      </div>

      {error && <p className="error" style={{ marginTop: 8 }}>{error}</p>}

      {(preview || result) && (
        <div className="tryon-result">
          {preview && (
            <div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>Il tuo ritratto</div>
              <img src={preview} alt="Anteprima ritratto" />
            </div>
          )}
          {result ? (
            <div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
                Try-on generato · {result.elapsed_ms} ms
              </div>
              <img
                src={tryOnImageUrl(result.item_id, result.filename)}
                alt={`Try-on di ${item.name}`}
              />
              <p className="ai-meta" style={{ marginTop: 4 }}>
                Prompt: <em>{result.prompt}</em>
              </p>
            </div>
          ) : (
            <div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>
                Capo di riferimento
              </div>
              {item.image_path && (
                <img src={itemImageUrl(item.id)} alt={item.name} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
