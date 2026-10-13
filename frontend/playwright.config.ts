import { defineConfig } from '@playwright/test';

// E2E expects the full stack running (scripts/dev.sh) against a DEV Supabase project with seeded users
// (scripts/create_dev_users.py) and Docker available for the grader. See README.
export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  expect: { timeout: 20_000 }, // live runs cross the internet and a serverless API
  workers: 1,
  use: { navigationTimeout: 60_000, baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173', trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {} },
});
