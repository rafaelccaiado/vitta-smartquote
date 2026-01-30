import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/qa-proxy': {
        target: 'https://vitta-smartquote.vercel.app',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/qa-proxy/, ''),
        secure: false,
      },
    },
  },
})
