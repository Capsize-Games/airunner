import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8188',
        changeOrigin: true,
        secure: false,
        proxyTimeout: 60_000,
        timeout: 60_000,
      },
    },
  },
})
