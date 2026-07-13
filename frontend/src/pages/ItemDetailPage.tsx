import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import AiDescription from '../components/AiDescription'
import CircularSection from '../components/CircularSection'
import Icon from '../components/Icon'
import ItemImage from '../components/ItemImage'
import StatusBadge from '../components/StatusBadge'
import { ErrorView, LoadingView } from '../components/StateView'
import TryOnPanel from '../components/TryOnPanel'
import { getLlmStatus, type LlmStatus } from '../api/ai'
import { errorMessage } from '../api/client'
import { deleteItem, getItem, itemImageUrl, reclassifyItem, type Item } from '../api/items'
import { getItemStats, type ItemStats } from '../api/stats'
import { deleteWear, listWears, logWear, type WearEvent } from '../api/wear'

function fmtDate(iso: string | null, includeTime = false): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return includeTime ? date.toLocaleString('it-IT') : date.toLocaleDateString('it-IT')
}

function confidenceLabel(value: number | null): string {
  if (value == null) return 'Non disponibile'
  if (value >= .7) return 'Alta'
  if (value >= .4) return 'Media'
  return 'Da verificare'
}

export default function ItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const itemId = Number(id)
  const isValidId = Number.isInteger(itemId) && itemId > 0
  const [item, setItem] = useState<Item | null>(null)
  const [stats, setStats] = useState<ItemStats | null>(null)
  const [wears, setWears] = useState<WearEvent[]>([])
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [secondaryError, setSecondaryError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [reclassifying, setReclassifying] = useState(false)
  const [logging, setLogging] = useState(false)

  useEffect(() => {
    getLlmStatus().then(setLlmStatus).catch(() => setLlmStatus(null))
  }, [])

  const refresh = useCallback(async () => {
    if (!isValidId) {
      setError('L’identificativo del capo non è valido.')
      return
    }
    try {
      const value = await getItem(itemId)
      setItem(value)
      setError(null)
    } catch (reason: unknown) {
      setError(errorMessage(reason))
      return
    }

    const [statsResult, wearsResult] = await Promise.allSettled([
      getItemStats(itemId),
      listWears(itemId),
    ])
    if (statsResult.status === 'fulfilled') setStats(statsResult.value)
    if (wearsResult.status === 'fulfilled') setWears(wearsResult.value)
    setSecondaryError(
      statsResult.status === 'rejected' || wearsResult.status === 'rejected'
        ? 'Alcuni dati di utilizzo non sono disponibili.'
        : null,
    )
  }, [itemId, isValidId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function onDelete() {
    if (!item || deleting) return
    if (!confirm(`Eliminare definitivamente “${item.name}”?`)) return
    setDeleting(true)
    try {
      await deleteItem(item.id)
      navigate('/', { replace: true })
    } catch (reason: unknown) {
      setSecondaryError(errorMessage(reason))
      setDeleting(false)
    }
  }

  async function onReclassify() {
    if (!item || reclassifying) return
    setReclassifying(true)
    setSecondaryError(null)
    setNotice(null)
    try {
      setItem(await reclassifyItem(item.id))
      setNotice('Categoria e colore sono stati rianalizzati dalla foto.')
    } catch (reason: unknown) {
      setSecondaryError(errorMessage(reason))
    } finally {
      setReclassifying(false)
    }
  }

  async function onLogWear() {
    if (!item || logging || item.retired_at) return
    setLogging(true)
    setSecondaryError(null)
    setNotice(null)
    try {
      await logWear(item.id)
      setNotice('Utilizzo di oggi registrato. Il cost-per-wear è stato aggiornato.')
      await refresh()
    } catch (reason: unknown) {
      setSecondaryError(errorMessage(reason))
    } finally {
      setLogging(false)
    }
  }

  async function onDeleteWear(event: WearEvent) {
    if (!confirm(`Rimuovere l’utilizzo del ${fmtDate(event.worn_on)}?`)) return
    try {
      await deleteWear(event.id)
      await refresh()
      setNotice('Utilizzo rimosso.')
    } catch (reason: unknown) {
      setSecondaryError(errorMessage(reason))
    }
  }

  if (error) {
    return <ErrorView message={error} action={<Link to="/" className="button button-primary">Torna al guardaroba</Link>} />
  }
  if (!item) return <LoadingView label="Preparo la storia del capo…" />

  const daysSince = stats?.days_since_last_worn

  return (
    <section>
      <div className="detail-hero">
        <div className="detail-media">
          <ItemImage src={itemImageUrl(item.id)} alt={item.name} loading="eager" />
        </div>

        <div className="detail-summary">
          <Link to="/" className="detail-back"><Icon name="arrow-left" size={16} /> Torna al guardaroba</Link>
          <div className="eyebrow">Capo #{item.id}</div>
          <h1>{item.name}</h1>
          <div className="detail-category">{[item.category, item.color].filter(Boolean).join(' · ') || 'Da classificare'}</div>
          <div className="detail-badges">
            <StatusBadge condition={item.condition} />
            {stats?.is_ghost && !item.retired_at && <span className="ghost-badge">Fantasma · mai indossato da {stats.ghost_after_days}+ giorni</span>}
            {item.retired_at && <span className="retired-badge">In seconda vita dal {fmtDate(item.retired_at)}</span>}
          </div>

          <div className="detail-metrics">
            <div className="detail-metric"><span>Utilizzi</span><strong>{stats?.wear_count ?? '—'}</strong></div>
            <div className="detail-metric"><span>Cost-per-wear</span><strong>{stats?.cost_per_wear != null ? `€ ${stats.cost_per_wear.toFixed(2)}` : '—'}</strong></div>
            <div className="detail-metric"><span>Ultimo uso</span><strong>{stats?.last_worn ? (daysSince === 0 ? 'Oggi' : `${daysSince}g fa`) : 'Mai'}</strong></div>
          </div>

          {notice && <div className="notice notice-success" role="status"><Icon name="check" size={17} /> {notice}</div>}
          {secondaryError && <div className="error" role="alert"><Icon name="circle-alert" size={17} /> {secondaryError}</div>}

          <div className="detail-actions">
            {!item.retired_at && (
              <button type="button" onClick={() => void onLogWear()} disabled={logging || deleting}>
                <Icon name="check" size={17} /> {logging ? 'Registro…' : 'Indossato oggi'}
              </button>
            )}
            <Link to={`/items/${item.id}/edit`} className="button button-secondary"><Icon name="edit" size={17} /> Modifica</Link>
            <button type="button" className="button button-secondary" onClick={() => void onReclassify()} disabled={reclassifying || deleting}>
              <Icon name="wand" size={17} /> {reclassifying ? 'Analizzo…' : 'Rianalizza foto'}
            </button>
          </div>
        </div>
      </div>

      <div className="content-grid">
        <section className="panel" aria-labelledby="identity-title">
          <div className="eyebrow">Carta d’identità</div>
          <h2 id="identity-title" style={{ margin: '6px 0 12px', fontFamily: 'var(--font-display)', fontWeight: 600 }}>Dettagli del capo</h2>
          <dl className="data-list">
            <div className="data-row"><dt>Categoria</dt><dd>{item.category ?? 'Da verificare'}</dd></div>
            <div className="data-row"><dt>Colore</dt><dd>{item.color ?? 'Da verificare'}</dd></div>
            <div className="data-row">
              <dt>Confidenza classificazione</dt>
              <dd className="confidence-meter" style={{ color: item.classification_confidence != null && item.classification_confidence >= .7 ? 'var(--ok)' : 'var(--warn)' }}>
                <span className="confidence-dot" /> {confidenceLabel(item.classification_confidence)}
                {item.classification_confidence != null && ` · ${Math.round(item.classification_confidence * 100)}%`}
              </dd>
            </div>
            <div className="data-row"><dt>Prezzo di acquisto</dt><dd>{item.price != null ? `€ ${item.price.toFixed(2)}` : 'Non indicato'}</dd></div>
            <div className="data-row"><dt>Data di acquisto</dt><dd>{fmtDate(item.purchase_date)}</dd></div>
            <div className="data-row"><dt>Aggiunto a ClosetAI</dt><dd>{fmtDate(item.created_at, true)}</dd></div>
          </dl>
        </section>

        <section className="wear-history" aria-labelledby="wear-title" style={{ marginTop: 0 }}>
          <div className="eyebrow">Uso reale</div>
          <h2 id="wear-title">La sua storia</h2>
          <p className="muted" style={{ fontSize: 11 }}>Ogni utilizzo abbassa il cost-per-wear e allunga il valore del capo.</p>
          {wears.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>Nessun utilizzo registrato.</p>
          ) : (
            <ul>
              {wears.slice(0, 8).map((event) => (
                <li key={event.id}>
                  <span><strong>{fmtDate(event.worn_on)}</strong>{event.occasion && <span className="muted"> · {event.occasion}</span>}</span>
                  <button type="button" className="del-event" aria-label={`Rimuovi utilizzo del ${fmtDate(event.worn_on)}`} onClick={() => void onDeleteWear(event)}>Rimuovi</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <AiDescription
        item={item}
        llmConfigured={llmStatus?.configured ?? false}
        onUpdated={(description) => setItem({ ...item, description })}
      />

      <TryOnPanel item={item} />

      <div id="circular">
        <CircularSection item={item} onItemRefresh={() => void refresh()} />
      </div>

      <section className="panel" style={{ marginTop: 16, borderColor: '#ebc9c2' }}>
        <div className="eyebrow" style={{ color: 'var(--danger)' }}>Zona delicata</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap', marginTop: 8 }}>
          <div>
            <h3 style={{ margin: 0 }}>Elimina definitivamente il capo</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 11 }}>Verranno rimossi anche foto, utilizzi e azioni associate.</p>
          </div>
          <button type="button" className="button button-danger" onClick={() => void onDelete()} disabled={deleting || reclassifying}>
            <Icon name="trash" size={17} /> {deleting ? 'Elimino…' : 'Elimina capo'}
          </button>
        </div>
      </section>
    </section>
  )
}
