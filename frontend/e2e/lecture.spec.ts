import { expect, test } from '@playwright/test';
import { BAD, GOOD, answer, apiStatus, setCode, signIn, toLab } from './helpers';

// REAL STACK (real Supabase, API, grader worker). These tests mutate data for the synthetic learners; they are meant for a
// DEV project. Each learner can complete the journey once; reset their rows (see README) before running again.
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
  await expect(page.getByText('Grading your submission').or(page.getByText('Your submission is queued')).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('How to fix it')).toBeVisible({ timeout: 90_000 }); // the worker polls every few seconds when idle
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 90_000 });
  await expect(page.getByText(/Best score 100%/)).toBeVisible();
  await page.getByText(/Attempt history \(/).click();
  await expect(page.getByRole('cell', { name: '1', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '2', exact: true })).toBeVisible();
});

test('C: a learner cannot use teacher pages or the teacher API, or read another learner\'s submission', async ({ page }) => {
  await signIn(page, 'learner2');
  await page.goto('/teacher');
  await expect(page.getByText(/don't have access/)).toBeVisible();
  expect(await apiStatus(page, '/api/v1/teacher/learners')).toBe(403);
  expect(await apiStatus(page, '/api/v1/submissions/00000000-0000-4000-8000-0000000000ff')).toBe(404);
});
