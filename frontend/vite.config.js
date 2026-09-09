import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /api to the Flask backend (default port 5001).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/docs/': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/flasgger_static/': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/api/openapi.json': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
})
