import { useCallback, useEffect, useState } from 'react'

import { getCoachMessage, type CoachOut } from '../api/ai'
import { errorMessage } from '../api/client'
import Icon from './Icon'

export default function CoachCard({
  llmConfigured,
  ghostAfterDays = 30,
}: {
  llmConfigured: boolean
  ghostAfterDays?: number
}) {
  const [data, setData] = useState<CoachOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      setData(await getCoachMessage(ghostAfterDays))
    } catch (e: unknown) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
      setLoaded(true)
    }
  }, [ghostAfterDays])

  useEffect(() => {
    if (!llmConfigured) return
    void load()
  }, [llmConfigured, load])

  if (!llmConfigured) return null
  if (!loaded && busy) {
    return (
      <div className="ai-card" style={{ marginBottom: 16 }}>
        <span className="ai-label">✨ AI · coach sostenibilità</span>
        <div className="skeleton line" style={{ marginTop: 10 }} />
        <div className="skeleton line short" />
      </div>
    )
  }
  if (error) {
    return (
      <div className="notice notice-warning" style={{ marginBottom: 16 }} role="status">
        <Icon name="circle-alert" size={17} /> Il coach AI non è disponibile.{' '}
        <button type="button" className="text-button" onClick={() => void load()}>Riprova</button>
      </div>
    )
  }

  return (
    <div className="ai-card" style={{ marginBottom: 16 }}>
      <span className="ai-label">✨ AI · coach sostenibilità</span>
      {data && <p className="ai-text">{data.text}</p>}
      <div className="ai-meta">
        {data?.model && <>{data.cached ? 'risposta cached · ' : ''}<code>{data.model}</code> · </>}
        <button
          className="ghost"
          style={{ padding: '4px 10px', fontSize: 11 }}
          onClick={() => void load()}
          disabled={busy}
        >
          {busy ? '…' : 'Rigenera'}
        </button>
      </div>
    </div>
  )
}
