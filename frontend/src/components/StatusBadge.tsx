import type { Condition } from '../api/items'
import Icon from './Icon'

const LABELS: Record<Condition, string> = {
  buono: 'In buono stato',
  usurato: 'Da curare',
  danneggiato: 'Richiede attenzione',
}

export default function StatusBadge({ condition }: { condition: Condition | null }) {
  if (!condition) {
    return <span className="status-badge status-unknown">Stato da verificare</span>
  }
  return (
    <span className={`status-badge status-${condition}`}>
      <Icon name={condition === 'buono' ? 'check' : 'wrench'} size={13} />
      {LABELS[condition]}
    </span>
  )
}
