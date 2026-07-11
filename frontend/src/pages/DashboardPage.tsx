import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import CoachCard from '../components/CoachCard'
import Icon from '../components/Icon'
import { ErrorView, LoadingView } from '../components/StateView'
import { getLlmStatus, type LlmStatus } from '../api/ai'
import { errorMessage } from '../api/client'
import { getImpactStats, type ImpactStats } from '../api/circular'
import { listItems, type Item } from '../api/items'
import {
  getGapAnalysis,
  getGhostItems,
  getWardrobeStats,
  type GapAnalysis,
  type GhostItem,
  type WardrobeStats,
} from '../api/stats'

function co2Equivalents(kg: number) {
  return {
    km: Math.round(kg / .18),
    flights: kg / 80,
    forest: kg / 8,
  }
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      <span className="metric-sub">{sub}</span>
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<WardrobeStats | null>(null)
  const [impact, setImpact] = useState<ImpactStats | null>(null)
  const [gap, setGap] = useState<GapAnalysis | null>(null)
  const [ghosts, setGhosts] = useState<GhostItem[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [partialError, setPartialError] = useState(false)
  const [loading, setLoading] = useState(true)
  const [ghostDays, setGhostDays] = useState(30)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const results = await Promise.allSettled([
      getWardrobeStats({ ghostAfterDays: ghostDays, topN: 5 }),
      getImpactStats(),
      getGapAnalysis(),
      getGhostItems({ ghostAfterDays: ghostDays }),
      listItems({ limit: 200 }),
      getLlmStatus(),
    ])
    const [statsResult, impactResult, gapResult, ghostsResult, itemsResult, llmResult] = results
    if (statsResult.status === 'fulfilled') setStats(statsResult.value)
    if (impactResult.status === 'fulfilled') setImpact(impactResult.value)
    if (gapResult.status === 'fulfilled') setGap(gapResult.value)
    if (ghostsResult.status === 'fulfilled') setGhosts(ghostsResult.value)
    if (itemsResult.status === 'fulfilled') setItems(itemsResult.value)
    if (llmResult.status === 'fulfilled') setLlmStatus(llmResult.value)
    if (statsResult.status === 'rejected') setError(errorMessage(statsResult.reason))
    setPartialError(results.slice(1).some((result) => result.status === 'rejected'))
    setLoading(false)
  }, [ghostDays])

  useEffect(() => {
    void load()
  }, [load])

  const activeItems = useMemo(() => items.filter((item) => !item.retired_at), [items])
  const conditionCounts = useMemo(() => ({
    buono: activeItems.filter((item) => item.condition === 'buono').length,
    usurato: activeItems.filter((item) => item.condition === 'usurato').length,
    danneggiato: activeItems.filter((item) => item.condition === 'danneggiato').length,
    unknown: activeItems.filter((item) => item.condition == null).length,
  }), [activeItems])

  const conditionTotal = Math.max(activeItems.length, 1)
  const maxActionCo2 = Math.max(...Object.values(impact?.co2_by_type ?? {}), 1)
  const equivalent = co2Equivalents(impact?.total_co2_saved_kg ?? 0)

  if (error && !stats) {
    return <ErrorView message={error} action={<button type="button" onClick={() => void load()}><Icon name="refresh" size={17} /> Riprova</button>} />
  }
  if (!stats) return <LoadingView label="Misuro il tuo impatto…" />

  return (
    <section>
      <section className="impact-hero">
        <div>
          <div className="eyebrow" style={{ color: 'var(--lime)' }}>Il valore di usare meglio</div>
          <h1>Il tuo guardaroba sta già facendo la differenza.</h1>
          <p>
            Impatto ambientale, stato dei capi e gap funzionali diventano azioni concrete:
            riparare, riscoprire, donare—e comprare solo quando serve davvero.
          </p>
        </div>
        <div className="impact-total">
          <span>CO₂eq evitata</span>
          <strong>{impact?.total_co2_saved_kg.toFixed(1) ?? '—'}</strong>
          <small>kg attraverso {impact?.total_actions ?? 0} azioni circolari</small>
        </div>
      </section>

      <div className="toolbar" style={{ marginTop: 14 }}>
        <div className="notice" style={{ margin: 0 }}>
          <Icon name="clock" size={16} /> Un “capo fantasma” non viene usato da almeno
          <label style={{ margin: 0 }}>
            <span className="sr-only">Soglia giorni per capo fantasma</span>
            <select value={ghostDays} onChange={(event) => setGhostDays(Number(event.target.value))} style={{ width: 88, minHeight: 36, paddingBlock: 5 }}>
              {[30, 60, 90, 180].map((days) => <option key={days} value={days}>{days} giorni</option>)}
            </select>
          </label>
        </div>
        <button type="button" className="button button-secondary button-small" onClick={() => void load()} disabled={loading}>
          <Icon name="refresh" size={15} /> {loading ? 'Aggiorno…' : 'Aggiorna dati'}
        </button>
      </div>

      {partialError && <div className="notice notice-warning" role="status"><Icon name="circle-alert" size={17} /> Alcuni approfondimenti non sono disponibili; i dati principali restano aggiornati.</div>}

      <div className="metric-grid">
        <MetricCard label="Capi attivi" value={String(stats.total_items)} sub={`${items.length - activeItems.length} in seconda vita`} />
        <MetricCard label="Utilizzi registrati" value={String(stats.total_wears)} sub={`media ${stats.avg_wears_per_item.toFixed(1)} per capo`} />
        <MetricCard label="Cost-per-wear medio" value={stats.avg_cost_per_wear != null ? `€ ${stats.avg_cost_per_wear.toFixed(2)}` : '—'} sub="sui capi con prezzo e utilizzi" />
        <MetricCard label="Capi da riscoprire" value={String(stats.ghost_count)} sub={`inattivi da più di ${stats.ghost_after_days} giorni`} />
      </div>

      <CoachCard llmConfigured={llmStatus?.configured ?? false} ghostAfterDays={ghostDays} />

      <div className="insight-grid">
        <section id="gaps" className="insight-card" aria-labelledby="gap-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Gap del guardaroba</div>
              <h2 id="gap-title">Cosa manca davvero?</h2>
              <p>Una rete neurale cerca vuoti funzionali, non nuove scuse per comprare.</p>
            </div>
            <span className="insight-icon"><Icon name="gap" size={21} /></span>
          </header>
          {gap?.balanced ? (
            <div className="gap-result gap-result-balanced">
              <span className="gap-probability" style={{ color: 'var(--ok)' }}>Equilibrato</span>
              <h3>Nessun acquisto necessario</h3>
              <p>Il guardaroba copre già le funzioni principali. Concentrati sulle combinazioni.</p>
            </div>
          ) : gap?.gaps.length ? (
            <div style={{ display: 'grid', gap: 9 }}>
              {gap.gaps.map((item) => (
                <div className="gap-result" key={item.code}>
                  {item.probability != null && <span className="gap-probability">{Math.round(item.probability * 100)}% confidenza</span>}
                  <h3>{item.label}</h3>
                  <p>{item.advice}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">La gap analysis sarà disponibile quando il guardaroba avrà abbastanza dati.</p>
          )}
          {gap && <p className="muted" style={{ margin: '13px 0 0', fontSize: 9 }}>Fonte: {gap.source === 'neural-net' ? 'rete neurale addestrata' : 'regole esperte'} · {gap.n_colors} colori · {gap.total_items} capi analizzati</p>}
        </section>

        <section id="condition" className="insight-card" aria-labelledby="condition-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Stato dei capi</div>
              <h2 id="condition-title">Cosa richiede cura?</h2>
              <p>La manutenzione anticipata prolunga la vita del capo e ne protegge il valore.</p>
            </div>
            <span className="insight-icon" style={{ background: 'var(--sun-soft)', color: 'var(--warn)' }}><Icon name="wrench" size={21} /></span>
          </header>
          <div className="condition-list">
            {[
              ['In buono stato', conditionCounts.buono, ''],
              ['Da curare', conditionCounts.usurato, 'worn'],
              ['Danneggiati', conditionCounts.danneggiato, 'damaged'],
              ['Da verificare', conditionCounts.unknown, 'unknown'],
            ].map(([label, count, className]) => (
              <div className="condition-row" key={String(label)}>
                <span>{label}</span>
                <span className="condition-track"><span className={`condition-fill ${className}`} style={{ width: `${(Number(count) / conditionTotal) * 100}%` }} /></span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
          {(conditionCounts.usurato + conditionCounts.danneggiato) > 0 && (
            <p className="notice notice-warning" style={{ margin: '18px 0 0' }}><Icon name="wrench" size={16} /> {conditionCounts.usurato + conditionCounts.danneggiato} capi possono beneficiare di una piccola azione di cura.</p>
          )}
        </section>

        <section id="circular" className="insight-card" aria-labelledby="circular-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Impatto circolare</div>
              <h2 id="circular-title">Da azione a CO₂ evitata.</h2>
              <p>Ogni riparazione o seconda vita evita parte dell’impatto di un capo nuovo.</p>
            </div>
            <span className="insight-icon"><Icon name="recycle" size={21} /></span>
          </header>
          {impact && impact.total_actions > 0 ? (
            <div className="bar-list">
              {Object.entries(impact.actions_by_type).map(([type, count]) => {
                const co2 = impact.co2_by_type[type] ?? 0
                return (
                  <div key={type}>
                    <div className="bar-label"><strong style={{ textTransform: 'capitalize' }}>{type}</strong><span>{count} azioni · {co2.toFixed(1)} kg</span></div>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${(co2 / maxActionCo2) * 100}%` }} /></div>
                  </div>
                )
              })}
            </div>
          ) : <p className="muted">Registra una riparazione, donazione o vendita dal dettaglio di un capo.</p>}
          {impact && impact.total_co2_saved_kg > 0 && (
            <div className="analysis-note" style={{ marginTop: 18 }}>
              <Icon name="leaf" size={19} />
              <p><strong>Un impatto che si vede</strong>Equivale indicativamente a {equivalent.km.toLocaleString('it-IT')} km in auto evitati, {equivalent.flights.toFixed(2)} voli Pisa–Roma o l’assorbimento annuale di {equivalent.forest.toFixed(1)} m² di foresta.</p>
            </div>
          )}
        </section>

        <section className="insight-card" aria-labelledby="top-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Campioni di utilizzo</div>
              <h2 id="top-title">I capi che lavorano di più.</h2>
              <p>Il miglior investimento è quello che entra davvero nella tua vita.</p>
            </div>
            <span className="insight-icon"><Icon name="trend" size={21} /></span>
          </header>
          <ol className="rank-list">
            {stats.top_worn.map((item, index) => (
              <li key={item.item_id}>
                <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
                <Link to={`/items/${item.item_id}`}>{item.name}</Link>
                <span className="rank-value">{item.wear_count} usi</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="insight-card" aria-labelledby="ghost-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Rotazione</div>
              <h2 id="ghost-title">Capi da riscoprire.</h2>
              <p>Prima di cercare qualcosa di nuovo, prova a riportarne uno in un outfit.</p>
            </div>
            <span className="insight-icon" style={{ background: 'var(--sun-soft)', color: 'var(--warn)' }}><Icon name="hanger" size={21} /></span>
          </header>
          {ghosts.length === 0 ? (
            <div className="notice notice-success"><Icon name="check" size={17} /> Tutti i capi sono in rotazione.</div>
          ) : (
            <ol className="rank-list">
              {ghosts.slice(0, 5).map((item, index) => (
                <li key={item.item_id}>
                  <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
                  <Link to={`/items/${item.item_id}`}>{item.name}</Link>
                  <span className="rank-value">{item.days_owned ?? '?'}g</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="insight-card" aria-labelledby="investment-title">
          <header className="insight-card-header">
            <div>
              <div className="eyebrow">Valore economico</div>
              <h2 id="investment-title">Compra meno, usa meglio.</h2>
              <p>Prezzo e utilizzo raccontano se un acquisto sta generando valore reale.</p>
            </div>
            <span className="insight-icon" style={{ background: 'var(--blue-soft)', color: 'var(--blue)' }}><Icon name="euro" size={21} /></span>
          </header>
          <div className="detail-metrics" style={{ margin: 0 }}>
            <div className="detail-metric"><span>Valore catalogato</span><strong>{stats.total_investment != null ? `€ ${stats.total_investment.toFixed(0)}` : '—'}</strong></div>
            <div className="detail-metric"><span>CPW medio</span><strong>{stats.avg_cost_per_wear != null ? `€ ${stats.avg_cost_per_wear.toFixed(2)}` : '—'}</strong></div>
            <div className="detail-metric"><span>Media utilizzi</span><strong>{stats.avg_wears_per_item.toFixed(1)}</strong></div>
          </div>
          <p className="muted" style={{ margin: '14px 0 0', fontSize: 9 }}>Indicatori descrittivi del guardaroba catalogato; non sono valutazioni finanziarie.</p>
        </section>
      </div>
    </section>
  )
}
