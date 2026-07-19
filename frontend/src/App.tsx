import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'

import BrandWordmark from './components/BrandWordmark'
import HeroBrandIntro from './components/HeroBrandIntro'
import Icon, { type IconName } from './components/Icon'
import Logo from './components/Logo'

const PRIMARY_NAV: Array<{ to: string; icon: IconName; label: string; helper: string }> = [
  { to: '/', icon: 'grid', label: 'Guardaroba', helper: 'I tuoi capi' },
  { to: '/today', icon: 'sparkles', label: 'Cosa metto?', helper: 'Outfit per oggi' },
  { to: '/dashboard', icon: 'leaf', label: 'Impatto', helper: 'Stato, gap e CO₂' },
]

const PAGE_TITLES: Record<string, string> = {
  '/': 'Guardaroba',
  '/items/new': 'Aggiungi un capo',
  '/today': 'Cosa metto oggi?',
  '/dashboard': 'Impatto',
  '/lab': 'ML Lab',
}

function navClass({ isActive }: { isActive: boolean }) {
  return isActive ? 'nav-link active' : 'nav-link'
}

export default function App() {
  const location = useLocation()
  const mainRef = useRef<HTMLElement | null>(null)
  // App resta montata durante la navigazione React Router: in questo modo
  // l'intro parte al caricamento diretto della home, non a ogni ritorno interno.
  const [showHeroIntro, setShowHeroIntro] = useState(location.pathname === '/')

  useEffect(() => {
    const section = location.pathname.startsWith('/items/')
      ? location.pathname === '/items/new' ? 'Aggiungi un capo' : location.pathname.endsWith('/edit') ? 'Modifica capo' : 'Dettaglio capo'
      : PAGE_TITLES[location.pathname] ?? 'ClosetAI'
    document.title = `${section} · ClosetAI`
    mainRef.current?.focus()
  }, [location.pathname])

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Vai al contenuto</a>
      {showHeroIntro && <HeroBrandIntro onComplete={() => setShowHeroIntro(false)} />}

      <aside className="sidebar" aria-label="Navigazione principale">
        <Link to="/" className="brand" aria-label="ClosetAI — guardaroba">
          <Logo size={42} />
          <BrandWordmark />
        </Link>

        <nav className="sidebar-nav">
          <span className="nav-section-label">Il tuo spazio</span>
          {PRIMARY_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => navClass({ isActive: isActive || (item.to === '/' && location.pathname.startsWith('/items')) })}
            >
              <span className="nav-icon"><Icon name={item.icon} size={20} /></span>
              <span>
                <strong>{item.label}</strong>
                <small>{item.helper}</small>
              </span>
              <Icon name="chevron-right" size={16} className="nav-chevron" />
            </NavLink>
          ))}
        </nav>

        <Link to="/items/new" className="nav-link sidebar-add">
          <span className="nav-icon"><Icon name="plus" size={20} /></span>
          <span><strong>Aggiungi un capo</strong><small>Foto o inserimento</small></span>
          <Icon name="chevron-right" size={16} className="nav-chevron" />
        </Link>

        <nav className="sidebar-nav sidebar-nav-secondary" aria-label="Approfondimenti">
          <span className="nav-section-label">Approfondimenti</span>
          <NavLink to="/lab" className={navClass}>
            <span className="nav-icon"><Icon name="flask" size={19} /></span>
            <span><strong>ML Lab</strong><small>Come funziona l’AI</small></span>
            <Icon name="chevron-right" size={16} className="nav-chevron" />
          </NavLink>
        </nav>

        <div className="sidebar-footnote">
          <span className="sidebar-footnote-icon"><Icon name="leaf" size={17} /></span>
          <p><strong>Il capo più sostenibile</strong><br />è quello che hai già.</p>
        </div>
      </aside>

      <header className="mobile-header">
        <Link to="/" className="brand" aria-label="ClosetAI — guardaroba">
          <Logo size={34} />
          <BrandWordmark />
        </Link>
        <Link to="/items/new" className="icon-button" aria-label="Aggiungi un capo">
          <Icon name="plus" size={20} />
        </Link>
      </header>

      <main id="main-content" className="app" ref={mainRef} tabIndex={-1}>
        <Outlet />
      </main>

      <nav className="mobile-nav" aria-label="Navigazione mobile">
        {PRIMARY_NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => isActive || (item.to === '/' && location.pathname.startsWith('/items')) ? 'active' : ''}
          >
            <Icon name={item.icon} size={21} />
            <span>{item.label}</span>
          </NavLink>
        ))}
        <NavLink to="/lab">
          <Icon name="flask" size={21} />
          <span>Lab</span>
        </NavLink>
      </nav>
    </div>
  )
}
