import { useCallback, useEffect, useState, type MouseEvent } from 'react'
import { Link } from 'react-router-dom'

import { itemImageUrl, listItems, type Item } from '../api/items'
import { logWear } from '../api/wear'

export default function HomePage() {
  const [items, setItems] = useState<Item[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [wearing, setWearing] = useState<number | null>(null)

  const load = useCallback(async () => {
    setRefreshing(true)
    try {
      setItems(await listItems({ limit: 200 }))
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function onQuickWear(ev: MouseEvent<HTMLButtonElement>, item: Item) {
    ev.preventDefault()
    ev.stopPropagation()
    if (wearing != null) return
    setWearing(item.id)
    try {
      await logWear(item.id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setWearing(null)
    }
  }

  if (error) {
    return (
      <p className="error">
        Errore: {error} <button className="ghost" onClick={() => void load()}>Riprova</button>
      </p>
    )
  }
  if (items == null) return <p className="muted">Caricamento…</p>

  return (
    <>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Guardaroba</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
          <Link to="/dashboard" className="ghost" style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)' }}>
            Dashboard
          </Link>
          <span className="count">
            {items.length} {items.length === 1 ? 'capo' : 'capi'}
          </span>
          <button className="ghost" onClick={() => void load()} disabled={refreshing}>
            {refreshing ? '…' : 'Aggiorna'}
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          Nessun capo nel guardaroba.{' '}
          <Link to="/items/new">Aggiungi il primo →</Link>
        </div>
      ) : (
        <div className="items-grid">
          {items.map((it) => (
            <Link key={it.id} to={`/items/${it.id}`} className="item-card">
              {it.image_path && (
                <img src={itemImageUrl(it.id)} alt={it.name} loading="lazy" />
              )}
              <div className="body">
                <strong>{it.name}</strong>
                <div className="muted">
                  {[it.category, it.color].filter(Boolean).join(' • ') || '—'}
                </div>
                {it.price != null && (
                  <div className="price">€ {it.price.toFixed(2)}</div>
                )}
              </div>
              <button
                type="button"
                className="quick-wear"
                title="Registra che l'hai indossato oggi"
                onClick={(ev) => void onQuickWear(ev, it)}
                disabled={wearing === it.id}
              >
                {wearing === it.id ? '…' : '✓ oggi'}
              </button>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
