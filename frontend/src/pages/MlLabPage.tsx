/**
 * ML Lab — pagina tecnica dedicata a training / test / eval delle reti
 * addestrate da noi. Tre sezioni:
 *
 *  1. Stato dei modelli (pesi presenti? metriche dal training) + dataset
 *  2. Prova la rete dello STATO: carica una foto → predizione live
 *  3. Prova la GAP ANALYSIS: simulatore what-if sui conteggi del guardaroba
 */
import { useEffect, useState } from 'react'

import PageHeader from '../components/PageHeader'

import {
  confusionMatrixUrl,
  getMlLabStatus,
  predictCondition,
  predictGap,
  type ConditionPredictOut,
  type GapPredictOut,
  type MlLabStatus,
} from '../api/mlLab'

const NATURE_STYLE: Record<string, { label: string; color: string }> = {
  own: { label: '🟩 modello addestrato da noi', color: 'var(--ok)' },
  gen: { label: '🟪 AI generativa', color: '#b48ce8' },
}

const METRIC_LABELS: Record<string, string> = {
  val_accuracy: 'Accuracy validazione',
  test_accuracy: 'Accuracy test',
  subset_accuracy: 'Accuracy esatta',
  micro_f1: 'Micro-F1',
  macro_f1: 'Macro-F1',
  hamming_loss: 'Hamming loss',
}

// Categorie modificabili nel simulatore gap (sottoinsieme rappresentativo).
const SIM_CATEGORIES = [
  't-shirt', 'camicia', 'maglione', 'giacca', 'cappotto',
  'jeans', 'pantaloni', 'gonna', 'vestito', 'scarpe',
] as const

function fmtMetric(v: unknown): string {
  if (typeof v === 'number') return v.toFixed(3)
  return String(v ?? '—')
}

function ProbBar({ label, value, highlight }: { label: string; value: number; highlight: boolean }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
        <span style={{ fontWeight: highlight ? 700 : 400 }}>{label}</span>
        <span className="muted">{Math.round(value * 100)}%</span>
      </div>
      <div style={{ height: 8, background: 'var(--panel-2)', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            width: `${Math.round(value * 100)}%`,
            height: '100%',
            background: highlight ? 'var(--ok)' : 'var(--border)',
            transition: 'width 300ms ease',
          }}
        />
      </div>
    </div>
  )
}

