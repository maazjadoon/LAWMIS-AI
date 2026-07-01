import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Base path for GitHub Pages: https://maazjadoon.github.io/LAWMIS-AI/
  base: process.env.NODE_ENV === 'production' ? '/LAWMIS-AI/' : '/',
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
})
