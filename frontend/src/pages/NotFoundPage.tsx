import { Link, useNavigate } from 'react-router-dom'

import Icon from '../components/Icon'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <section className="not-found-page">
      <div className="not-found-code">404</div>
      <div className="eyebrow">Questa gruccia è vuota</div>
      <h1>La pagina non è nel guardaroba.</h1>
      <p>Il link potrebbe essere cambiato oppure il contenuto non è più disponibile.</p>
      <div className="button-row">
        <Link to="/" className="button button-primary"><Icon name="grid" size={18} /> Torna al guardaroba</Link>
        <button type="button" className="button button-secondary" onClick={() => navigate(-1)}>
          <Icon name="arrow-left" size={18} /> Indietro
        </button>
      </div>
    </section>
  )
}
