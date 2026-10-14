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
/** Orientation screen -> Start, then the intro section -> Continue. */
async function startLecture(page: Page) {
  // A learner who has already started resumes where they left off, without the orientation screen.
  const orientation = page.getByRole('heading', { name: 'Before you start' });
  const resumed = page.getByRole('button', { name: /finished this video|Submit answer|Submit for grading/ });
  await expect(orientation.or(resumed).first()).toBeVisible();
  if (await orientation.isVisible()) {
    await page.getByRole('button', { name: 'Start lecture' }).click();
    await expect(page.getByText('Today you will set up Python and write your first program.')).toBeVisible();
    await page.getByRole('button', { name: 'Continue' }).click();
  }
}
async function answer(page: Page, option: string) {
  await page.getByLabel(option, { exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
}
async function toLab(page: Page) {
  await page.goto(`/lectures/${IDS.lecture}`);
  await startLecture(page);
  await finishVideo(page);
  await answer(page, 'Option B'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await answer(page, 'Option A'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page); // practical video -> exercise opens automatically
  await expect(page.getByRole('heading', { name: /Print your name/ })).toBeVisible();
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
        ['course', `/courses/${IDS.course}`, async () => { await expect(page.getByText('Module 2: Python for AI')).toBeVisible(); }],
        ['progress', '/progress', async () => { await expect(page.getByRole('heading', { name: 'My progress' })).toBeVisible(); }],
        ['orientation', `/lectures/${IDS.lecture}`, async () => { await expect(page.getByRole('heading', { name: 'Before you start' })).toBeVisible(); }],
      ];
      for (const [name, path, ready] of screens) {
        await page.goto(path); await ready(); await noOverflow(page, `${name} @${vp.name}`); await shot(page, `${vp.name}-${name}`);
      }
      await page.goto(`/lectures/${IDS.lecture}`);
      await page.getByRole('button', { name: 'Start lecture' }).click();
      await noOverflow(page, `intro section @${vp.name}`); await shot(page, `${vp.name}-intro`);
      await page.getByRole('button', { name: 'Continue' }).click();
      await expect(page.getByRole('heading', { name: 'Introduction and first concept' })).toBeVisible();
      await noOverflow(page, `video @${vp.name}`); await shot(page, `${vp.name}-video`);
      await toLab(page);
      await noOverflow(page, `lab @${vp.name}`); await shot(page, `${vp.name}-lab-code`);
      await typeCode(page, HALF);
      await page.getByRole('button', { name: 'Submit for grading' }).click();
      await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
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
  await expect(page.getByText('About 60 minutes')).toBeVisible();
  await expect(page.getByText('None — you can start right away.')).toBeVisible();
  await expect(page.getByText('Pass the practical lab with at least 80%.')).toBeVisible();
  await expect(page.getByText(/practise as often as you like/)).toBeVisible();
  await startLecture(page);
  await finishVideo(page);
  await expect(page.getByText('the video is paused')).toBeVisible();
  await answer(page, 'Option C'); // wrong on purpose
  await expect(page.getByText('Not quite')).toBeVisible();
  await expect(page.getByText('Not this one — see the lesson.')).toBeVisible();
  await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await answer(page, 'Option A'); await page.getByRole('button', { name: 'Continue lesson' }).click();
  await finishVideo(page);
  await expect(page.getByRole('heading', { name: /Print your name/ })).toBeVisible(); // exercise opened automatically
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
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Print the variable with print(student_name).')).toBeVisible(); // remediation for the failed hidden check
  await expect(page.getByText('Hidden check 1')).toBeVisible();
  await expect(page.getByText('Best score 50%')).toBeVisible();
  await page.getByRole('button', { name: /Show hint 1 of 3/ }).click();
  await expect(page.getByText('Create a variable called student_name.')).toBeVisible();
  await page.locator('textarea.simple-editor').fill(GOOD);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText(/Score: 90%/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/1 hint/).first()).toBeVisible();
  await page.getByText(/Attempt history \(/).click();
  await expect(page.getByRole('cell', { name: '1', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '2', exact: true })).toBeVisible();
  await expect(page.getByText('Best score 90%')).toBeVisible();
});

test('C: refresh restores position, saved result and draft; seeking past a checkpoint is refused by the server', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = await setup(page);
  await page.goto(`/lectures/${IDS.lecture}`);
  await startLecture(page);
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
  await expect(page.getByText('System error — not your fault').first()).toBeVisible();
  await expect(page.getByText('Passed', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Continue to exit check' })).toHaveCount(0);
  await expect(page.getByText('Needs work', { exact: true })).toHaveCount(0);
});

test('failed media shows a recoverable error and never advances', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page, { videoFails: true });
  await page.goto(`/lectures/${IDS.lecture}`);
  await startLecture(page);
  await expect(page.getByRole('heading', { name: 'The video had a problem' })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
  await expect(page.getByLabel('Option A')).toHaveCount(0);
});

test('keyboard: skip link, sign-in form and answering a checkpoint without a mouse', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto('/sign-in');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused(); // the sign-in page offers a skip link too
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
  await startLecture(page);
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
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
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
  await expect(page.getByText('Needs work').first()).toBeVisible();
  await page.getByLabel('Message').fill('Nice work on the first attempt.');
  await page.getByRole('button', { name: 'Save feedback' }).click();
  await expect(page.getByText('Feedback saved and shared.')).toBeVisible();
  expect(state.feedback).toHaveLength(1);
  await page.getByRole('link', { name: 'Evidence' }).first().click();
  await expect(page.getByText('Grader version')).toBeVisible();
  await expect(page.getByText("Official scores can't be edited")).toBeVisible();
  await expect(page.getByRole('button', { name: /score/i })).toHaveCount(0);
});

