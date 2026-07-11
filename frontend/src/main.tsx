import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import App from './App'
import HomePage from './pages/HomePage'
import AddItemPage from './pages/AddItemPage'
import EditItemPage from './pages/EditItemPage'
import ItemDetailPage from './pages/ItemDetailPage'
import DashboardPage from './pages/DashboardPage'
import TodayPage from './pages/TodayPage'
import MirrorPage from './pages/MirrorPage'
import MlLabPage from './pages/MlLabPage'
import NotFoundPage from './pages/NotFoundPage'
import RouteErrorPage from './pages/RouteErrorPage'
import '@fontsource-variable/inter/wght.css'
import './index.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'items/new', element: <AddItemPage /> },
      { path: 'items/:id', element: <ItemDetailPage /> },
      { path: 'items/:id/edit', element: <EditItemPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'today', element: <TodayPage /> },
      { path: 'lab', element: <MlLabPage /> },
      { path: '*', element: <NotFoundPage /> },
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
