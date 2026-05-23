import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import CircularSection from '../components/CircularSection'
import { deleteItem, getItem, itemImageUrl, reclassifyItem, type Item } from '../api/items'
import { getItemStats, type ItemStats } from '../api/stats'
import { deleteWear, listWears, logWear, type WearEvent } from '../api/wear'

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100)
  const color = confidence >= 0.7 ? 'var(--ok)' : confidence >= 0.4 ? 'var(--accent)' : 'var(--danger)'
  return (
    <span title={`Confidenza classificazione: ${pct}%`} style={{ color, fontWeight: 600 }}>
      {pct}%
    </span>
  )
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('it-IT')
  } catch {
    return iso
  }
}

export default function ItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)
  const [stats, setStats] = useState<ItemStats | null>(null)
  const [wears, setWears] = useState<WearEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [reclassifying, setReclassifying] = useState(false)
  const [logging, setLogging] = useState(false)

  const itemId = Number(id)
  const isValidId = Number.isInteger(itemId) && itemId > 0

  const refresh = useCallback(async () => {
    if (!isValidId) return
    try {
      const [it, st, ws] = await Promise.all([
        getItem(itemId),
        getItemStats(itemId),
        listWears(itemId),
      ])
      setItem(it)
      setStats(st)
      setWears(ws)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [itemId, isValidId])

  useEffect(() => {
    if (!isValidId) {
      setError('ID non valido')
      return
    }
    void refresh()
  }, [refresh, isValidId])

  async function onDelete() {
    if (!item || deleting) return
    if (!confirm(`Eliminare "${item.name}" (#${item.id})?`)) return
    setDeleting(true)
    try {
      await deleteItem(item.id)
      navigate('/')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setDeleting(false)
    }
  }

  async function onReclassify() {
    if (!item || reclassifying) return
    setReclassifying(true)
    setError(null)
    try {
      setItem(await reclassifyItem(item.id))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setReclassifying(false)
    }
  }

  async function onLogWear() {
    if (!item || logging) return
    setLogging(true)
    try {
      await logWear(item.id)
      await refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLogging(false)
    }
  }

  async function onDeleteWear(eventId: number) {
    if (!confirm('Eliminare questo evento di utilizzo?')) return
    try {
      await deleteWear(eventId)
      await refresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  if (error) {
    return (
      <p className="error">
        Errore: {error} — <Link to="/">torna al guardaroba</Link>
      </p>
    )
  }
  if (item == null) return <p className="muted">Caricamento…</p>

  const cpw = stats?.cost_per_wear
  const daysSince = stats?.days_since_last_worn

  return (
    <section>
      <div className="detail">
        <div>
          {item.image_path ? (
            <img src={itemImageUrl(item.id)} alt={item.name} />
          ) : (
            <div className="panel muted">Nessuna immagine</div>
          )}
        </div>
        <div>
          <h2 style={{ marginTop: 0 }}>
            {item.name}
            {item.condition && (
              <span className={`condition-badge ${item.condition}`}>{item.condition}</span>
            )}
            {item.retired_at && <span className="retired-badge">ritirato</span>}
            {stats?.is_ghost && !item.retired_at && (
              <span className="ghost-badge">Capo fantasma</span>
            )}
          </h2>
          <div className="meta">
            <div className="kv"><span className="muted">ID</span><b>#{item.id}</b></div>
            <div className="kv"><span className="muted">Categoria</span><b>{item.category ?? '—'}</b></div>
            <div className="kv"><span className="muted">Colore</span><b>{item.color ?? '—'}</b></div>
            <div className="kv">
              <span className="muted">Confidenza classificatore</span>
              <b>
                {item.classification_confidence != null ? (
                  <ConfidenceBadge confidence={item.classification_confidence} />
                ) : (
                  '—'
                )}
              </b>
            </div>
            <div className="kv">
              <span className="muted">Prezzo</span>
              <b>{item.price != null ? `€ ${item.price.toFixed(2)}` : '—'}</b>
            </div>
            <div className="kv">
              <span className="muted">Data acquisto</span>
              <b>{item.purchase_date ?? '—'}</b>
            </div>
            <div className="kv">
              <span className="muted">Utilizzi</span>
              <b>{stats?.wear_count ?? 0}</b>
            </div>
            <div className="kv">
              <span className="muted">Cost-per-wear</span>
              <b>{cpw != null ? `€ ${cpw.toFixed(2)}` : '—'}</b>
            </div>
            <div className="kv">
              <span className="muted">Ultimo utilizzo</span>
              <b>
                {stats?.last_worn
                  ? `${stats.last_worn}${daysSince != null ? ` (${daysSince}g fa)` : ''}`
                  : 'mai'}
              </b>
            </div>
            <div className="kv">
              <span className="muted">Creato</span>
              <b>{new Date(item.created_at).toLocaleString('it-IT')}</b>
            </div>
          </div>
          <div className="actions">
            <button onClick={onLogWear} disabled={logging || deleting}>
              {logging ? '…' : 'Indossato oggi'}
            </button>
            <button onClick={onReclassify} disabled={reclassifying || deleting} className="ghost">
              {reclassifying ? 'Riclassifico…' : 'Riclassifica'}
            </button>
            <button className="danger" onClick={onDelete} disabled={deleting || reclassifying}>
              {deleting ? 'Elimino…' : 'Elimina'}
            </button>
            <button
              type="button"
              className="ghost"
              onClick={() => navigate('/')}
              disabled={deleting || reclassifying}
            >
              Indietro
            </button>
          </div>
        </div>
      </div>

      <div className="wear-history">
        <h3>Storico utilizzi ({wears.length})</h3>
        {wears.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>Nessun utilizzo registrato.</p>
        ) : (
          <ul>
            {wears.map((ev) => (
              <li key={ev.id}>
                <span>
                  <b>{fmtDate(ev.worn_on)}</b>
                  {ev.occasion && <span className="muted"> · {ev.occasion}</span>}
                </span>
                <button className="del-event" onClick={() => void onDeleteWear(ev.id)}>
                  rimuovi
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <CircularSection item={item} onItemRefresh={() => void refresh()} />
    </section>
  )
}