// ---------------- Flow spec (Complete Flow & Working v1.0) ----------------
test('flow: dashboard shows continue-learning, recent attempts and a remediation queue derived from the last failed attempt', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Start: Lecture 9/ })).toBeVisible();
  await expect(page.getByText("You haven't submitted any code yet")).toBeVisible();
  await toLab(page);
  await typeCode(page, HALF);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
  await page.getByRole('link', { name: 'Dashboard' }).first().click();
  await expect(page.getByRole('heading', { name: /Continue: Lecture 9/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Next steps to improve' })).toBeVisible();
  await expect(page.getByText('Focus on: Print output with print()')).toBeVisible();
  await expect(page.getByRole('table').getByText('Needs work')).toBeVisible();
  await shot(page, 'dashboard-after-failure');
});

test('flow: a learner who is not enrolled sees a clear empty state, not an error', async ({ page }) => {
  await setup(page, { unenrolled: true });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'You are not enrolled in a course yet' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('flow: the course map shows server-decided states; a locked lecture cannot be opened', async ({ page }) => {
  await setup(page, { lockedLecture: true });
  await page.goto(`/courses/${IDS.course}`);
  await expect(page.getByText('Locked', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Locked' })).toBeDisabled();
  await expect(page.getByText('Complete the earlier lecture first to unlock this one.').first()).toBeVisible();
  await page.goto(`/lectures/${IDS.lecture}`);
  await expect(page.getByRole('heading', { name: 'This lecture is locked' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Before you start' })).toHaveCount(0);
});

test('flow: remediation maps a failed check to its objective and lets the learner replay the section without losing code', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await toLab(page);
  await typeCode(page, 'student_name = 5\n');
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Store text in a variable:')).toBeVisible();
  await page.getByRole('button', { name: /Review “Practical demonstration”/ }).click();
  const dlg = page.getByRole('dialog', { name: /Review: Practical demonstration/ });
  await expect(dlg).toBeVisible();
  await expect(dlg.getByText("Replaying a section doesn't change your progress")).toBeVisible();
  await dlg.getByRole('button', { name: 'Back to the exercise' }).click();
  await expect(dlg).toBeHidden();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = 5\n');
});

test('flow: exercise panel shows objective, task, constraints, success criteria, examples and the hint policy', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await toLab(page);
  await expect(page.getByRole('heading', { name: 'Objective' })).toBeVisible();
  await expect(page.getByText('Create a text variable and print it.')).toBeVisible();
  await expect(page.getByText('Use a variable named student_name and print() once.')).toBeVisible();
  await expect(page.getByText('What you print matches student_name')).toBeVisible();
  await expect(page.getByText(/visible examples are a guide; the official tests are private/)).toBeVisible();
  await expect(page.getByText('Expected output:')).toBeVisible();
  await expect(page.getByText(/never lowers a score you already earned/)).toBeVisible();
  await expect(page.getByText(/Practice.*runs in your browser and never counts/)).toBeVisible();
  await page.getByRole('button', { name: 'Load into editor' }).click();
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = "Aarav"\nprint(student_name)');
});

for (const [status, label, text] of [
  ['runtime_error', 'Runtime error', /stopped with an error/],
  ['timeout', 'Time limit', /loop that never ends/],
  ['expired', 'Expired — not your fault', /not because of your code/],
] as const) {
  test(`flow: status vocabulary — ${status}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await setup(page, { forceStatus: status });
    await toLab(page);
    await typeCode(page, GOOD);
    await page.getByRole('button', { name: 'Submit for grading' }).click();
    await expect(page.getByRole('status').filter({ hasText: label }).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(text)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue to exit check' })).toHaveCount(0);
    if (status === 'expired') await expect(page.getByText(/Score:/)).toHaveCount(0);
  });
}

test('flow: if the server cannot be reached the draft is kept on the device and restored later', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page, { draftFails: true });
  await toLab(page);
  await typeCode(page, 'student_name = "Offline"\n');
  await expect(page.getByText(/kept on this device/)).toBeVisible({ timeout: 8000 });
  await page.evaluate(() => { window.onbeforeunload = null; });
  page.once('dialog', (d) => void d.accept()); // the unsaved-work warning
  await page.reload();
  await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await expect(page.getByText(/restored work that was saved on this device/)).toBeVisible();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = "Offline"\n');
});

test('flow: teacher filters for learners who need support and sees analytics and content status', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await setup(page, { role: 'teacher', name: 'Mr Teacher', email: 'teacher@neuromind.test' }, 'teacher@neuromind.test');
  await page.goto('/teacher');
  await expect(page.getByText('Needs support', { exact: true }).first()).toBeVisible();
  await page.getByRole('checkbox', { name: 'Needs support' }).check();
  await expect(page.getByRole('link', { name: 'View progress and evidence' })).toHaveCount(1);
  await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Exercise analytics' })).toBeVisible();
  await expect(page.getByText('completion 50%')).toBeVisible();
  await expect(page.getByText('Hidden check 1 — 4 times')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Content status' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'v1' })).toBeVisible();
  await expect(page.getByText("Editing, review and publishing of content isn't enabled")).toBeVisible();
  await shot(page, 'teacher-analytics');
});

test('UX spec S02: account recovery gives the same confirmation and offers a way back', async ({ page }) => {
  const state = newState({});
  await installMocks(page, state);
  await page.goto('/sign-in');
  await page.getByRole('link', { name: 'Forgot your password?' }).click();
  await page.getByLabel('Email').fill('nobody@example.test');
  await page.getByRole('button', { name: 'Send reset instructions' }).click();
  await expect(page.getByRole('status')).toContainText('If an account exists for that email');
  await page.getByRole('link', { name: 'Return to sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
});

test('UX spec S03/S18/S15: welcome, help with FAQ and attempt history', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setup(page);
  await page.goto('/welcome');
  await expect(page.getByRole('heading', { name: 'How the lab works' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Start learning' })).toBeVisible();
  await noOverflow(page, 'welcome');
  await page.goto('/help');
  await page.getByText('What does “System error — not your fault” mean?').click();
  await expect(page.getByText('was not marked incorrect and your best score is unchanged')).toBeVisible();
  await expect(page.getByText('Never share passwords, keys or other secrets')).toBeVisible();
  await noOverflow(page, 'help');
  await page.goto(`/exercises/${IDS.ex}/attempts`);
  await expect(page.getByRole('heading', { name: /Attempts: / })).toBeVisible();
  await expect(page.getByText('No official attempts yet')).toBeVisible();
  await page.goto('/progress');
  await page.getByText('How is progress calculated?').click();
  await expect(page.getByText(/Watching a video alone does not complete/)).toBeVisible();
});

test('policies hub lists every policy and each page opens without signing in', async ({ page }) => {
  await page.goto('/policies');
  await expect(page.getByRole('heading', { level: 1, name: 'Policies' })).toBeVisible();
  for (const name of ['Privacy notice', 'Terms of use', 'Acceptable use and academic honesty', 'Data retention', 'Accessibility statement', 'Security and reporting']) {
    await page.goto('/policies');
    await page.getByRole('link', { name }).click();
    await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
    await expect(page.getByRole('link', { name: 'All policies' }).first()).toBeVisible();
  }
});

test('portfolio: only a passed result can be added, it appears in the portfolio, and the result is announced to screen readers', async ({ page }) => {
  await setup(page);
  await toLab(page);
  await typeCode(page, HALF);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('button', { name: 'Add to portfolio' })).toHaveCount(0); // a failed attempt cannot be added
  await expect(page.getByTestId('result-announcement')).toContainText(/Official result: Needs work\. Score 50 percent/);
  await page.locator('textarea.simple-editor').fill(GOOD); // the plain editor is already on from the first attempt
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('result-announcement')).toContainText(/Official result: Passed\. Score 100 percent/);
  await page.getByRole('button', { name: 'Add to portfolio' }).click();
  await page.getByLabel('Name this piece of work').fill('My first program');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await expect(page.getByText('Added to your')).toBeVisible();
  await page.getByRole('link', { name: 'Portfolio', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'My first program' })).toBeVisible();
  await expect(page.getByText('official score 100%')).toBeVisible();
  await page.getByRole('button', { name: /Remove My first program/ }).click();
  await page.getByRole('button', { name: 'Remove', exact: true }).click();
  await expect(page.getByText('Nothing here yet')).toBeVisible();
});

test('attempt history shows the exercise version of every attempt', async ({ page }) => {
  await setup(page);
  await toLab(page);
  await typeCode(page, HALF);
  await page.getByRole('button', { name: 'Submit for grading' }).click();
  await expect(page.getByText('Needs work').first()).toBeVisible({ timeout: 15_000 });
  await page.goto(`/exercises/${IDS.ex}/attempts`);
  await expect(page.getByRole('columnheader', { name: 'Exercise version' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Lesson v1, checks v1' })).toBeVisible();
});

test('certificates: none until earned; an issued certificate can be printed; anyone can verify a serial', async ({ page }) => {
  const state = await setup(page);
  await page.goto('/certificates');
  await expect(page.getByText('No certificate yet')).toBeVisible();
  state.ext.certificates.push({ id: 'c1', serial: 'NM-2026-ABCD1234', course: 'NeuroMind AI Foundations', issued_at: '2026-10-14T00:00:00Z', completed_lectures: 4, holder: 'Asha Rao' });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Asha Rao' })).toBeVisible();
  await expect(page.getByText('Serial NM-2026-ABCD1234')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Print or save as PDF' })).toBeVisible();
  await page.goto('/verify/NM-2026-ABCD1234');
  await expect(page.getByText('This certificate is genuine.')).toBeVisible();
  await expect(page.getByText(/Asha R\. completed NeuroMind AI Foundations/)).toBeVisible();
  await page.getByLabel('Certificate serial').fill('nm-2026-00000000');
  await page.getByRole('button', { name: 'Check' }).click();
  await expect(page.getByText('No certificate was found for that serial.')).toBeVisible();
});

test('help: a problem report is sent with a reference, and announcements show on the dashboard', async ({ page }) => {
  const state = await setup(page);
  state.ext.announcements.push({ id: 'an1', title: 'Lab on Friday', body: 'Bring your questions.', created_at: '2026-10-14T00:00:00Z', from: 'Tara Teacher' });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Announcements' })).toBeVisible();
  await expect(page.getByText('Lab on Friday')).toBeVisible();
  await page.goto('/help');
  await page.getByLabel('What is it about?').selectOption('grading');
  await page.getByLabel('What happened?').fill('My lab result looks wrong');
  await page.getByRole('button', { name: 'Send report' }).click();
  await expect(page.getByText('Your report was sent.')).toBeVisible();
  await expect(page.getByText('Reference I9ABCDEF')).toBeVisible();
  expect(state.ext.reported).toEqual([{ category: 'grading', message: 'My lab result looks wrong' }]);
});

test('sign-up: same confirmation for every address, and sign-in offers sign-up and social sign-in', async ({ page }) => {
  const state = newState();
  await installMocks(page, state);
  await page.goto('/sign-in');
  await expect(page.getByRole('link', { name: 'Create an account' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Google' })).toBeVisible();
  await page.getByRole('link', { name: 'Create an account' }).click();
  await page.getByLabel('Full name').fill('New Learner');
  await page.getByLabel('Email').fill('new@example.test');
  await page.getByLabel('Password').fill('a-long-password-123');
  await expect(page.getByRole('button', { name: 'Create account' })).toBeDisabled(); // terms must be accepted first
  await page.getByLabel(/I have read the/).check();
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
  expect(state.ext.signups).toEqual(['new@example.test']);
  await page.getByRole('button', { name: 'Send the email again' }).click();
  await expect.poll(() => state.calls).toContain('POST /auth/v1/resend');
  await page.goto('/sign-in');
  await page.getByRole('button', { name: 'Google' }).click(); // leaves the app for the provider
  await expect.poll(() => state.ext.oauth).toContain('google');
});

test('two-step verification: set up in the profile, then required before anything protected shows', async ({ page }) => {
  const state = newState();
  await installMocks(page, state);
  await signedIn(page);
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Set up' }).click();
  await expect(page.getByAltText('QR code for your authenticator app')).toBeVisible();
  await expect(page.getByText('JBSWY3DPEHPK3PXP')).toBeVisible();
  await page.getByLabel('6-digit code').fill('000000');
  await page.getByRole('button', { name: 'Turn on' }).click();
  await expect(page.getByText('That code did not match.')).toBeVisible();
  await page.getByLabel('6-digit code').fill('123456');
  await page.getByRole('button', { name: 'Turn on' }).click();
  await expect(page.getByText('Two-step verification is on.')).toBeVisible();
  // a new session for an account with a verified factor starts at assurance level 1: the challenge comes before any content
  const challenged = await page.context().newPage();
  await installMocks(challenged, state);
  await signedIn(challenged, 'learner1@neuromind.test', (await import('./mockServer')).token('learner1@neuromind.test', 'aal1', state.ext.factors));
  await challenged.goto('/');
  await expect(challenged.getByRole('heading', { name: 'Two-step verification' })).toBeVisible();
  await expect(challenged.getByRole('heading', { name: /Lecture 9/ })).toHaveCount(0);
  await challenged.getByLabel('6-digit code').fill('654321');
  await challenged.getByRole('button', { name: 'Verify' }).click();
  await expect(challenged.getByText('That code did not work.')).toBeVisible();
  await challenged.getByLabel('6-digit code').fill('123456');
  await challenged.getByRole('button', { name: 'Verify' }).click();
  await expect(challenged.getByRole('heading', { level: 1 })).toContainText('Lecture 9');
});

test('certificate check works for a visitor who is not signed in (the sign-out notice on load must not cancel the request)', async ({ page }) => {
  await installMocks(page, newState()); // no session
  await page.goto('/verify/NM-2026-ABCD1234');
  await expect(page.getByText('This certificate is genuine.')).toBeVisible();
  await page.getByLabel('Certificate serial').fill('NM-2026-FFFFFFFF');
  await page.getByRole('button', { name: 'Check' }).click();
  await expect(page.getByText('No certificate was found for that serial.')).toBeVisible();
});
