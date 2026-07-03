import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The `base` is prefixed onto every asset URL in the production build.
// GitHub Pages serves this repo under /App-pulse-based-on-App-User-reviews-/,
// so we need that prefix to match. In dev, Vite ignores it.
export default defineConfig({
  base: process.env.VITE_BASE || '/App-pulse-based-on-App-User-reviews-/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5050',
    },
  },
})
