import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { IDS, installMocks, newState, signedIn, type MockOpts, type MockState } from './mockServer';

const SHOTS = process.env.SHOT_DIR;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const VIEWPORTS = [
  { name: '360', width: 360, height: 800 }, { name: '390', width: 390, height: 844 }, { name: '768', width: 768, height: 1024 },
  { name: '1366', width: 1366, height: 768 }, { name: '1440', width: 1440, height: 900 },
];

async function setup(page: Page, opts: MockOpts = {}, email?: string): Promise<MockState> {
  const state = newState(opts);
  await installMocks(page, state);
  await signedIn(page, email);
  return state;
}
const overflow = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
async function noOverflow(page: Page, where: string) { expect(await overflow(page), `horizontal overflow on ${where}`).toBeLessThanOrEqual(1); }
async function shot(page: Page, name: string) { if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true }); }
const finishVideo = (page: Page) => page.getByRole('button', { name: /finished this video/ }).click();
async function answer(page: Page, option: string) {
  await page.getByLabel(option, { exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
}
async function toLab(page: Page) {
  await page.goto(`/lectures/${IDS.lecture}`);
  await finishVideo(page);
  await answer(page, 'Option B'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await answer(page, 'Option A'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page); // practical video -> exercise opens automatically
  await expect(page.getByRole('heading', { name: /Print a variable/ })).toBeVisible();
}
async function typeCode(page: Page, code: string) {
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await page.locator('textarea.simple-editor').fill(code);
}
const GOOD = 'student_name = "Aarav"\nprint(student_name)\n';
const HALF = 'student_name = "Aarav"\nprint("hello")\n';

test.describe('responsive layout (360/390/768/1366/1440): no horizontal overflow on core screens', () => {
  for (const vp of VIEWPORTS) {
    test(`learner screens at ${vp.name}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await setup(page);
      const screens: [string, string, () => Promise<void>][] = [
        ['dashboard', '/', async () => { await expect(page.getByRole('heading', { level: 1 })).toContainText('Lecture 9'); }],
        ['course', `/courses/${IDS.course}`, async () => { await expect(page.getByText('Module 2: Python for AI (sample)')).toBeVisible(); }],
        ['progress', '/progress', async () => { await expect(page.getByRole('heading', { name: 'My progress' })).toBeVisible(); }],
        ['lecture-video', `/lectures/${IDS.lecture}`, async () => { await expect(page.getByRole('heading', { name: 'Introduction and first concept' })).toBeVisible(); }],
      ];
      for (const [name, path, ready] of screens) {
        await page.goto(path); await ready(); await noOverflow(page, `${name} @${vp.name}`); await shot(page, `${vp.name}-${name}`);
      }
      await toLab(page);
      await noOverflow(page, `lab @${vp.name}`); await shot(page, `${vp.name}-lab-code`);
      await typeCode(page, HALF);
      await page.getByRole('button', { name: 'Submit for grading' }).click();
      await expect(page.getByText('Needs retry').first()).toBeVisible({ timeout: 15_000 });
      await noOverflow(page, `lab result @${vp.name}`); await shot(page, `${vp.name}-lab-result`);
    });

    test(`sign-in and teacher screens at ${vp.name}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/sign-in'); await noOverflow(page, `sign-in @${vp.name}`); await shot(page, `${vp.name}-signin`);
      await setup(page, { role: 'teacher', name: 'Mr Teacher', email: 'teacher@neuromind.test' }, 'teacher@neuromind.test');
      await page.goto('/teacher'); await expect(page.getByRole('heading', { name: 'Teacher dashboard' })).toBeVisible();
      await noOverflow(page, `teacher @${vp.name}`); await shot(page, `${vp.name}-teacher`);
      await page.goto(`/teacher/learners/${IDS.learner}`); await expect(page.getByRole('heading', { name: 'Asha Rao' })).toBeVisible();
      await noOverflow(page, `learner detail @${vp.name}`); await shot(page, `${vp.name}-teacher-learner`);
      await page.goto('/teacher/submissions/s-1'); await expect(page.getByText('Evidence record')).toBeVisible();
      await noOverflow(page, `submission detail @${vp.name}`);
    });
  }
});

test('A: learner completes the whole lecture through the UI', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await setup(page);
  await page.goto('/');
  await page.getByRole('link', { name: 'Start lecture' }).first().click();
  await expect(page.getByRole('heading', { name: /Lecture 9/ })).toBeVisible();
  await finishVideo(page);
  await expect(page.getByText('the video is paused')).toBeVisible();
  await answer(page, 'Option C'); // wrong on purpose
  await expect(page.getByText('Not quite')).toBeVisible();
  await expect(page.getByText('Not this one — see the lesson.')).toBeVisible();
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await answer(page, 'Option A'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await expect(page.getByRole('heading', { name: /Print a variable/ })).toBeVisible(); // exercise opened automatically
  await typeCode(page, GOOD);
  await expect(page.getByText('All changes saved')).toBeVisible({ timeout: 8000 });
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Best score 100%')).toBeVisible();
  await page.getByRole('button', { name: 'Continue to exit check' }).click();
  await answer(page, 'Option A');
  await page.getByRole('button', { name: 'Finish lecture' }).click();
  await expect(page.getByRole('heading', { name: /Lecture complete/ })).toBeVisible();
  expect(state.status).toBe('completed');
  expect(state.calls.some((c) => c.endsWith('/complete'))).toBe(true);
});

test('B: fail, use a hint, retry — both attempts shown, best score preserved', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await toLab(page);
  await typeCode(page, HALF);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs retry').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Print the variable with print(student_name).')).toBeVisible(); // remediation for the failed hidden check
  await expect(page.getByText('Hidden check 1')).toBeVisible();
  await expect(page.getByText('Best score 50%')).toBeVisible();
  await page.getByRole('button', { name: /Show hint 1 of 3/ }).click();
  await expect(page.getByText('Create a variable called student_name.')).toBeVisible();
  await page.locator('textarea.simple-editor').fill(GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText(/Score: 90%/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/1 hint/).first()).toBeVisible();
  await page.getByText(/Attempt history/).click();
  await expect(page.getByRole('cell', { name: '1', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '2', exact: true })).toBeVisible();
  await expect(page.getByText('Best score 90%')).toBeVisible();
});