export default function MlLabPage() {
  const [status, setStatus] = useState<MlLabStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  // — prova condition —
  const [condFile, setCondFile] = useState<File | null>(null)
  const [condPreview, setCondPreview] = useState<string | null>(null)
  const [condResult, setCondResult] = useState<ConditionPredictOut | null>(null)
  const [condError, setCondError] = useState<string | null>(null)
  const [condBusy, setCondBusy] = useState(false)

  // — simulatore gap —
  const [counts, setCounts] = useState<Record<string, number>>({
    't-shirt': 5, 'camicia': 2, 'jeans': 2, 'scarpe': 2, 'giacca': 1,
  })
  const [nColors, setNColors] = useState(4)
  const [hasNeutral, setHasNeutral] = useState(true)
  const [gapResult, setGapResult] = useState<GapPredictOut | null>(null)
  const [gapBusy, setGapBusy] = useState(false)

  useEffect(() => {
    getMlLabStatus()
      .then(setStatus)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  useEffect(() => {
    if (!condFile) {
      setCondPreview(null)
      return
    }
    const url = URL.createObjectURL(condFile)
    setCondPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [condFile])

  async function onPredictCondition() {
    if (!condFile || condBusy) return
    setCondBusy(true)
    setCondError(null)
    setCondResult(null)
    try {
      setCondResult(await predictCondition(condFile))
    } catch (e: unknown) {
      setCondError(e instanceof Error ? e.message : String(e))
    } finally {
      setCondBusy(false)
    }
  }

  async function onPredictGap() {
    if (gapBusy) return
    setGapBusy(true)
    try {
      setGapResult(
        await predictGap({
          counts,
          n_colors: nColors,
          has_neutral: hasNeutral,
          ghost_ratio: 0.2,
        }),
      )
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setGapBusy(false)
    }
  }

  if (error) return <p className="error">Errore: {error}</p>
  if (status == null) return <p className="muted">Caricamento stato modelli…</p>

  const condAvailable = status.models.find((m) => m.key === 'condition-mlp')?.available ?? false

  return (
    <section>
      <PageHeader
        eyebrow="Approfondimento tecnico"
        title="ML Lab"
        description="Modelli, dati di addestramento e prove interattive per lo stato dei capi e i gap del guardaroba."
      />

      {/* ── 1 · Stato dei modelli ─────────────────────────────────── */}
      <div className="stats-grid lab-status-grid">
        {status.models.map((m) => {
          const nature = NATURE_STYLE[m.nature] ?? NATURE_STYLE.own
          return (
            <section
              key={m.key}
              className="panel"
              style={{ borderColor: m.available ? nature.color : 'var(--border)' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <h3 style={{ margin: 0, fontSize: 15 }}>{m.name}</h3>
                <span
                  style={{
                    fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
                    color: m.available ? 'var(--ok)' : 'var(--warn)',
                  }}
                >
                  {m.available ? '● addestrata' : '○ da addestrare'}
                </span>
              </div>
              <p className="muted" style={{ fontSize: 12, margin: '6px 0' }}>{m.task}</p>
              <p style={{ fontSize: 11, color: nature.color, margin: '0 0 6px' }}>{nature.label}</p>
              {m.architecture && (
                <p className="muted" style={{ fontSize: 11, margin: '0 0 8px' }}>
                  <code>{m.architecture}</code>
                </p>
              )}
              {m.metrics && (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
                  {Object.entries(m.metrics)
                    .filter(([, v]) => typeof v === 'number')
                    .map(([k, v]) => (
                      <div key={k}>
                        <div className="muted" style={{ fontSize: 10 }}>{METRIC_LABELS[k] ?? k.replaceAll('_', ' ')}</div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ok)' }}>{fmtMetric(v)}</div>
                      </div>
                    ))}
                </div>
              )}
            </section>
          )
        })}
      </div>

      {/* dataset */}
      <section className="panel" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 15 }}>📚 Dataset</h3>
        <div className="lab-dataset-grid">
          {status.datasets.map((d) => (
            <div
              key={d.key}
              style={{ padding: 10, border: '1px solid var(--border)', borderRadius: 8, background: 'var(--panel-2)' }}
            >
              <strong style={{ fontSize: 13 }}>{d.name}</strong>{' '}
              <span className="muted" style={{ fontSize: 11 }}>
                {d.available ? `· ${d.n_samples ?? '?'} campioni` : '· non generato'}
              </span>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{d.detail}</div>
            </div>
          ))}
        </div>
      </section>

      <div className="lab-demo-grid">
        {/* ── 2 · Prova la rete dello stato ────────────────────────── */}
        <section className="panel">
          <h3 style={{ marginTop: 0, fontSize: 15 }}>🛠️ Prova: stato dalla foto</h3>
          <p className="muted" style={{ fontSize: 12 }}>
            Carica la foto di un capo: la rete (Fashion-CLIP → MLP) predice lo stato
            di conservazione. Nessun capo viene salvato.
          </p>
          {!condAvailable && (
            <p style={{ color: 'var(--warn)', fontSize: 12 }}>
              ⚠️ Rete non addestrata: l'endpoint risponderà 503.
            </p>
          )}
          <label htmlFor="condition-photo">Foto del capo da analizzare</label>
          <input
            id="condition-photo"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => {
              setCondFile(e.target.files?.[0] ?? null)
              setCondResult(null)
            }}
          />
          {condPreview && (
            <img
              src={condPreview}
              alt="anteprima"
              style={{ width: '100%', maxHeight: 220, objectFit: 'contain', marginTop: 8, borderRadius: 8, background: 'var(--panel-2)' }}
            />
          )}
          <div style={{ marginTop: 10 }}>
            <button onClick={() => void onPredictCondition()} disabled={!condFile || condBusy}>
              {condBusy ? 'Predico…' : 'Predici stato'}
            </button>
          </div>
          {condError && <p className="error" style={{ fontSize: 12 }}>{condError}</p>}
          {condResult && (
            <div style={{ marginTop: 12 }}>
              <p style={{ margin: '0 0 8px' }}>
                Stato: <strong style={{ color: 'var(--ok)' }}>{condResult.condition}</strong>{' '}
                <span className="muted">({Math.round(condResult.confidence * 100)}%)</span>
              </p>
              {Object.entries(condResult.probabilities).map(([lab, p]) => (
                <ProbBar key={lab} label={lab} value={p} highlight={lab === condResult.condition} />
              ))}
            </div>
          )}
          {condAvailable && (
            <details style={{ marginTop: 12 }}>
              <summary className="muted" style={{ fontSize: 12, cursor: 'pointer' }}>
                Confusion matrix (ultimo training)
              </summary>
              <img
                src={confusionMatrixUrl()}
                alt="Confusion matrix della rete stato"
                style={{ width: '100%', marginTop: 8, borderRadius: 8, background: '#fff' }}
              />
            </details>
          )}
        </section>

        {/* ── 3 · Simulatore gap analysis ──────────────────────────── */}
        <section className="panel">
          <h3 style={{ marginTop: 0, fontSize: 15 }}>🧩 Prova: gap analysis (what-if)</h3>
          <p className="muted" style={{ fontSize: 12 }}>
            Componi un guardaroba immaginario: la rete multi-label predice i vuoti
            funzionali in tempo reale.
          </p>
          <div style={{ display: 'grid', gap: 6, gridTemplateColumns: '1fr 1fr' }}>
            {SIM_CATEGORIES.map((cat) => (
              <label key={cat} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, fontSize: 12, margin: 0 }}>
                <span>{cat}</span>
                <input
                  type="number"
                  min={0}
                  max={30}
                  value={counts[cat] ?? 0}
                  onChange={(e) =>
                    setCounts((prev) => ({ ...prev, [cat]: Math.max(0, Number(e.target.value) || 0) }))
                  }
                  style={{ width: 62 }}
                />
              </label>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, margin: 0 }}>
              colori distinti
              <input
                type="number"
                min={0}
                max={13}
                value={nColors}
                onChange={(e) => setNColors(Math.max(0, Number(e.target.value) || 0))}
                style={{ width: 56 }}
              />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, margin: 0 }}>
              <input
                type="checkbox"
                checked={hasNeutral}
                onChange={(e) => setHasNeutral(e.target.checked)}
                style={{ width: 'auto' }}
              />
              ha colori neutri
            </label>
            <button onClick={() => void onPredictGap()} disabled={gapBusy}>
              {gapBusy ? '…' : 'Analizza'}
            </button>
          </div>
          {gapResult && (
            <div style={{ marginTop: 12 }}>
              <p className="muted" style={{ fontSize: 11, margin: '0 0 8px' }}>
                fonte: {gapResult.source === 'neural-net' ? '🟩 rete neurale' : '🟨 regole (rete non addestrata)'}
              </p>
              {gapResult.balanced ? (
                <p style={{ color: 'var(--ok)', margin: 0 }}>✔ Guardaroba equilibrato: nessun vuoto.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: 6 }}>
                  {gapResult.gaps.map((code) => (
                    <li
                      key={code}
                      style={{ padding: 8, border: '1px solid var(--warn)', borderRadius: 8, background: 'var(--panel-2)', fontSize: 12 }}
                    >
                      {gapResult.labels[code] ?? code}
                      {gapResult.probabilities[code] != null && (
                        <span className="muted"> · {Math.round(gapResult.probabilities[code] * 100)}%</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
