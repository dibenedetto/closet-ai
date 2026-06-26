import { useCallback, useEffect, useState } from 'react'

import type { Condition, Item } from '../api/items'
import { getEnrichedTutorial } from '../api/ai'
import {
  deleteAction,
  diagnoseItem,
  getRepairTutorial,
  listActions,
  listSupportedDefects,
  registerAction,
  setItemCondition,
  type ActionType,
  type DiagnoseResponse,
  type ItemAction,
  type RepairTutorial,
} from '../api/circular'

const CONDITIONS: Condition[] = ['nuovo', 'buono', 'usurato', 'danneggiato']

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('it-IT')
  } catch {
    return iso
  }
}

function TutorialModal({
  tutorial,
  onEnrich,
  enriching,
  onClose,
}: {
  tutorial: RepairTutorial
  onEnrich: () => void
  enriching: boolean
  onClose: () => void
}) {
  const isLlm = tutorial.source === 'llm'
  return (
    <div className="tutorial-modal-backdrop" onClick={onClose}>
      <div className="tutorial-modal" onClick={(e) => e.stopPropagation()}>
        <h3>
          {tutorial.title}
          {isLlm && <span className="ai-label" style={{ marginLeft: 8 }}>✨ AI</span>}
        </h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Difficoltà: <b>{tutorial.difficulty}</b> ·
          tempo stimato: <b>{tutorial.time_minutes} min</b>
        </p>

        <h4>Materiali</h4>
        <ul>
          {tutorial.materials.map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ul>

        <h4>Procedura</h4>
        <ol>
          {tutorial.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>

        <p className="muted" style={{ fontSize: 11 }}>
          Sorgente: {tutorial.source}
        </p>

        <div style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          {tutorial.llm_enrichment_available && !isLlm && (
            <button onClick={onEnrich} disabled={enriching}>
              {enriching ? 'Arricchisco con AI…' : '✨ Arricchisci con AI'}
            </button>
          )}
          <button className="ghost" onClick={onClose} style={{ marginLeft: 'auto' }}>
            Chiudi
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CircularSection({
  item,
  onItemRefresh,
}: {
  item: Item
  onItemRefresh: () => void
}) {
  const [diagnosis, setDiagnosis] = useState<DiagnoseResponse | null>(null)
  const [actions, setActions] = useState<ItemAction[]>([])
  const [defects, setDefects] = useState<string[]>([])
  const [selectedDefect, setSelectedDefect] = useState<string>('')
  const [tutorial, setTutorial] = useState<RepairTutorial | null>(null)
  const [enriching, setEnriching] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const [d, a, def] = await Promise.all([
        diagnoseItem(item.id),
        listActions(item.id),
        listSupportedDefects(),
      ])
      setDiagnosis(d)
      setActions(a)
      setDefects(def)
      if (!selectedDefect && def.length) setSelectedDefect(def[0])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }, [item.id, selectedDefect])

  useEffect(() => {
    void refresh()
    // refresh dipende dal solo item.id; le re-render esterne non rilanciano la diagnosi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id])

  async function onChangeCondition(c: Condition) {
    setBusy(true)
    try {
      const updated = await setItemCondition(item.id, c)
      setDiagnosis(updated)
      onItemRefresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onExecute(action_type: ActionType, co2: number) {
    if (item.retired_at && action_type !== 'riparazione') {
      if (!confirm('Il capo è già ritirato. Registrare comunque una nuova azione?')) {
        return
      }
    }
    if (!confirm(
        `Registrare "${action_type}" su questo capo? Risparmio CO₂ stimato: ${co2} kg.`,
    )) {
      return
    }
    setBusy(true)
    try {
      const created = await registerAction(item.id, { action_type })
      setActions((prev) => [created, ...prev])
      onItemRefresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onRemoveAction(a: ItemAction) {
    if (!confirm('Eliminare questa azione?')) return
    setBusy(true)
    try {
      await deleteAction(a.id)
      setActions((prev) => prev.filter((x) => x.id !== a.id))
      onItemRefresh()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onOpenTutorial() {
    if (!selectedDefect) return
    setBusy(true)
    try {
      setTutorial(await getRepairTutorial(selectedDefect, item.category ?? undefined))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onEnrichTutorial() {
    if (!tutorial || enriching) return
    setEnriching(true)
    try {
      const enriched = await getEnrichedTutorial(tutorial.defect, {
        category: item.category ?? undefined,
        color: item.color ?? undefined,
        condition: item.condition ?? undefined,
      })
      setTutorial(enriched)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setEnriching(false)
    }
  }

  return (
    <div className="circular-card">
      <h3>Azioni circolari</h3>

      {error && <p className="error">{error}</p>}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, flexWrap: 'wrap' }}>
        <label htmlFor="cond" className="muted" style={{ margin: 0 }}>
          Condizione
        </label>
        <select
          id="cond"
          value={diagnosis?.condition ?? item.condition ?? ''}
          onChange={(e) => void onChangeCondition(e.target.value as Condition)}
          disabled={busy}
          style={{
            background: 'var(--panel-2)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '6px 10px',
          }}
        >
          {CONDITIONS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        {diagnosis && (
          <span className="muted" style={{ fontSize: 12 }}>
            {diagnosis.rationale}
          </span>
        )}
      </div>

      {diagnosis?.tutorial && (
        <div className="ai-card" style={{ marginBottom: 12 }}>
          <span className="ai-label">✨ AI · diagnosi dalla foto</span>
          {diagnosis.defect && (
            <p className="muted" style={{ fontSize: 12, margin: '6px 0 0' }}>
              Difetto rilevato: {diagnosis.defect}
            </p>
          )}
          <p className="ai-text">{diagnosis.tutorial}</p>
        </div>
      )}

      {item.retired_at && (
        <p className="muted" style={{ fontSize: 12 }}>
          ⓘ Capo ritirato il {fmtDate(item.retired_at)}. Le azioni nuove sono opzionali.
        </p>
      )}

      {diagnosis && diagnosis.suggestions.length > 0 && (
        <>
          <h3 style={{ marginTop: 16 }}>Suggerimenti</h3>
          {diagnosis.suggestions.map((s) => (
            <div className="suggestion-row" key={s.action_type}>
              <div className="info">
                <strong>{s.action_type}</strong>
                <span className="muted" style={{ fontSize: 12 }}>{s.rationale}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="co2">−{s.co2_saved_kg} kg CO₂</span>
                <button
                  onClick={() => void onExecute(s.action_type, s.co2_saved_kg)}
                  disabled={busy}
                >
                  Esegui
                </button>
              </div>
            </div>
          ))}
        </>
      )}

      <h3 style={{ marginTop: 16 }}>Storico azioni ({actions.length})</h3>
      {actions.length === 0 ? (
        <p className="muted" style={{ margin: 0 }}>Nessuna azione registrata.</p>
      ) : (
        <ul style={{ paddingLeft: 0, listStyle: 'none', margin: 0 }}>
          {actions.map((a) => (
            <li
              key={a.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <span>
                <b style={{ textTransform: 'capitalize' }}>{a.action_type}</b>
                <span className="muted" style={{ marginLeft: 6, fontSize: 12 }}>
                  · {fmtDate(a.created_at)}
                  {a.notes && ` · ${a.notes}`}
                </span>
              </span>
              <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="co2">−{a.co2_saved_kg} kg</span>
                <button
                  className="del-event"
                  onClick={() => void onRemoveAction(a)}
                  disabled={busy}
                >
                  rimuovi
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <h3 style={{ marginTop: 16 }}>Tutorial di riparazione</h3>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <select
          value={selectedDefect}
          onChange={(e) => setSelectedDefect(e.target.value)}
          disabled={busy || defects.length === 0}
          style={{
            background: 'var(--panel-2)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '6px 10px',
          }}
        >
          {defects.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <button className="ghost" onClick={() => void onOpenTutorial()} disabled={busy}>
          Mostra tutorial
        </button>
      </div>

      {tutorial && (
        <TutorialModal
          tutorial={tutorial}
          onEnrich={() => void onEnrichTutorial()}
          enriching={enriching}
          onClose={() => setTutorial(null)}
        />
      )}
    </div>
  )
}
