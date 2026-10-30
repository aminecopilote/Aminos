import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      // En mode VITE_EKA_API=http, « /api » est relayé vers le serveur de `npm run api`.
      proxy: { '/api': `http://127.0.0.1:${env.EKA_API_PORT || 8787}` },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.js',
      css: false,
    },
  }
})
