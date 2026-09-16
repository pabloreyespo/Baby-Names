import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' },
    watch: process.env.VITE_POLL ? { usePolling: true } : undefined,
  },
})
