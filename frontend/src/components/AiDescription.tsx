import { useState } from 'react'

import { describeItem } from '../api/ai'
import type { Item } from '../api/items'

export default function AiDescription({
  item,
  llmConfigured,
  onUpdated,
}: {
  item: Item
  llmConfigured: boolean
  onUpdated: (text: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [modelUsed, setModelUsed] = useState<string | null>(null)

  if (!llmConfigured && !item.description) {
    return null
  }

  async function onGenerate(regenerate: boolean) {
    setBusy(true)
    setError(null)
    try {
      const out = await describeItem(item.id, { regenerate })
      if (out.description) onUpdated(out.description)
      if (out.model) setModelUsed(out.model)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ai-card" style={{ marginTop: 12 }}>
      <span className="ai-label">✨ AI · descrizione</span>
      {item.description ? (
        <>
          <p className="ai-text">{item.description}</p>
          <div className="ai-meta">
            {modelUsed && <>generata da <code>{modelUsed}</code> · </>}
            <button
              className="ghost"
              style={{ padding: '4px 10px', fontSize: 11 }}
              onClick={() => void onGenerate(true)}
              disabled={busy}
            >
              {busy ? 'Rigenero…' : 'Rigenera'}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="ai-text muted">Nessuna descrizione. Generala con l'AI.</p>
          <div className="ai-meta">
            <button onClick={() => void onGenerate(false)} disabled={busy}>
              {busy ? 'Genero…' : '✨ Genera descrizione'}
            </button>
          </div>
        </>
      )}
      {error && <p className="error" style={{ marginTop: 8 }}>{error}</p>}
    </div>
  )
}
