import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getImpactStats, type ImpactStats } from '../api/circular'
import {
  getGhostItems,
  getWardrobeStats,
  type GhostItem,
  type WardrobeStats,
} from '../api/stats'

function StatCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<WardrobeStats | null>(null)
  const [ghosts, setGhosts] = useState<GhostItem[]>([])
  const [impact, setImpact] = useState<ImpactStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [ghostDays, setGhostDays] = useState(30)

  useEffect(() => {
    let cancelled = false
    setError(null)
    Promise.all([
      getWardrobeStats({ ghostAfterDays: ghostDays, topN: 5 }),
      getGhostItems({ ghostAfterDays: ghostDays }),
      getImpactStats(),
    ])
      .then(([s, g, i]) => {
        if (!cancelled) {
          setStats(s)
          setGhosts(g)
          setImpact(i)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e))
        }
      })
    return () => {
      cancelled = true
    }
  }, [ghostDays])

  if (error) return <p className="error">Errore: {error}</p>
  if (stats == null) return <p className="muted">Caricamento…</p>

  return (
    <section>
      <div className="toolbar">
        <h2 style={{ margin: 0 }}>Dashboard impatto</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label htmlFor="ghost-days" className="muted" style={{ margin: 0 }}>
            Soglia fantasma (giorni)
          </label>
          <input
            id="ghost-days"
            type="number"
            min={1}
            max={365}
            value={ghostDays}
            onChange={(e) => setGhostDays(Number(e.target.value) || 30)}
            style={{ width: 80 }}
          />
          <Link
            to="/"
            className="ghost"
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)' }}
          >
            ← Guardaroba
          </Link>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Capi totali" value={String(stats.total_items)} />
        <StatCard
          label="Utilizzi totali"
          value={String(stats.total_wears)}
          sub={`media ${stats.avg_wears_per_item.toFixed(2)} / capo`}
        />
        <StatCard
          label="Capi fantasma"
          value={String(stats.ghost_count)}
          sub={`> ${stats.ghost_after_days} giorni senza utilizzo`}
        />
        <StatCard
          label="Investimento totale"
          value={stats.total_investment != null ? `€ ${stats.total_investment.toFixed(2)}` : '—'}
        />
        <StatCard
          label="Cost-per-wear medio"
          value={stats.avg_cost_per_wear != null ? `€ ${stats.avg_cost_per_wear.toFixed(2)}` : '—'}
          sub="sui capi con prezzo e ≥ 1 utilizzo"
        />
        {impact && (
          <>
            <StatCard
              label="CO₂ evitata"
              value={`${impact.total_co2_saved_kg.toFixed(1)} kg`}
              sub={`${impact.total_actions} azioni circolari`}
            />
            <StatCard
              label="Capi salvati"
              value={String(impact.repaired_items_count + impact.retired_items_count)}
              sub={`${impact.repaired_items_count} riparati · ${impact.retired_items_count} ritirati`}
            />
          </>
        )}
      </div>

      {impact && impact.total_actions > 0 && (
        <section className="panel" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Azioni circolari per tipo</h3>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
            {Object.entries(impact.actions_by_type).map(([type, count]) => (
              <div
                key={type}
                style={{
                  padding: 10,
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  background: 'var(--panel-2)',
                }}
              >
                <div className="muted" style={{ fontSize: 11, textTransform: 'capitalize' }}>{type}</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{count}</div>
                <div className="muted" style={{ fontSize: 11 }}>
                  −{(impact.co2_by_type[type] ?? 0).toFixed(1)} kg CO₂
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: '1fr 1fr' }}>
        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Top capi più indossati</h3>
          {stats.top_worn.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>Nessun utilizzo registrato.</p>
          ) : (
            <ol style={{ paddingLeft: 18, margin: 0 }}>
              {stats.top_worn.map((t) => (
                <li key={t.item_id} style={{ marginBottom: 6 }}>
                  <Link to={`/items/${t.item_id}`}>{t.name}</Link>{' '}
                  <span className="muted">— {t.wear_count} utilizzi</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="panel">
          <h3 style={{ marginTop: 0 }}>Capi fantasma</h3>
          {ghosts.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>Nessuno: tutti i capi sono stati indossati. 🎉</p>
          ) : (
            <ul style={{ paddingLeft: 0, listStyle: 'none', margin: 0 }}>
              {ghosts.map((g) => (
                <li
                  key={g.item_id}
                  style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}
                >
                  <Link to={`/items/${g.item_id}`}>{g.name}</Link>
                  <span className="muted">
                    {' '}— {g.days_owned ?? '?'}g posseduto
                    {g.price != null ? ` · € ${g.price.toFixed(2)}` : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </section>
  )
}
