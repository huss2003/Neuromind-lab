import { expect, test } from '@playwright/test';
import { API, BAD, GOOD, accessToken, answer, continueReading, openLecture, setCode, signIn, startLecture } from './helpers';

// REAL STACK (real Supabase, API, grader worker). These tests mutate data for the synthetic learners; they are meant for a
// DEV project. Each learner can complete the journey once; reset their rows (see README) before running again.
const CHECK_1 = 'python --version';
const CHECK_2 = 'Each cell can be run on its own, and all cells share the same variables while the kernel is running';

async function toLab(page: import('@playwright/test').Page) {
  await openLecture(page);
  await startLecture(page);
  await continueReading(page);                                  // intro
  await continueReading(page);                                  // Set up Python
  await answer(page, CHECK_1);
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await continueReading(page);                                  // Notebooks and cells
  await answer(page, CHECK_2);
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await continueReading(page);                                  // Variables and print()
  await expect(page.getByRole('heading', { name: /Print your name/ })).toBeVisible();
}

test('A: learner completes the lecture end to end against the real grader', async ({ page }) => {
  await signIn(page, 'learner1');
  await toLab(page);
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 90_000 });
  await page.getByRole('button', { name: 'Continue to exit check' }).click();
  await answer(page, '25');
  await page.getByRole('button', { name: 'Finish lecture' }).click();
  await expect(page.getByRole('heading', { name: /Lecture complete/ })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: /Lecture complete/ })).toBeVisible(); // completion is server state
});

test('B: a failed attempt gives guidance, a retry passes, and both attempts are kept', async ({ page }) => {
  await signIn(page, 'learner2');
  await toLab(page);
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText('How to fix it')).toBeVisible();
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/Best score 100%/)).toBeVisible();
  await page.getByText(/Attempt history \(/).click();
  await expect(page.getByRole('cell', { name: '1', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '2', exact: true })).toBeVisible();
});

test('C: a learner cannot use teacher pages or the teacher API, or read another learner\'s submission', async ({ page, request }) => {
  await signIn(page, 'learner2');
  await page.goto('/teacher');
  await expect(page.getByText(/don't have access/)).toBeVisible();
  const headers = { Authorization: `Bearer ${await accessToken(page)}` };
  expect((await request.get(`${API}/api/v1/teacher/learners`, { headers })).status()).toBe(403);
  expect((await request.get(`${API}/api/v1/submissions/00000000-0000-4000-8000-0000000000ff`, { headers })).status()).toBe(404);
});
