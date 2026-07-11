import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom'

import Icon from '../components/Icon'

export default function RouteErrorPage() {
  const error = useRouteError()
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error ? error.message : 'Errore inatteso'

  return (
    <section className="not-found-page" role="alert">
      <span className="state-icon"><Icon name="circle-alert" size={26} /></span>
      <div className="eyebrow">ClosetAI ha perso il filo</div>
      <h1>Questa vista non si è caricata.</h1>
      <p>{message}</p>
      <Link to="/" className="button button-primary"><Icon name="grid" size={18} /> Torna al guardaroba</Link>
    </section>
  )
}
