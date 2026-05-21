import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import App from './App'
import HomePage from './pages/HomePage'
import AddItemPage from './pages/AddItemPage'
import ItemDetailPage from './pages/ItemDetailPage'
import './index.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'items/new', element: <AddItemPage /> },
      { path: 'items/:id', element: <ItemDetailPage /> },
    ],
  },
])

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error("Elemento #root non trovato in index.html")

createRoot(rootEl).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
