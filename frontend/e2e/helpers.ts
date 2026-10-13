import { expect, type Page } from '@playwright/test';

export const PASSWORD = process.env.DEV_USER_PASSWORD ?? 'NeuroMind-dev-2026!';

export async function signIn(page: Page, who: 'learner1' | 'learner2' | 'learner3' | 'teacher') {
  await page.goto('/sign-in');
  await page.getByLabel('Email').fill(`${who}@neuromind.test`);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}

export async function openLecture(page: Page) {
  await page.getByRole('link', { name: /(Start|Resume|Review) lecture/ }).first().click();
  await expect(page.getByRole('heading', { name: /Lecture 9/ })).toBeVisible();
}

/** The placeholder videos are 5 seconds; skip waiting by using the explicit manual-continue control. */
export async function finishVideo(page: Page) {
  await page.getByRole('button', { name: /finished this video/ }).click();
}

export async function answer(page: Page, optionText: string | RegExp) {
  await page.getByLabel(optionText).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
}

export async function setCode(page: Page, code: string) {
  await page.getByRole('button', { name: 'Use simple text editor' }).click(); // deterministic input (Monaco is canvas-like)
  await page.locator('textarea.simple-editor').fill(code);
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
