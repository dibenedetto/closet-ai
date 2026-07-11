import { useCallback, useEffect, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'

import Icon from '../components/Icon'
import ItemImage from '../components/ItemImage'
import PageHeader from '../components/PageHeader'
import { EmptyView, ErrorView, LoadingView } from '../components/StateView'
import { errorMessage } from '../api/client'
import { itemImageUrl } from '../api/items'
import {
  submitOutfitFeedback,
  suggestOutfits,
  type OutfitSuggestion,
  type OutfitSuggestResponse,
} from '../api/outfits'
import { batchLogWears } from '../api/wear'

const CITIES = [
  { id: 'pisa', label: 'Pisa', lat: 43.72, lon: 10.40 },
  { id: 'milano', label: 'Milano', lat: 45.46, lon: 9.19 },
  { id: 'roma', label: 'Roma', lat: 41.90, lon: 12.50 },
  { id: 'torino', label: 'Torino', lat: 45.07, lon: 7.69 },
  { id: 'napoli', label: 'Napoli', lat: 40.85, lon: 14.27 },
] as const

const OCCASIONS = [
  { value: '', label: 'Ogni giorno' },
  { value: 'lavoro', label: 'Lavoro' },
  { value: 'tempo libero', label: 'Tempo libero' },
  { value: 'sera', label: 'Sera' },
] as const

function weatherSymbol(code: number, precipitation: number): string {
  if (precipitation >= 5) return '☂'
  if (code >= 71 && code <= 77) return '❄'
  if (code >= 51 && code <= 67) return '☂'
  if (code >= 1 && code <= 3) return '◒'
  return '☀'
}

function outfitKey(outfit: OutfitSuggestion): string {
  return outfit.items.map((item) => item.id).sort((a, b) => a - b).join('-')
}

function OutfitCard({
  outfit,
  index,
  busy,
  feedback,
  onFeedback,
  onWear,
}: {
  outfit: OutfitSuggestion
  index: number
  busy: boolean
  feedback: 1 | -1 | undefined
  onFeedback: (rating: 1 | -1) => void
  onWear: () => void
}) {
  const match = `${Math.round(outfit.score * 100)}%`
  return (
    <article className="outfit-card">
      <header className="outfit-card-header">
        <div>
          <div className="eyebrow">Proposta {String(index + 1).padStart(2, '0')}</div>
          <h2>{index === 0 ? 'La scelta migliore' : index === 1 ? 'Una buona alternativa' : 'Prova qualcosa di diverso'}</h2>
        </div>
        <div className="match-ring" style={{ '--match': match } as CSSProperties} aria-label={`Compatibilità ${match}`}>
          <span>{match}</span>
        </div>
      </header>

      <div className="outfit-composition">
        {outfit.items.map((item) => (
          <Link key={item.id} to={`/items/${item.id}`} className="outfit-item" aria-label={`Apri ${item.name}`}>
            <ItemImage src={itemImageUrl(item.id)} alt={item.name} />
            <span className="outfit-item-overlay">
              <strong>{item.name}</strong>
              <span>{item.category ?? 'Capo'}</span>
            </span>
          </Link>
        ))}
      </div>

      <div className="outfit-card-body">
        <p className="outfit-rationale">{outfit.rationale}</p>
        <div className="score-list" aria-label="Composizione del punteggio">
          <div className="score-row">
            <span>Palette</span>
            <span className="score-track"><span className="score-fill" style={{ width: `${Math.round(outfit.color_score * 100)}%` }} /></span>
            <span>{Math.round(outfit.color_score * 100)}%</span>
          </div>
          <div className="score-row">
            <span>Meteo</span>
            <span className="score-track"><span className="score-fill" style={{ width: `${Math.round(outfit.weather_score * 100)}%`, background: 'var(--blue)' }} /></span>
            <span>{Math.round(outfit.weather_score * 100)}%</span>
          </div>
          {outfit.ghost_bonus > 0 && (
            <div className="score-row">
              <span>Riscoperta</span>
              <span className="score-track"><span className="score-fill" style={{ width: `${Math.round(outfit.ghost_bonus * 100 / .15)}%`, background: 'var(--sun)' }} /></span>
              <span>+{Math.round(outfit.ghost_bonus * 100)}%</span>
            </div>
          )}
        </div>
        <div className="outfit-actions">
          <button type="button" className="button button-primary" onClick={onWear} disabled={busy}>
            <Icon name="check" size={17} /> {busy ? 'Registro…' : 'Indosso questo'}
          </button>
          <div className="feedback-group" role="group" aria-label="Valuta questa proposta">
            <button
              type="button"
              className="feedback-button"
              aria-label="Questa proposta mi piace"
              aria-pressed={feedback === 1}
              onClick={() => onFeedback(1)}
              disabled={busy}
            ><Icon name="heart" size={17} /></button>
            <button
              type="button"
              className="feedback-button"
              aria-label="Questa proposta non fa per me"
              aria-pressed={feedback === -1}
              onClick={() => onFeedback(-1)}
              disabled={busy}
            ><Icon name="close" size={17} /></button>
          </div>
        </div>
      </div>
    </article>
  )
}

export default function TodayPage() {
  const [data, setData] = useState<OutfitSuggestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busyKey, setBusyKey] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<Record<string, 1 | -1>>({})
  const [count, setCount] = useState(3)
  const [occasion, setOccasion] = useState('')
  const [cityId, setCityId] = useState(() => localStorage.getItem('closetai-city') ?? 'pisa')

  const city = CITIES.find((value) => value.id === cityId) ?? CITIES[0]

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await suggestOutfits({ count, lat: city.lat, lon: city.lon }))
    } catch (reason: unknown) {
      setError(errorMessage(reason))
    } finally {
      setLoading(false)
    }
  }, [city.lat, city.lon, count])

  useEffect(() => {
    void load()
  }, [load])

  function changeCity(value: string) {
    setCityId(value)
    localStorage.setItem('closetai-city', value)
  }

  async function onFeedback(outfit: OutfitSuggestion, rating: 1 | -1) {
    const key = outfitKey(outfit)
    setBusyKey(key)
    setMutationError(null)
    try {
      await submitOutfitFeedback({ item_ids: outfit.items.map((item) => item.id), rating, occasion: occasion || undefined })
      setFeedback((current) => ({ ...current, [key]: rating }))
      setNotice(rating === 1 ? 'Preferenza salvata: più proposte come questa.' : 'Preferenza salvata: questo stile peserà meno nelle prossime proposte.')
    } catch (reason: unknown) {
      setMutationError(errorMessage(reason))
    } finally {
      setBusyKey(null)
    }
  }

  async function onWear(outfit: OutfitSuggestion) {
    const key = outfitKey(outfit)
    setBusyKey(key)
    setMutationError(null)
    try {
      await batchLogWears(outfit.items.map((item) => ({ item_id: item.id, occasion: occasion || undefined })))
      setNotice(`${outfit.items.length} capi registrati insieme${occasion ? ` per “${occasion}”` : ''}.`)
    } catch (reason: unknown) {
      setMutationError(errorMessage(reason))
    } finally {
      setBusyKey(null)
    }
  }

  if (error && !data) {
    return <ErrorView message={error} action={<button type="button" onClick={() => void load()}><Icon name="refresh" size={17} /> Riprova</button>} />
  }

  const weather = data?.weather

  return (
    <section>
      <PageHeader
        eyebrow="Stylist quotidiano"
        title="Cosa metto oggi?"
        description="Outfit costruiti con ciò che possiedi, bilanciando meteo, colori e capi che meritano di tornare in rotazione."
        actions={<Link to="/" className="button button-secondary"><Icon name="grid" size={17} /> Guardaroba</Link>}
      />

      <section className="weather-hero" aria-labelledby="weather-title">
        <div>
          <div className="eyebrow" style={{ color: 'var(--lime)' }}>Contesto di oggi</div>
          <h2 id="weather-title">Vestiti per la giornata che hai davanti.</h2>
          <p>Personalizza luogo e occasione: le proposte cambiano con te.</p>
          <div className="today-controls">
            <label>
              <span className="sr-only">Città per il meteo</span>
              <select value={cityId} onChange={(event) => changeCity(event.target.value)}>
                {CITIES.map((value) => <option key={value.id} value={value.id}>{value.label}</option>)}
              </select>
            </label>
            <label>
              <span className="sr-only">Occasione</span>
              <select value={occasion} onChange={(event) => setOccasion(event.target.value)}>
                {OCCASIONS.map((value) => <option key={value.value} value={value.value}>{value.label}</option>)}
              </select>
            </label>
            <label>
              <span className="sr-only">Numero di proposte</span>
              <select value={count} onChange={(event) => setCount(Number(event.target.value))}>
                {[2, 3, 4].map((value) => <option key={value} value={value}>{value} proposte</option>)}
              </select>
            </label>
            <button type="button" className="button button-secondary" onClick={() => void load()} disabled={loading}>
              <Icon name="refresh" size={16} /> {loading ? 'Aggiorno…' : 'Nuove proposte'}
            </button>
          </div>
        </div>
        <div className="weather-pill">
          <span className="weather-symbol">{weather ? weatherSymbol(weather.weather_code, weather.precipitation_mm) : '·'}</span>
          <span>
            <strong className="weather-temperature">{weather ? `${weather.temperature_c.toFixed(0)}°` : '—'}</strong>
            <span className="weather-detail">
              {city.label} · {weather ? (weather.precipitation_mm > 0 ? `${weather.precipitation_mm.toFixed(1)} mm pioggia` : 'asciutto') : 'meteo in arrivo'}
            </span>
          </span>
        </div>
      </section>

      {weather?.source === 'fallback' && <div className="notice notice-warning" role="status" style={{ marginTop: 14 }}><Icon name="circle-alert" size={17} /> Meteo live non disponibile: uso condizioni miti di riferimento.</div>}
      {notice && <div className="notice notice-success" role="status" style={{ marginTop: 14 }}><Icon name="check" size={17} /> {notice}</div>}
      {mutationError && <div className="error" role="alert" style={{ marginTop: 14 }}><Icon name="circle-alert" size={17} /> {mutationError}</div>}
      {error && data && <div className="notice notice-warning" role="status" style={{ marginTop: 14 }}>{error} Mostro le ultime proposte disponibili.</div>}

      {loading && !data ? (
        <LoadingView label="Compongo outfit dal tuo guardaroba…" />
      ) : data?.outfits.length === 0 ? (
        <EmptyView
          icon="sparkles"
          title="Servono più combinazioni"
          message="Aggiungi almeno un top e un pantalone, oppure un vestito, per ricevere proposte complete."
          action={<Link to="/items/new" className="button button-primary"><Icon name="camera" size={17} /> Aggiungi un capo</Link>}
        />
      ) : (
        <div className="outfit-grid" aria-busy={loading}>
          {data?.outfits.map((outfit, index) => {
            const key = outfitKey(outfit)
            return (
              <OutfitCard
                key={key}
                outfit={outfit}
                index={index}
                busy={busyKey === key}
                feedback={feedback[key]}
                onFeedback={(rating) => void onFeedback(outfit, rating)}
                onWear={() => void onWear(outfit)}
              />
            )
          })}
        </div>
      )}
    </section>
  )
}
