import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Frontend-backend separation: during development the Vue dev server proxies
// API calls to the FastAPI backend running on localhost:8000. For production,
// `npm run build` produces dist/ which the backend serves as static files.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/predict': 'http://localhost:8000',
      '/models': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
})
