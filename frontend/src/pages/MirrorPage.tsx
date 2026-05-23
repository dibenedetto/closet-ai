/**
 * Pagina per il prototipo specchio smart (Raspberry Pi 5 + monitor verticale).
 *
 * Resa minimalissima — pensata per essere lasciata in fullscreen kiosk:
 * orologio enorme, meteo, e l'outfit suggerito per oggi con thumbnails.
 *
 * Refresh automatico ogni 5 minuti (re-genera la proposta di outfit).
 */
import { useEffect, useState } from 'react'

import { itemImageUrl } from '../api/items'
import { suggestOutfits, type OutfitSuggestResponse } from '../api/outfits'

const REFRESH_MS = 5 * 60 * 1000

function fmtClock(d: Date): string {
  return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}

function fmtDate(d: Date): string {
  return d.toLocaleDateString('it-IT', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

function weatherIcon(code: number, precipitation: number): string {
  if (precipitation >= 5) return '🌧️'
  if (precipitation >= 1) return '🌦️'
  if (code >= 71 && code <= 77) return '❄️'
  if (code >= 51 && code <= 67) return '🌧️'
  if (code >= 1 && code <= 3) return '⛅'
  return '☀️'
}

export default function MirrorPage() {
  const [now, setNow] = useState(new Date())
  const [data, setData] = useState<OutfitSuggestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Tick orologio ogni 30s (basta per ore:minuti).
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const r = await suggestOutfits({ count: 1 })
        if (!cancelled) {
          setData(r)
          setError(null)
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e))
        }
      }
    }
    void load()
    const id = window.setInterval(() => void load(), REFRESH_MS)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const outfit = data?.outfits[0]
  const weather = data?.weather

  return (
    <div className="mirror-root">
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 24,
        }}
      >
        <div>
          <div className="mirror-clock">{fmtClock(now)}</div>
          <div className="mirror-date">{fmtDate(now)}</div>
        </div>
        {weather && (
          <div className="mirror-weather" style={{ textAlign: 'right' }}>
            <div>
              {weatherIcon(weather.weather_code, weather.precipitation_mm)}{' '}
              {weather.temperature_c.toFixed(0)}°C
            </div>
            <small>
              {weather.precipitation_mm > 0
                ? `${weather.precipitation_mm.toFixed(1)} mm pioggia`
                : 'asciutto'}{' '}
              · vento {weather.wind_kmh.toFixed(0)} km/h
            </small>
          </div>
        )}
      </header>

      {error && <p className="error">Errore: {error}</p>}

      {outfit ? (
        <section>
          <div className="mirror-section-title">Cosa metto oggi · ClosetAI suggerisce</div>
          <div className="mirror-outfit">
            {outfit.items.map((it) => (
              <div className="mirror-item" key={it.id}>
                {it.image_path && (
                  <img src={itemImageUrl(it.id)} alt={it.name} loading="lazy" />
                )}
                <div className="name">{it.name}</div>
                <div className="meta">
                  {[it.category, it.color].filter(Boolean).join(' · ')}
                </div>
              </div>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 16, fontSize: 13 }}>
            {outfit.rationale} ·{' '}
            <span style={{ color: 'var(--ok)' }}>match {Math.round(outfit.score * 100)}%</span>
          </p>
        </section>
      ) : (
        !error && (
          <p className="muted" style={{ fontSize: 18 }}>
            Sto preparando una proposta di outfit…
          </p>
        )
      )}

      <footer style={{ marginTop: 'auto', fontSize: 11, color: 'var(--muted)' }}>
        ClosetAI · refresh ogni {REFRESH_MS / 60000} min
        {weather && weather.source === 'fallback' && ' · meteo non disponibile'}
      </footer>
    </div>
  )
}
