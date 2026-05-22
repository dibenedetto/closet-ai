import { NavLink, Outlet } from 'react-router-dom'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <h1>ClosetAI</h1>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Guardaroba
          </NavLink>
          <NavLink to="/today" className={({ isActive }) => (isActive ? 'active' : '')}>
            Cosa metto oggi?
          </NavLink>
          <NavLink to="/items/new" className={({ isActive }) => (isActive ? 'active' : '')}>
            Aggiungi capo
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'active' : '')}>
            Dashboard
          </NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
