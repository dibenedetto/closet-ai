import { NavLink, Outlet, Link } from 'react-router-dom'

import Logo from './components/Logo'

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand" title="ClosetAI — home">
          <Logo size={34} />
          <span className="brand-name">
            Closet<span className="brand-ai">AI</span>
          </span>
        </Link>
        <nav>
          <NavLink to="/" end className={navClass}>
            Guardaroba
          </NavLink>
          <NavLink to="/today" className={navClass}>
            Cosa metto oggi?
          </NavLink>
          <NavLink to="/dashboard" className={navClass}>
            Impatto
          </NavLink>
          <NavLink to="/lab" className={navClass}>
            ML Lab
          </NavLink>
        </nav>
        <Link to="/items/new" className="add-cta" title="Fotografa un nuovo capo">
          📷 Aggiungi capo
        </Link>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
