import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

import { watchOptions } from './vite.watch.ts'

// The browser only calls its own origin under /api; the dev server forwards those calls to the
// backend, so no cross-origin request (and no CORS on the backend) is needed. In compose the target
// is the backend service; locally it is the backend on port 8000.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: watchOptions(process.env),
    proxy: {
      '/api': { target: apiProxyTarget, changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    // MUI components render slowly in jsdom; keep slow machines from failing on the 5s default.
    testTimeout: 15000,
  },
})