test('C: refresh restores position, saved result and draft; seeking past a checkpoint is refused by the server', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await setup(page);
  await page.goto(`/lectures/${IDS.lecture}`);
  await finishVideo(page);
  await answer(page, 'Option B');
  await page.reload();
  await expect(page.getByText('Right because it is.')).toBeVisible(); // explanation survives refresh
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await expect(page.getByRole('heading', { name: 'Second concept' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Second concept' })).toBeVisible(); // resumed at the saved segment
  const res = await page.evaluate(async (v) => {
    const r = await fetch('http://api.mock.test/api/v1/lectures/l-9/session', { method: 'PATCH', headers: { 'content-type': 'application/json', authorization: 'Bearer x' }, body: JSON.stringify({ current_segment_id: 'seg-5', playback_position_seconds: 0, state_version: v }) });
    return r.status;
  }, state.version);
  expect(res).toBe(400);
});

test('code is preserved on refresh (server draft) and when switching tabs on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const state = await setup(page);
  await toLab(page);
  await typeCode(page, 'student_name = "Zed"\nprint(student_name)\n');
  await page.getByRole('tab', { name: 'Task' }).click();
  await expect(page.getByText('Create a variable called student_name and print it.')).toBeVisible();
  await page.getByRole('tab', { name: 'Code' }).click();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = "Zed"\nprint(student_name)\n');
  await expect(page.getByText('All changes saved')).toBeVisible({ timeout: 8000 });
  expect(state.drafts[IDS.ex]).toContain('Zed');
  await page.reload();
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = "Zed"\nprint(student_name)\n');
});

test('reset to starter asks for confirmation and can be cancelled', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await toLab(page);
  await typeCode(page, 'my work');
  await page.getByRole('button', { name: 'Reset to starter' }).click();
  await expect(page.getByRole('dialog', { name: 'Reset to starter code?' })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('my work');
  await page.getByRole('button', { name: 'Reset to starter' }).click();
  await page.getByRole('button', { name: 'Reset code' }).click();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = ""\nprint(student_name)\n');
});

test('E: grader outage shows an infrastructure message, never a failure or a pass', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page, { graderDown: true });
  await toLab(page);
  await typeCode(page, GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText(/problem with the grading system, not your code/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Grader unavailable').first()).toBeVisible();
  await expect(page.getByText('Passed', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Continue to exit check' })).toHaveCount(0);
  await expect(page.getByText('Needs retry')).toHaveCount(0);
});

test('failed media shows a recoverable error and never advances', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page, { videoFails: true });
  await page.goto(`/lectures/${IDS.lecture}`);
  await expect(page.getByRole('heading', { name: 'The video had a problem' })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
  await expect(page.getByLabel('Option A')).toHaveCount(0);
});

test('keyboard: skip link, sign-in form and answering a checkpoint without a mouse', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto('/sign-in');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Email')).toBeFocused();
  await page.keyboard.type('a@b.test'); await page.keyboard.press('Tab'); await page.keyboard.type('wrong');
  await page.keyboard.press('Enter');
  await expect(page.getByRole('alert')).toContainText('Sign-in failed');
  await expect(page.getByLabel('Email')).toHaveAttribute('aria-invalid', 'true');
  const state = newState(); await installMocks(page, state); await signedIn(page);
  await page.goto(`/lectures/${IDS.lecture}`);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await finishVideo(page);
  await page.getByLabel('Option A').focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByLabel('Option B')).toBeChecked();
  await page.getByRole('button', { name: 'Submit answer' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Right because it is.')).toBeVisible();
});

test('status is never conveyed by colour alone', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await toLab(page);
  await typeCode(page, HALF);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs retry').first()).toBeVisible({ timeout: 15_000 });
  for (const item of await page.locator('ul.criteria li').all()) {
    expect((await item.innerText()).trim()).toMatch(/Passed:|Not passed:/);
  }
  await expect(page.getByRole('progressbar', { name: 'Knowledge checks' })).toHaveAttribute('aria-valuetext', /\d of \d/);
});

test('expired session sends the learner to sign-in with an explanation', async ({ page }) => {
  await setup(page, { apiDown401: true });
  await page.goto('/');
  await expect(page).toHaveURL(/\/sign-in$/, { timeout: 15_000 });
  await expect(page.getByText(/Your session ended/)).toBeVisible();
});

test('sign-out clears cached data: the next user never sees the previous user', async ({ page }) => {
  const state = newState({ name: 'Asha Rao', email: 'asha@neuromind.test' });
  await installMocks(page, state);
  await page.goto('/sign-in');
  await page.getByLabel('Email').fill('asha@neuromind.test');
  await page.getByLabel('Password').fill('correct-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Welcome back, Asha')).toBeVisible();
  await expect(page.getByText('Asha Rao').first()).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  state.opts = { name: 'Bilal Khan', email: 'bilal@neuromind.test' };
  await page.getByLabel('Email').fill('bilal@neuromind.test');
  await page.getByLabel('Password').fill('correct-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Bilal Khan').first()).toBeVisible();
  await expect(page.getByText('Asha Rao')).toHaveCount(0);
  await expect(page.getByText('asha@neuromind.test')).toHaveCount(0);
});

