import { useCallback, useEffect, useMemo, useState, type MouseEvent } from 'react'
import { Link } from 'react-router-dom'

import { itemImageUrl, listItems, type Item } from '../api/items'
import { logWear } from '../api/wear'
import { getWardrobeStats, type WardrobeStats } from '../api/stats'

type StatusFilter = 'all' | 'active' | 'retired'

export default function HomePage() {
  const [items, setItems] = useState<Item[] | null>(null)
  const [stats, setStats] = useState<WardrobeStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [wearing, setWearing] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string>('')
  const [status, setStatus] = useState<StatusFilter>('active')

  const load = useCallback(async () => {
    setRefreshing(true)
    try {
      const [list, ws] = await Promise.all([
        listItems({ limit: 200 }),
        getWardrobeStats({ topN: 5 }),
      ])
      setItems(list)
      setStats(ws)
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
      void load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setWearing(null)
    }
  }

  const categories = useMemo(() => {
    if (!items) return []
    const set = new Set<string>()
    for (const it of items) {
      if (it.category) set.add(it.category)
    }
    return [...set].sort()
  }, [items])

  const filtered = useMemo(() => {
    if (!items) return []
    const q = search.trim().toLowerCase()
    return items.filter((it) => {
      if (status === 'active' && it.retired_at) return false
      if (status === 'retired' && !it.retired_at) return false
      if (category && it.category !== category) return false
      if (q) {
        const hay = `${it.name} ${it.category ?? ''} ${it.color ?? ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [items, search, category, status])

  if (error) {
    return (
      <p className="error">
        Errore: {error} <button className="ghost" onClick={() => void load()}>Riprova</button>
      </p>
    )
  }
  if (items == null) {
    return (
      <div>
        <div className="hero-banner">
          {[0, 1, 2, 3].map((i) => (
            <div className="metric" key={i}>
              <div className="skeleton line short" />
              <div className="skeleton line" style={{ height: 22, width: '60%' }} />
            </div>
          ))}
        </div>
        <div className="items-grid">
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div className="skeleton card" key={i} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <>
      <nav className="story-strip" aria-label="Il ciclo di vita di un capo">
        <Link to="/items/new"><span className="step-num">1</span><span className="step-icon">📷</span>Fotografalo</Link>
        <Link to="/"><span className="step-num">2</span><span className="step-icon">✓</span>Indossalo</Link>
        <Link to="/today"><span className="step-num">3</span><span className="step-icon">👗</span>Cosa metto?</Link>
        <Link to="/dashboard"><span className="step-num">4</span><span className="step-icon">🛠️</span>Riparalo</Link>
        <Link to="/dashboard"><span className="step-num">5</span><span className="step-icon">🧩</span>Serve altro?</Link>
        <Link to="/dashboard"><span className="step-num">6</span><span className="step-icon">♻️</span>Seconda vita</Link>
      </nav>

      {stats && (
        <div className="hero-banner">
          <div className="metric">
            <span className="label">Capi attivi</span>
            <span className="value">{stats.total_items}</span>
            <span className="sub">nel guardaroba</span>
          </div>
          <div className="metric">
            <span className="label">Utilizzi totali</span>
            <span className="value">{stats.total_wears}</span>
            <span className="sub">media {stats.avg_wears_per_item.toFixed(1)} / capo</span>
          </div>
          <div className="metric">
            <span className="label">Capi fantasma</span>
            <span className="value" style={{ color: stats.ghost_count > 0 ? 'var(--warn)' : 'var(--ok)' }}>
              {stats.ghost_count}
            </span>
            <span className="sub">mai indossati &gt; 30g</span>
          </div>
          <div className="metric">
            <span className="label">Cost-per-wear</span>
            <span className="value">
              {stats.avg_cost_per_wear != null ? `€ ${stats.avg_cost_per_wear.toFixed(2)}` : '—'}
            </span>
            <span className="sub">medio</span>
          </div>
        </div>
      )}

      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Guardaroba</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
          <span className="count">
            {filtered.length} di {items.length} {items.length === 1 ? 'capo' : 'capi'}
          </span>
          <button className="ghost" onClick={() => void load()} disabled={refreshing}>
            {refreshing ? '…' : 'Aggiorna'}
          </button>
        </div>
      </div>

      <div className="filter-bar">
        <input
          type="text"
          placeholder="🔍 Cerca per nome, categoria, colore…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Tutte le categorie</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          type="button"
          className={`chip ${status === 'all' ? 'active' : ''}`}
          onClick={() => setStatus('all')}
        >
          Tutti
        </button>
        <button
          type="button"
          className={`chip ${status === 'active' ? 'active' : ''}`}
          onClick={() => setStatus('active')}
        >
          Attivi
        </button>
        <button
          type="button"
          className={`chip ${status === 'retired' ? 'active' : ''}`}
          onClick={() => setStatus('retired')}
        >
          Ritirati
        </button>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          {items.length === 0 ? (
            <>
              Nessun capo nel guardaroba.{' '}
              <Link to="/items/new">Aggiungi il primo →</Link>
            </>
          ) : (
            'Nessun capo corrisponde ai filtri.'
          )}
        </div>
      ) : (
        <div className="items-grid">
          {filtered.map((it) => (
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
              {!it.retired_at && (
                <button
                  type="button"
                  className="quick-wear"
                  title="Registra che l'hai indossato oggi"
                  onClick={(ev) => void onQuickWear(ev, it)}
                  disabled={wearing === it.id}
                >
                  {wearing === it.id ? '…' : '✓ oggi'}
                </button>
              )}
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
