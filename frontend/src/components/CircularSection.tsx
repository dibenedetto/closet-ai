import { useCallback, useEffect, useState } from 'react'

import type { Condition, Item } from '../api/items'
import {
  deleteAction,
  diagnoseItem,
  listActions,
  registerAction,
  setItemCondition,
  type ActionType,
  type DiagnoseResponse,
  type ItemAction,
} from '../api/circular'

const CONDITIONS: Condition[] = ['buono', 'usurato', 'danneggiato']

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('it-IT')
  } catch {
    return iso
  }
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
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const [d, a] = await Promise.all([diagnoseItem(item.id), listActions(item.id)])
      setDiagnosis(d)
      setActions(a)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }, [item.id])

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
    </div>
  )
}
