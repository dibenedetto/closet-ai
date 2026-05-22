import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { itemImageUrl } from '../api/items'
import { logWear } from '../api/wear'
import {
  submitOutfitFeedback,
  suggestOutfits,
  type OutfitSuggestion,
  type OutfitSuggestResponse,
} from '../api/outfits'

function weatherIcon(code: number, precipitation: number): string {
  if (precipitation >= 5) return '🌧️'
  if (precipitation >= 1) return '🌦️'
  if (code >= 71 && code <= 77) return '❄️'
  if (code >= 51 && code <= 67) return '🌧️'
  if (code >= 1 && code <= 3) return '⛅'
  return '☀️'
}

function ScoreBar({ value, color = 'var(--accent)' }: { value: number; color?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div
      style={{
        height: 6,
        background: 'var(--panel-2)',
        borderRadius: 3,
        overflow: 'hidden',
      }}
    >
      <div style={{ width: `${pct}%`, height: '100%', background: color }} />
    </div>
  )
}

function OutfitCard({
  outfit,
  index,
  onFeedback,
  onWearAll,
  busy,
}: {
  outfit: OutfitSuggestion
  index: number
  onFeedback: (outfit: OutfitSuggestion, rating: 1 | -1) => void
  onWearAll: (outfit: OutfitSuggestion) => void
  busy: boolean
}) {
  return (
    <section className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 8,
        }}
      >
        <h3 style={{ margin: 0 }}>
          Proposta #{index + 1}
          <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
            {Math.round(outfit.score * 100)}% match
          </span>
        </h3>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${outfit.items.length}, 1fr)`,
          gap: 8,
        }}
      >
        {outfit.items.map((it) => (
          <Link key={it.id} to={`/items/${it.id}`} className="item-card" style={{ position: 'relative' }}>
            {it.image_path && (
              <img src={itemImageUrl(it.id)} alt={it.name} loading="lazy" />
            )}
            <div className="body" style={{ fontSize: 12 }}>
              <strong>{it.name}</strong>
              <div className="muted">{it.category ?? '—'}</div>
            </div>
          </Link>
        ))}
      </div>

      <div style={{ display: 'grid', gap: 4, fontSize: 11, color: 'var(--muted)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Colore</span><span>{Math.round(outfit.color_score * 100)}%</span>
        </div>
        <ScoreBar value={outfit.color_score} color="var(--ok)" />
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Meteo</span><span>{Math.round(outfit.weather_score * 100)}%</span>
        </div>
        <ScoreBar value={outfit.weather_score} color="var(--accent)" />
        {outfit.ghost_bonus > 0 && (
          <div className="muted" style={{ fontSize: 11 }}>
            +{Math.round(outfit.ghost_bonus * 100)}% bonus per capi mai indossati
          </div>
        )}
      </div>

      <p className="muted" style={{ margin: 0, fontSize: 12 }}>{outfit.rationale}</p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={() => onWearAll(outfit)} disabled={busy}>
          Indosso questo →
        </button>
        <button className="ghost" onClick={() => onFeedback(outfit, 1)} disabled={busy} title="Like">
          👍
        </button>
        <button className="ghost" onClick={() => onFeedback(outfit, -1)} disabled={busy} title="Dislike">
          👎
        </button>
      </div>
    </section>
  )
}

export default function TodayPage() {
  const [data, setData] = useState<OutfitSuggestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [count, setCount] = useState(3)

  const load = useCallback(async () => {
    setError(null)
    setNotice(null)
    setData(null)
    try {
      setData(await suggestOutfits({ count }))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [count])

  useEffect(() => {
    void load()
  }, [load])

  async function onFeedback(outfit: OutfitSuggestion, rating: 1 | -1) {
    setBusy(true)
    try {
      await submitOutfitFeedback({
        item_ids: outfit.items.map((i) => i.id),
        rating,
      })
      setNotice(rating === 1 ? 'Feedback salvato 👍' : 'Feedback salvato 👎')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onWearAll(outfit: OutfitSuggestion) {
    setBusy(true)
    try {
      await Promise.all(outfit.items.map((i) => logWear(i.id)))
      setNotice(`Indossati ${outfit.items.length} capi: ✓`)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    return (
      <p className="error">
        Errore: {error} <button className="ghost" onClick={() => void load()}>Riprova</button>
      </p>
    )
  }
  if (data == null) return <p className="muted">Caricamento proposte…</p>

  const w = data.weather

  return (
    <section>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Cosa metto oggi?</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span title={`Sorgente meteo: ${w.source}`}>
            {weatherIcon(w.weather_code, w.precipitation_mm)} {w.temperature_c.toFixed(1)}°C
            <span className="muted" style={{ marginLeft: 6 }}>
              {w.precipitation_mm > 0 ? `${w.precipitation_mm.toFixed(1)}mm` : 'asciutto'}
              · vento {w.wind_kmh.toFixed(0)} km/h
            </span>
          </span>
          <label htmlFor="count" className="muted">Proposte</label>
          <input
            id="count"
            type="number"
            min={1}
            max={6}
            value={count}
            onChange={(e) => setCount(Number(e.target.value) || 3)}
            style={{ width: 60 }}
          />
          <button className="ghost" onClick={() => void load()}>Rigenera</button>
        </div>
      </div>

      {w.source === 'fallback' && (
        <p className="muted" style={{ fontSize: 12 }}>
          ⚠️ Meteo API non raggiungibile, sto usando un meteo "mite" di fallback.
        </p>
      )}

      {notice && <p style={{ color: 'var(--ok)' }}>{notice}</p>}

      {data.outfits.length === 0 ? (
        <div className="empty-state">
          Non riesco a comporre un outfit. Aggiungi più capi (almeno una camicia / pantaloni / scarpe) per ottenere proposte.{' '}
          <Link to="/items/new">Aggiungi un capo →</Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          {data.outfits.map((o, i) => (
            <OutfitCard
              key={i}
              outfit={o}
              index={i}
              onFeedback={onFeedback}
              onWearAll={onWearAll}
              busy={busy}
            />
          ))}
        </div>
      )}
    </section>
  )
}
