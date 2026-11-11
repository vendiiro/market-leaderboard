import { defineConfig } from '@playwright/test'

// Browser tests run against the dev server with the committed demo fixtures (no network, no live data).
// They use the installed Chrome so no browser download is needed.
export default defineConfig({
  testDir: 'e2e',
  outputDir: 'test-results',
  reporter: 'line',
  use: { baseURL: 'http://localhost:5199', channel: 'chrome', trace: 'off' },
  webServer: {
    command: 'npm run dev -- --port 5199 --strictPort',
    url: 'http://localhost:5199',
    env: { VITE_FIXTURES: '1' },
    reuseExistingServer: true,
  },
})
