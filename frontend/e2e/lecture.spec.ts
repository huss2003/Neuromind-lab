import { expect, test } from '@playwright/test';
import { API, BAD, GOOD, accessToken, answer, finishVideo, openLecture, setCode, signIn } from './helpers';

// These tests mutate DEV data (attempts/submissions for learner1). Reset between runs:
//   delete from lecture_sessions/checkpoint_attempts/lab_submissions where learner_id = <learner1>  (see README).

test('A: successful lecture end to end', async ({ page }) => {
  await signIn(page, 'learner1');
  await openLecture(page);
  await finishVideo(page);
  await answer(page, 'print(\'Hi\')');
  await page.getByRole('button', { name: /Continue lesson|Try again/ }).click();
  await finishVideo(page);
  await answer(page, 'A block of code or text you can run on its own');
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page); // practical video -> exercise opens automatically
  await expect(page.getByRole('heading', { name: /Print your name/ })).toBeVisible();
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed', { exact: false }).first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Continue to exit check' }).click();
  await answer(page, '=');
  await page.getByRole('button', { name: 'Finish lecture' }).click();
  await expect(page.getByRole('heading', { name: /Lecture complete/ })).toBeVisible();
});

test('B: failed exercise then retry keeps both attempts', async ({ page }) => {
  await signIn(page, 'learner2');
  await openLecture(page);
  await finishVideo(page);
  await answer(page, 'print(\'Hi\')'); await page.getByRole('button', { name: /Continue lesson/ }).click();
  await finishVideo(page);
  await answer(page, 'A block of code or text you can run on its own'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs retry').first()).toBeVisible({ timeout: 60_000 });
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 60_000 });
  await page.getByText(/Attempt history/).click();
  await expect(page.getByText(/Attempt 1:/)).toBeVisible();
  await expect(page.getByText(/Attempt 2:/)).toBeVisible();
});

test('C: refresh restores progress and checkpoints cannot be bypassed', async ({ page, request }) => {
  await signIn(page, 'learner3');
  await openLecture(page);
  await finishVideo(page);
  await answer(page, 'print(\'Hi\')');
  await page.getByRole('button', { name: /Continue lesson/ }).click();
  await expect(page.getByRole('heading', { name: /Second concept/ })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: /Second concept/ })).toBeVisible(); // server state restored
  const headers = { Authorization: `Bearer ${await accessToken(page)}` };
  const courses = await (await request.get(`${API}/api/v1/courses`, { headers })).json();
  const course = await (await request.get(`${API}/api/v1/courses/${courses.courses[0].id}`, { headers })).json();
  const lectureId = course.lectures[0].id;
  const manifest = await (await request.get(`${API}/api/v1/lectures/${lectureId}`, { headers })).json();
  const session = await (await request.get(`${API}/api/v1/lectures/${lectureId}/session`, { headers })).json();
  const practical = manifest.segments.find((s: { order: number }) => s.order === 5);
  const r = await request.patch(`${API}/api/v1/lectures/${lectureId}/session`, {
    headers, data: { current_segment_id: practical.id, playback_position_seconds: 0, state_version: session.state_version } });
  expect(r.status()).toBe(400); // MCQ 2 not completed: server refuses the skip
  const done = await request.post(`${API}/api/v1/lectures/${lectureId}/complete`, { headers, data: {} });
  expect(done.status()).toBe(400);
});

test('D: learner cannot use teacher pages or API, or read another learner\'s submission', async ({ page, request }) => {
  await signIn(page, 'learner2');
  await page.goto('/teacher');
  await expect(page.getByText(/don't have access/)).toBeVisible();
  const headers = { Authorization: `Bearer ${await accessToken(page)}` };
  expect((await request.get(`${API}/api/v1/teacher/learners`, { headers })).status()).toBe(403);
  expect((await request.get(`${API}/api/v1/submissions/00000000-0000-4000-8000-0000000000ff`, { headers })).status()).toBe(404);
});

test('E: grader outage is shown as infrastructure error, not a learner failure', async ({ page }) => {
  // Run this one with the grader stopped (pnpm e2e:grader-down). Skipped unless E2E_GRADER_DOWN=1.
  test.skip(process.env.E2E_GRADER_DOWN !== '1', 'requires the grader to be stopped');
  await signIn(page, 'learner2');
  await openLecture(page);
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await page.locator('textarea.simple-editor').fill(GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText(/problem with the grading system, not your code/)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('Passed')).toHaveCount(0);
});
