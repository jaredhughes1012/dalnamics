import { defineConfig, devices } from '@playwright/test'
import { API_URL, REPO_ROOT, STUDIO_URL } from './tests/env'

/**
 * End-to-end tests run against the real stack: postgres, the api (with
 * DEBUG=true and the e2e dev user), devicemgr, and the mosquitto broker from
 * docker-compose, and the studio Vite dev server. Already-running servers are reused outside CI.
 *
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: STUDIO_URL,
    trace: 'on-first-retry',
  },

  projects: [
    // Signs in the e2e dev user once and saves the session to AUTH_FILE.
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },
  ],

  webServer: [
    {
      command: 'docker compose up --build postgres api devicemgr mosquitto',
      cwd: REPO_ROOT,
      url: `${API_URL}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
      stdout: 'ignore',
    },
    {
      command: 'pnpm dev --port 5173 --strictPort',
      cwd: `${REPO_ROOT}/studio`,
      url: STUDIO_URL,
      reuseExistingServer: !process.env.CI,
    },
  ],
})

