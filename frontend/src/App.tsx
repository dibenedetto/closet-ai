import { useEffect, useState } from 'react'
import { NavLink, Outlet, Link, useLocation } from 'react-router-dom'

import Logo from './components/Logo'

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : '')

const NAV_ITEMS = [
  { to: '/', end: true, icon: '👕', label: 'Guardaroba' },
  { to: '/today', end: false, icon: '✨', label: 'Cosa metto oggi?' },
  { to: '/dashboard', end: false, icon: '🌱', label: 'Impatto' },
  { to: '/lab', end: false, icon: '🧪', label: 'ML Lab' },
]

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  // Chiudi il menu mobile a ogni cambio pagina.
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand" title="ClosetAI — home">
            <Logo size={32} />
            <span className="brand-name">
              Closet<span className="brand-ai">AI</span>
            </span>
          </Link>

          <nav className={`topbar-nav ${menuOpen ? 'open' : ''}`}>
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navClass}>
                <span className="nav-icon" aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
            <Link to="/items/new" className="add-cta add-cta-mobile">
              <span aria-hidden="true">📷</span> Aggiungi capo
            </Link>
          </nav>

          <div className="topbar-actions">
            <Link to="/items/new" className="add-cta">
              <span aria-hidden="true">📷</span> Aggiungi capo
            </Link>
            <button
              type="button"
              className="nav-toggle ghost"
              aria-label={menuOpen ? 'Chiudi menu' : 'Apri menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <span className={`burger ${menuOpen ? 'open' : ''}`} />
            </button>
          </div>
        </div>
      </header>
      <main className="app">
        <Outlet />
      </main>
    </div>
  )
}
