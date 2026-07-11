import { Link } from 'react-router-dom'

import Icon, { type IconName } from './Icon'

const STEPS: Array<{ number: string; label: string; helper: string; to: string; icon: IconName }> = [
  { number: '01', label: 'Aggiungi', helper: 'Fotografa il capo', to: '/items/new', icon: 'camera' },
  { number: '02', label: 'Indossa', helper: 'Registra gli utilizzi', to: '/#wardrobe', icon: 'check' },
  { number: '03', label: 'Combina', helper: 'Crea un outfit', to: '/today', icon: 'sparkles' },
  { number: '04', label: 'Cura', helper: 'Controlla lo stato', to: '/dashboard#condition', icon: 'wrench' },
  { number: '05', label: 'Valuta', helper: 'Scopri i gap', to: '/dashboard#gaps', icon: 'gap' },
  { number: '06', label: 'Rigenera', helper: 'Dai seconda vita', to: '/dashboard#circular', icon: 'recycle' },
]

export default function LifecycleRail() {
  return (
    <section className="lifecycle" aria-labelledby="lifecycle-title">
      <div className="lifecycle-heading">
        <div>
          <div className="eyebrow">Il ciclo del tuo guardaroba</div>
          <h2 id="lifecycle-title">Ogni capo può fare più strada.</h2>
        </div>
        <p>Sei piccoli gesti trasformano ciò che possiedi in valore, stile e impatto misurabile.</p>
      </div>
      <ol className="lifecycle-steps">
        {STEPS.map((step) => (
          <li key={step.number}>
            <Link to={step.to}>
              <span className="lifecycle-number">{step.number}</span>
              <span className="lifecycle-icon"><Icon name={step.icon} size={19} /></span>
              <span className="lifecycle-label">{step.label}</span>
              <span className="lifecycle-helper">{step.helper}</span>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  )
}
