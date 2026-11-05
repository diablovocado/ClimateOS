import { defineConfig } from 'vite'

export default defineConfig({
  // Serve from repo root so all HTML files are accessible
  root: '.',

  server: {
    port: 5173,
    open: '/citizen.html',   // opens citizen home on startup
    strictPort: true,

    // Proxy all /api/* requests to FastAPI backend — no CORS needed
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },

  // Tell Vite which HTML files are entry points (multi-page app)
  build: {
    rollupOptions: {
      input: {
        index:             'index.html',
        citizen:           'citizen.html',
        'citizen-map':     'citizen-map.html',
        'citizen-report':  'citizen-report.html',
        'citizen-shelters':'citizen-shelters.html',
        'citizen-route':   'citizen-route.html',
        government:        'government.html',
        stitch:            'stitch_climateos_disaster_intelligence_platform/code.html',
      }
    }
  }
})
