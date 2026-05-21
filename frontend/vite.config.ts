import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev tutte le richieste a /api vengono proxy-ate al backend FastAPI.
// In produzione le API sono raggiunte tramite VITE_API_BASE_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
