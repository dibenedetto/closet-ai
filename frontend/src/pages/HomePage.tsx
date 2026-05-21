import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { itemImageUrl, listItems, type Item } from '../api/items'

export default function HomePage() {
  const [items, setItems] = useState<Item[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

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
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
