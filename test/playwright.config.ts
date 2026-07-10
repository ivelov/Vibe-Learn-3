import { defineConfig } from '@playwright/test';

// BASE_URL is injected by docker-compose.test.yml (http://app:8000) so the
// Playwright container can reach the app service over the compose network.
// Falls back to localhost for running the suite directly against a local app.
const baseURL = process.env.BASE_URL || 'http://localhost:8000';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL,
    headless: true,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});
