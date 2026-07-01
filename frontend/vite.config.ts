import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Vercel: VITE_BASE_PATH is not set → defaults to '/'
  // GitHub Pages: VITE_BASE_PATH=/LAWMIS-AI/ is set in the Actions workflow
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
})
