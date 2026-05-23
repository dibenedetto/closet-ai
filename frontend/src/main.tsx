import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import App from './App'
import HomePage from './pages/HomePage'
import AddItemPage from './pages/AddItemPage'
import ItemDetailPage from './pages/ItemDetailPage'
import DashboardPage from './pages/DashboardPage'
import TodayPage from './pages/TodayPage'
import MirrorPage from './pages/MirrorPage'
import './index.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'items/new', element: <AddItemPage /> },
      { path: 'items/:id', element: <ItemDetailPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'today', element: <TodayPage /> },
    ],
  },
  // La pagina specchio gira fullscreen, senza topbar/nav.
  { path: '/mirror', element: <MirrorPage /> },
])

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error("Elemento #root non trovato in index.html")

createRoot(rootEl).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
