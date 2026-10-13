import { expect, test } from '@playwright/test';
import { GOOD, signIn, toLab } from './helpers';

// Verifies the browser practice runtime for real: Monaco editor and Pyodide (loaded from the CDN in a Web Worker).
// Uses a synthetic load-test learner (E2E_PRACTICE_USER, default loadtest40) so the three journey learners stay untouched.
const USER = process.env.E2E_PRACTICE_USER ?? 'loadtest40';

test('Run practice executes learner code in Pyodide and shows its output; Monaco is the default editor', async ({ page }) => {
  await signIn(page, USER);
  await toLab(page);
  await expect(page.locator('.monaco-editor').first()).toBeVisible({ timeout: 60_000 }); // Monaco (CDN) loaded, not the plain fallback
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await page.locator('textarea.simple-editor').fill(GOOD);
  await page.getByRole('button', { name: 'Run practice' }).click();
  await expect(page.getByText('Aarav').first()).toBeVisible({ timeout: 120_000 }); // first run downloads the runtime
  await page.locator('textarea.simple-editor').fill('while True:\n    pass\n');
  await page.getByRole('button', { name: 'Run practice' }).click();
  await expect(page.getByText(/time limit|too long|timed out/i).first()).toBeVisible({ timeout: 60_000 }); // worker is terminated, page stays usable
  await expect(page.getByRole('button', { name: 'Run practice' })).toBeEnabled({ timeout: 30_000 });
});
