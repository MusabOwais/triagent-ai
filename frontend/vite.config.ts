import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In relay mode the browser calls /api and /samples on this dev server, which forwards them
// to the Relay Triage backend. Same origin, so the backend needs no CORS setup.
const backend = process.env.VITE_API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true, proxy: { '/api': backend, '/samples': backend } },
})
