import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config — Sprint 6.5.
 *
 * Estrategia para Sprint 6.5: testes rodam contra o `next start` local
 * (build de producao) e mockam backend via `page.route(...)`. NAO sobe
 * agents-server nem api/ — isso eh territorio de smoke test em
 * Sprint 6.6.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 5_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
