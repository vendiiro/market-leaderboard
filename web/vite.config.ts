import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  base: './', // relative paths so the build works from any folder
  plugins: [react()],
  test: { include: ['src/**/*.test.ts'] }, // e2e/ belongs to Playwright
})
