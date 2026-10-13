import { expect, type Page } from '@playwright/test';

export const PASSWORD = process.env.DEV_USER_PASSWORD ?? '';
if (!PASSWORD) throw new Error('Set DEV_USER_PASSWORD to the password used when the synthetic test users were created.');

export async function signIn(page: Page, who: 'learner1' | 'learner2' | 'learner3' | 'teacher') {
  await page.goto('/sign-in');
  await page.getByLabel('Email').fill(`${who}@neuromind.test`);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).not.toHaveURL(/sign-in/); // the sign-in page has its own h1, so wait for the redirect
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}

export async function openLecture(page: Page) {
  await page.getByRole('link', { name: /(Start|Resume|Review) lecture/ }).first().click();
  await expect(page.getByRole('heading', { name: /Lecture 9/ })).toBeVisible();
}

/** Orientation screen -> Start lecture. A learner who already started resumes without it. */
export async function startLecture(page: Page) {
  const start = page.getByRole('button', { name: 'Start lecture' });
  await start.click({ timeout: 10_000 }).catch(() => undefined); // not shown when the learner resumes mid-lecture
}

/** Calls the API from inside the page (same network path as the app), returning only the HTTP status. */
export async function apiStatus(page: Page, path: string): Promise<number> {
  const token = await accessToken(page);
  return page.evaluate(async ([url, t]) => (await fetch(url, { headers: { Authorization: `Bearer ${t}` } })).status, [`${API}${path}`, token]);
}

/** A written section ends with a Continue button. */
export const continueReading = (page: Page) => page.getByRole('button', { name: 'Continue', exact: true }).click();

export async function answer(page: Page, optionText: string | RegExp) {
  await page.getByLabel(optionText).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
}

export async function setCode(page: Page, code: string) {
  const area = page.locator('textarea.simple-editor');
  if (!(await area.isVisible())) await page.getByRole('button', { name: 'Use simple text editor' }).click(); // deterministic input (Monaco is canvas-like)
  await area.fill(code);
}

export const GOOD = "student_name = 'Aarav'\nprint(student_name)\n";
export const BAD = "student_name = 'Aarav'\nprint('hello')\n";

export async function accessToken(page: Page): Promise<string> {
  return page.evaluate(() => {
    for (const v of Object.values(localStorage)) {
      try { const t = JSON.parse(String(v)).access_token; if (t) return t as string; } catch { /* not JSON */ }
    }
    return '';
  });
}
export const API = process.env.E2E_API_URL ?? 'http://localhost:8000';
