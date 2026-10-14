import { defineConfig } from '@playwright/test';

// UI tests: the real built app in Chromium with the network mocked at the browser boundary (ui-tests/mockServer.ts).
// They verify rendering, layout at the required widths, keyboard use and the client state machine.
// They do NOT prove integration with Supabase, the API, Docker grading or Pyodide: use `pnpm e2e` for that.
export default defineConfig({
  testDir: './ui-tests',
  timeout: 60_000,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5174',
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_PATH ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } : {},
  },
  webServer: {
    command: 'pnpm build:mock && pnpm exec vite preview --host 127.0.0.1 --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