test('learner cannot see or open teacher pages', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Teacher' })).toHaveCount(0);
  await page.goto('/teacher');
  await expect(page.getByText("You don't have access to this page.")).toBeVisible();
});

test('teacher: summary, search, pagination, evidence and feedback', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  const state = await setup(page, { role: 'teacher', name: 'Mr Teacher', email: 'teacher@neuromind.test' }, 'teacher@neuromind.test');
  await page.goto('/teacher');
  await expect(page.getByText('Assigned learners', { exact: true })).toBeVisible();
  await expect(page.getByText('Showing 1–10 of 13')).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('Showing 11–13 of 13')).toBeVisible();
  await page.getByRole('searchbox', { name: /Search learners/ }).fill('asha');
  await page.getByRole('button', { name: 'Search' }).click();
  await expect(page.getByRole('link', { name: 'View progress and evidence' })).toHaveCount(1);
  await page.getByRole('link', { name: 'View progress and evidence' }).click();
  await expect(page.getByRole('heading', { name: 'Asha Rao' })).toBeVisible();
  await expect(page.getByText('Grader problem').first()).toBeVisible(); // infra failure distinguished from a failed attempt
  await expect(page.getByText('Needs retry').first()).toBeVisible();
  await page.getByLabel('Message').fill('Nice work on the first attempt.');
  await page.getByRole('button', { name: 'Save feedback' }).click();
  await expect(page.getByText('Feedback saved and shared.')).toBeVisible();
  expect(state.feedback).toHaveLength(1);
  await page.getByRole('link', { name: 'Evidence' }).first().click();
  await expect(page.getByText('Grader version')).toBeVisible();
  await expect(page.getByText("Official scores can't be edited")).toBeVisible();
  await expect(page.getByRole('button', { name: /score/i })).toHaveCount(0);
});
