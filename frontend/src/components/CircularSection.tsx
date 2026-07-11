import { useCallback, useEffect, useMemo, useState } from 'react'

import { errorMessage } from '../api/client'
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
import Icon, { type IconName } from './Icon'

const CONDITIONS: Array<{ value: Condition; label: string }> = [
  { value: 'buono', label: 'In buono stato' },
  { value: 'usurato', label: 'Da curare' },
  { value: 'danneggiato', label: 'Danneggiato' },
]

const ACTIONS: Record<ActionType, { label: string; icon: IconName }> = {
  riparazione: { label: 'Ripara', icon: 'wrench' },
  swap: { label: 'Scambia', icon: 'refresh' },
  vendita: { label: 'Vendi', icon: 'tag' },
  donazione: { label: 'Dona', icon: 'heart' },
  riciclo: { label: 'Ricicla', icon: 'recycle' },
}

function fmtDate(iso: string): string {
  const value = new Date(iso)
  return Number.isNaN(value.getTime()) ? iso : value.toLocaleString('it-IT')
}

export default function CircularSection({ item, onItemRefresh }: { item: Item; onItemRefresh: () => void }) {
  const [diagnosis, setDiagnosis] = useState<DiagnoseResponse | null>(null)
  const [actions, setActions] = useState<ItemAction[] | null>(null)
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setBusy(true)
    setError(null)
    const [diagnosisResult, actionsResult] = await Promise.allSettled([diagnoseItem(item.id), listActions(item.id)])
    if (diagnosisResult.status === 'fulfilled') setDiagnosis(diagnosisResult.value)
    if (actionsResult.status === 'fulfilled') setActions(actionsResult.value)
    if (diagnosisResult.status === 'rejected' || actionsResult.status === 'rejected') {
      const reason = diagnosisResult.status === 'rejected' ? diagnosisResult.reason : actionsResult.status === 'rejected' ? actionsResult.reason : null
      setError(errorMessage(reason))
    }
    setBusy(false)
  }, [item.id])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const suggestions = useMemo(
    () => (diagnosis?.suggestions ?? []).filter((suggestion) => !item.retired_at || suggestion.action_type === 'riparazione'),
    [diagnosis, item.retired_at],
  )

  async function onChangeCondition(condition: Condition) {
    setBusy(true)
    setError(null)
    try {
      setDiagnosis(await setItemCondition(item.id, condition))
      setNotice('Stato del capo aggiornato.')
      onItemRefresh()
    } catch (reason: unknown) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  async function onExecute(actionType: ActionType, co2: number) {
    if (!confirm(`Registrare “${ACTIONS[actionType].label}”? Impatto stimato: ${co2} kg di CO₂eq evitata.`)) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await registerAction(item.id, { action_type: actionType, notes: notes.trim() || undefined })
      setActions((current) => [created, ...(current ?? [])])
      setNotes('')
      setNotice(`${ACTIONS[actionType].label} registrato: −${created.co2_saved_kg} kg di CO₂eq.`)
      onItemRefresh()
    } catch (reason: unknown) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  async function onRemoveAction(action: ItemAction) {
    if (!confirm(`Rimuovere l’azione “${ACTIONS[action.action_type].label}”?`)) return
    setBusy(true)
    try {
      await deleteAction(action.id)
      setActions((current) => (current ?? []).filter((value) => value.id !== action.id))
      setNotice('Azione rimossa e impatto ricalcolato.')
      onItemRefresh()
    } catch (reason: unknown) {
      setError(errorMessage(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="circular-card" aria-labelledby="circular-title">
      <div className="eyebrow">Cura e seconda vita</div>
      <h2 id="circular-title" style={{ marginTop: 5 }}>Qual è il prossimo gesto giusto?</h2>
      <p className="muted" style={{ fontSize: 11 }}>Lo stato del capo guida azioni che ne allungano la vita e rendono visibile l’impatto evitato.</p>

      {error && <div className="error" role="alert"><Icon name="circle-alert" size={17} /> {error}</div>}
      {notice && <div className="notice notice-success" role="status"><Icon name="check" size={17} /> {notice}</div>}

      <div className="form-grid" style={{ marginTop: 18 }}>
        <label className="field" htmlFor={`condition-${item.id}`}>
          Stato del capo
          <select
            id={`condition-${item.id}`}
            value={diagnosis?.condition ?? item.condition ?? 'buono'}
            onChange={(event) => void onChangeCondition(event.target.value as Condition)}
            disabled={busy}
          >
            {CONDITIONS.map((condition) => <option key={condition.value} value={condition.value}>{condition.label}</option>)}
          </select>
        </label>
        <label className="field" htmlFor={`action-notes-${item.id}`}>
          Nota per la prossima azione
          <input
            id={`action-notes-${item.id}`}
            type="text"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Es. zip sostituita, donato al mercatino…"
          />
        </label>
      </div>

      {diagnosis && (
        <div className="analysis-note">
          <Icon name="wand" size={18} />
          <p><strong>Diagnosi {diagnosis.source === 'clip-mlp' ? 'dalla rete neurale' : 'da regole esperte'}</strong>{diagnosis.rationale}</p>
        </div>
      )}

      {item.retired_at && <div className="notice" style={{ marginTop: 12 }}><Icon name="recycle" size={17} /> In seconda vita dal {fmtDate(item.retired_at)}. Le azioni di ritiro non vengono proposte di nuovo.</div>}

      <div className="section-heading" style={{ marginTop: 26 }}>
        <div><div className="eyebrow">Azioni suggerite</div><h3 style={{ margin: '5px 0 0' }}>Fai durare il capo più a lungo</h3></div>
      </div>
      {busy && !diagnosis ? (
        <p className="muted" role="status">Analizzo stato, età e utilizzi…</p>
      ) : suggestions.length === 0 ? (
        <p className="muted">Nessuna azione urgente: continua a usare e prenderti cura del capo.</p>
      ) : suggestions.map((suggestion) => (
        <div className="suggestion-row" key={suggestion.action_type}>
          <div className="info">
            <strong style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Icon name={ACTIONS[suggestion.action_type].icon} size={16} /> {ACTIONS[suggestion.action_type].label}
            </strong>
            <span className="muted" style={{ fontSize: 11 }}>{suggestion.rationale}</span>
          </div>
          <div className="button-row" style={{ alignItems: 'center' }}>
            <span className="co2">−{suggestion.co2_saved_kg} kg CO₂</span>
            <button type="button" className="button button-small" onClick={() => void onExecute(suggestion.action_type, suggestion.co2_saved_kg)} disabled={busy}>
              Registra
            </button>
          </div>
        </div>
      ))}

      <div className="section-heading" style={{ marginTop: 28 }}>
        <div><div className="eyebrow">Storico circolare</div><h3 style={{ margin: '5px 0 0' }}>{actions?.length ?? 0} azioni registrate</h3></div>
      </div>
      {actions == null ? (
        <p className="muted" role="status">Carico lo storico…</p>
      ) : actions.length === 0 ? (
        <p className="muted">La prima azione circolare apparirà qui.</p>
      ) : (
        <ul className="rank-list">
          {actions.map((action, index) => (
            <li key={action.id} style={{ gridTemplateColumns: '28px 1fr auto auto' }}>
              <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
              <span>
                <strong style={{ fontSize: 11 }}>{ACTIONS[action.action_type].label}</strong>
                <span className="muted" style={{ display: 'block', fontSize: 9 }}>{fmtDate(action.created_at)}{action.notes ? ` · ${action.notes}` : ''}</span>
              </span>
              <span className="co2">−{action.co2_saved_kg} kg</span>
              <button type="button" className="del-event" aria-label={`Rimuovi azione ${ACTIONS[action.action_type].label}`} onClick={() => void onRemoveAction(action)} disabled={busy}>Rimuovi</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
