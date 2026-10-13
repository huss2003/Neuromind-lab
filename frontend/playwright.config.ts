import { defineConfig } from '@playwright/test';

// E2E expects the full stack running (scripts/dev.sh) against a DEV Supabase project with seeded users
// (scripts/create_dev_users.py) and Docker available for the grader. See README.
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  workers: 1,
  use: { baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173', trace: 'retain-on-failure',
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {} },
});
