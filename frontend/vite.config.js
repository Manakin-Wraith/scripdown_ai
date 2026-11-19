import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // recharts / pdf viewer are only reached via lazy routes, so Rollup splits them itself;
        // forcing them into named chunks pulled shared helpers in and made them eager.
        // Stable vendor chunks so app-code deploys don't invalidate cached libraries.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) return 'vendor-react'
          if (id.includes('@supabase')) return 'vendor-supabase'
          return undefined
        },
      },
    },
  },
})
