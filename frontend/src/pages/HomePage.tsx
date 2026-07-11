import { useCallback, useEffect, useMemo, useState, type MouseEvent } from 'react'
import { Link } from 'react-router-dom'

import Icon from '../components/Icon'
import ItemImage from '../components/ItemImage'
import LifecycleRail from '../components/LifecycleRail'
import StatusBadge from '../components/StatusBadge'
import { EmptyView, ErrorView } from '../components/StateView'
import { errorMessage } from '../api/client'
import { getImpactStats, type ImpactStats } from '../api/circular'
import { itemImageUrl, listItems, type Item } from '../api/items'
import {
  getGapAnalysis,
  getWardrobeStats,
  type GapAnalysis,
  type WardrobeStats,
} from '../api/stats'
import { logWear } from '../api/wear'

type StatusFilter = 'all' | 'active' | 'retired'

export default function HomePage() {
  const [items, setItems] = useState<Item[] | null>(null)
  const [stats, setStats] = useState<WardrobeStats | null>(null)
  const [impact, setImpact] = useState<ImpactStats | null>(null)
  const [gap, setGap] = useState<GapAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [signalError, setSignalError] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [wearing, setWearing] = useState<number | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [mutationError, setMutationError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState<StatusFilter>('active')

  const loadSignals = useCallback(async () => {
    const results = await Promise.allSettled([
      getWardrobeStats({ topN: 5 }),
      getImpactStats(),
      getGapAnalysis(),
    ])
    const [statsResult, impactResult, gapResult] = results
    if (statsResult.status === 'fulfilled') setStats(statsResult.value)
    if (impactResult.status === 'fulfilled') setImpact(impactResult.value)
    if (gapResult.status === 'fulfilled') setGap(gapResult.value)
    setSignalError(results.some((result) => result.status === 'rejected'))
  }, [])

  const load = useCallback(async () => {
    setRefreshing(true)
    try {
      setItems(await listItems({ limit: 200 }))
      setError(null)
    } catch (e: unknown) {
      setError(errorMessage(e))
    } finally {
      setRefreshing(false)
    }
    await loadSignals()
  }, [loadSignals])

  useEffect(() => {
    void load()
  }, [load])

  async function onQuickWear(ev: MouseEvent<HTMLButtonElement>, item: Item) {
    ev.preventDefault()
    if (wearing != null) return
    setWearing(item.id)
    setNotice(null)
    setMutationError(null)
    try {
      await logWear(item.id)
      setNotice(`Utilizzo registrato per ${item.name}.`)
      await loadSignals()
    } catch (e: unknown) {
      setMutationError(errorMessage(e))
    } finally {
      setWearing(null)
    }
  }

  const categories = useMemo(() => {
    const values = new Set<string>()
    for (const item of items ?? []) if (item.category) values.add(item.category)
    return [...values].sort((a, b) => a.localeCompare(b, 'it'))
  }, [items])

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('it')
    return (items ?? []).filter((item) => {
      if (status === 'active' && item.retired_at) return false
      if (status === 'retired' && !item.retired_at) return false
      if (category && item.category !== category) return false
      if (!q) return true
      return `${item.name} ${item.category ?? ''} ${item.color ?? ''}`.toLocaleLowerCase('it').includes(q)
    })
  }, [items, search, category, status])

  const activeItems = useMemo(() => (items ?? []).filter((item) => !item.retired_at), [items])
  const needsCare = activeItems.filter((item) => item.condition === 'usurato' || item.condition === 'danneggiato').length
  const unknownCondition = activeItems.filter((item) => item.condition == null).length
  const firstGap = gap?.gaps[0]
  function clearFilters() {
    setSearch('')
    setCategory('')
    setStatus('active')
  }

  if (error && items == null) {
    return (
      <ErrorView
        message={error}
        action={<button type="button" onClick={() => void load()}><Icon name="refresh" size={17} /> Riprova</button>}
      />
    )
  }

  return (
    <>
      <section className="home-hero">
        <div className="home-hero-copy">
          <div className="eyebrow">Il guardaroba che lavora per te</div>
          <h1>Vesti meglio.<br />Compra meno.</h1>
          <p>
            ClosetAI trasforma ciò che possiedi in outfit, cura e impatto misurabile—
            così ogni capo viene usato più a lungo.
          </p>
          <div className="button-row">
            <Link to="/today" className="button button-primary">
              <Icon name="sparkles" size={18} /> Crea l'outfit di oggi
            </Link>
            <Link to="/items/new" className="button button-secondary">
              <Icon name="camera" size={18} /> Aggiungi un capo
            </Link>
          </div>
        </div>
        <Link to="/dashboard#circular" className="hero-impact">
          <span className="hero-impact-icon"><Icon name="leaf" size={24} /></span>
          <div>
            <span className="hero-impact-label">Impatto verde</span>
            <strong className="hero-impact-value">
              {impact ? impact.total_co2_saved_kg.toFixed(1) : '—'}<small> kg</small>
            </strong>
            <p>CO₂eq evitata grazie a riparazione, riuso e seconda vita.</p>
          </div>
          <span className="hero-impact-link">
            Esplora il tuo impatto <Icon name="arrow-right" size={17} />
          </span>
        </Link>
      </section>

      {signalError && (
        <div className="notice notice-warning" role="status" style={{ marginTop: 14 }}>
          <Icon name="circle-alert" size={17} /> Alcuni indicatori non sono aggiornati. Il guardaroba resta disponibile.
        </div>
      )}

      <section className="signal-grid" aria-label="Segnali principali del guardaroba">
        <Link to="/#wardrobe" className="signal-card usage">
          <div className="signal-card-top">
            <span className="signal-icon"><Icon name="trend" size={20} /></span>
            <span className="signal-kicker">Uso reale</span>
          </div>
          <strong className="signal-value">{stats?.total_wears ?? '—'} utilizzi</strong>
          <p>{stats ? `Media ${stats.avg_wears_per_item.toFixed(1)} per capo attivo.` : 'Sto calcolando il ritmo del tuo guardaroba.'}</p>
        </Link>

        <Link to="/dashboard#condition" className="signal-card state">
          <div className="signal-card-top">
            <span className="signal-icon"><Icon name="wrench" size={20} /></span>
            <span className="signal-kicker">Stato dei capi</span>
          </div>
          <strong className="signal-value">{needsCare > 0 ? `${needsCare} da curare` : 'Tutto in ordine'}</strong>
          <p>{unknownCondition > 0 ? `${unknownCondition} capi aspettano ancora una diagnosi.` : 'Tutti i capi attivi hanno uno stato verificato.'}</p>
        </Link>

        <Link to="/dashboard#gaps" className="signal-card gap">
          <div className="signal-card-top">
            <span className="signal-icon"><Icon name="gap" size={20} /></span>
            <span className="signal-kicker">Gap del guardaroba</span>
          </div>
          <strong className="signal-value">{gap?.balanced ? 'Ben bilanciato' : firstGap?.label ?? 'In analisi'}</strong>
          <p>{gap?.balanced ? 'Non emerge nessun acquisto necessario.' : firstGap?.advice ?? 'La rete sta cercando eventuali vuoti funzionali.'}</p>
        </Link>
      </section>

      <LifecycleRail />

      <section id="wardrobe" className="wardrobe-section">
        <div className="section-heading">
          <div>
            <div className="eyebrow">La tua collezione</div>
            <h2>Guardaroba</h2>
          </div>
          <div className="button-row">
            <span className="result-count">{filtered.length} di {items?.length ?? 0} capi</span>
            <button type="button" className="button button-secondary button-small" onClick={() => void load()} disabled={refreshing}>
              <Icon name="refresh" size={15} /> {refreshing ? 'Aggiorno…' : 'Aggiorna'}
            </button>
          </div>
        </div>

        <div className="wardrobe-toolbar">
          <label className="search-field">
            <span className="sr-only">Cerca nel guardaroba</span>
            <Icon name="search" size={18} />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Cerca per nome, categoria o colore"
            />
          </label>
          <label>
            <span className="sr-only">Filtra per categoria</span>
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">Tutte le categorie</option>
              {categories.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <div className="segmented-control" role="group" aria-label="Stato del guardaroba">
            {(['active', 'all', 'retired'] as const).map((value) => (
              <button
                key={value}
                type="button"
                className={status === value ? 'active' : ''}
                aria-pressed={status === value}
                onClick={() => setStatus(value)}
              >
                {value === 'active' ? 'Attivi' : value === 'all' ? 'Tutti' : 'Seconda vita'}
              </button>
            ))}
          </div>
        </div>

        {notice && <div className="notice notice-success" role="status"><Icon name="check" size={17} /> {notice}</div>}
        {mutationError && <div className="error" role="alert"><Icon name="circle-alert" size={17} /> {mutationError}</div>}

        {items == null ? (
          <div className="items-grid" aria-label="Caricamento guardaroba">
            {Array.from({ length: 8 }, (_, index) => <div className="skeleton card" key={index} />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyView
            icon={items.length === 0 ? 'hanger' : 'search'}
            title={items.length === 0 ? 'Il tuo guardaroba parte da qui' : 'Nessun capo corrisponde'}
            message={items.length === 0 ? 'Fotografa il primo capo: ClosetAI riconoscerà categoria e colore.' : 'Prova a modificare o azzerare i filtri.'}
            action={items.length === 0
              ? <Link to="/items/new" className="button button-primary"><Icon name="camera" size={17} /> Aggiungi il primo capo</Link>
              : <button type="button" className="button button-secondary" onClick={clearFilters}>Azzera filtri</button>}
          />
        ) : (
          <div className="items-grid">
            {filtered.map((item) => (
              <article key={item.id} className="item-card">
                <Link to={`/items/${item.id}`} className="item-card-media" aria-label={`Apri ${item.name}`}>
                  {item.retired_at && <span className="item-card-retired">Seconda vita</span>}
                  <ItemImage src={itemImageUrl(item.id)} alt={item.name} />
                </Link>
                <div className="item-card-body">
                  <div className="item-card-heading">
                    <div>
                      <Link to={`/items/${item.id}`} className="item-card-name">{item.name}</Link>
                      <div className="item-card-meta">{[item.category, item.color].filter(Boolean).join(' · ') || 'Da classificare'}</div>
                    </div>
                    {!item.retired_at && <StatusBadge condition={item.condition} />}
                  </div>
                  <div className="item-card-footer">
                    <span className="item-card-price">{item.price != null ? `€ ${item.price.toFixed(2)}` : 'Prezzo non indicato'}</span>
                    {!item.retired_at && (
                      <button
                        type="button"
                        className="quick-wear"
                        aria-label={`Registra che hai indossato ${item.name} oggi`}
                        onClick={(event) => void onQuickWear(event, item)}
                        disabled={wearing === item.id}
                      >
                        <Icon name="check" size={13} /> {wearing === item.id ? 'Registro…' : 'Indossato'}
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  )
}
