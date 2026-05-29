import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Relative base so the build works both on a GitHub Pages sub-path
  // (rakeshtycoon.github.io/claude-code-mate/) and when opened as a file.
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
})
