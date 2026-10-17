import { expect, test, type Page } from '@playwright/test';
import { IDS, installMocks, newState, signedIn, type MockOpts, type MockState } from './mockServer';

// Practical Labs (mocked network): the catalogue, the Save & check popup with Dismiss / Show hint, bulb hints capped at 3 with Redo,
// quiz marking, written work reviewed by the teacher, and the administrator's view of every check.
async function learner(page: Page, opts: MockOpts = {}): Promise<MockState> {
  const state = newState({ labReady: true, passFail: true, ...opts });
  await installMocks(page, state);
  await signedIn(page);
  return state;
}
const BAD = 'student_name = 5\nprint(student_name)\n';
const GOOD = 'student_name = "Aarav"\nprint(student_name)\n';
async function setCode(page: Page, code: string) {
  const area = page.locator('textarea.simple-editor');
  if (!(await area.isVisible())) await page.getByRole('button', { name: 'Use simple text editor' }).click();
  await area.fill(code);
}

test('catalogue: the Practical labs section lists each lecture lab with its state and opens the lab', async ({ page }) => {
  await learner(page);
  await page.goto('/');
  await page.getByRole('link', { name: 'Practical labs' }).click();
  await expect(page.getByRole('heading', { name: 'Practical labs', level: 1 })).toBeVisible();
  await expect(page.getByText('0 of 1 labs passed.')).toBeVisible();
  await expect(page.getByText('Not started')).toBeVisible();
  await page.getByRole('link', { name: 'Open lab' }).click();
  await expect(page.getByRole('heading', { name: 'Print your name', level: 1 })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save & check' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Hint: 0 of 3 used/ })).toBeVisible();
});

test('catalogue: a locked lecture shows a locked lab that cannot be opened', async ({ page }) => {
  await learner(page, { lockedLecture: true });
  await page.goto('/labs');
  await expect(page.getByRole('button', { name: /Locked/ })).toBeDisabled();
  await page.goto(`/labs/${IDS.ex}`);
  await expect(page.getByText(/This lab is locked/)).toBeVisible();
});

test('save & check: a failing attempt opens the popup with the error, Dismiss closes it, Show hint explains the fix', async ({ page }) => {
  const state = await learner(page);
  await page.goto(`/labs/${IDS.ex}`);
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Save & check' }).click();
  const dialog = page.getByTestId('check-dialog');
  await expect(dialog.getByRole('heading', { name: 'Not quite right yet' })).toBeVisible({ timeout: 15_000 });
  await expect(dialog.getByText('Not passed: student_name holds text')).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Dismiss' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Show hint' }).click();
  await expect(page.getByTestId('check-fix')).toContainText('Create student_name = "Aarav".');
  await dialog.getByRole('button', { name: 'Dismiss' }).click();
  await expect(dialog).toBeHidden();
  expect(state.submissions).toHaveLength(1);
  expect(state.hintsShown).toBe(0); // the fix explanation is free: it is not one of the 3 hints
  await expect(page.getByText(/Not passed yet · 0 of 3 hints used/)).toBeVisible();
});

test('hints: the bulb gives 3 hints, then Redo restores the starter code and fresh hints while keeping the history', async ({ page }) => {
  const state = await learner(page);
  await page.goto(`/labs/${IDS.ex}`);
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Save & check' }).click();
  await page.getByTestId('check-dialog').getByRole('button', { name: 'Dismiss' }).click();
  for (let i = 1; i <= 3; i++) {
    await page.getByRole('button', { name: new RegExp(`Hint: ${i - 1} of 3 used`) }).click();
    await expect(page.getByText(`Hint ${i}:`)).toBeVisible();
  }
  await expect(page.getByRole('button', { name: /Hint: 3 of 3 used/ })).toBeDisabled();
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Save & check' }).click();
  const dialog = page.getByTestId('check-dialog');
  await expect(dialog.getByRole('heading', { name: 'Not quite right yet' })).toBeVisible({ timeout: 15_000 });
  await dialog.getByRole('button', { name: 'Redo the lab' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: /Hint: 0 of 3 used/ })).toBeEnabled();
  await expect(page.locator('textarea.simple-editor')).toHaveValue('student_name = ""\nprint(student_name)\n');
  expect(state.cycle).toBe(2);
  expect(state.submissions).toHaveLength(2); // history kept
  await expect(page.getByText('Attempt history (2)')).toBeVisible();
});

test('hints: after the 3rd hint the Redo button appears in the lab at once, without a reload or another check', async ({ page }) => {
  const state = await learner(page);
  await page.goto(`/labs/${IDS.ex}`);
  await setCode(page, BAD);
  await page.getByRole('button', { name: 'Save & check' }).click();
  await page.getByTestId('check-dialog').getByRole('button', { name: 'Dismiss' }).click();
  await expect(page.getByRole('button', { name: /Redo the lab/ })).toHaveCount(0);
  for (let i = 1; i <= 3; i++) {
    await page.getByRole('button', { name: new RegExp(`Hint: ${i - 1} of 3 used`) }).click();
    await expect(page.getByText(`Hint ${i}:`)).toBeVisible();
  }
  await expect(page.getByText(/Not passed yet · 3 of 3 hints used/)).toBeVisible();
  await page.getByRole('button', { name: /Redo the lab/ }).click();
  await expect(page.getByRole('button', { name: /Hint: 0 of 3 used/ })).toBeEnabled();
  expect(state.cycle).toBe(2);
});

test('save & check: a correct attempt passes, the popup says so and the catalogue shows Passed', async ({ page }) => {
  await learner(page);
  await page.goto(`/labs/${IDS.ex}`);
  await setCode(page, GOOD);
  await page.getByRole('button', { name: 'Save & check' }).click();
  const dialog = page.getByTestId('check-dialog');
  await expect(dialog.getByRole('heading', { name: 'Lab passed' })).toBeVisible({ timeout: 15_000 });
  await dialog.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByText('Passed', { exact: false }).first()).toBeVisible();
  await expect(page.getByTestId('result-announcement')).toContainText('Passed');
  await page.goto('/labs');
  await expect(page.getByText('1 of 1 labs passed.')).toBeVisible();
  await page.getByText('Month 2: Python Fundamentals I').click(); // a fully passed month is collapsed
  await expect(page.getByRole('link', { name: 'Review lab' })).toBeVisible();
});

test('quiz lab: answers are marked by the server; wrong answers show explanations; all right passes', async ({ page }) => {
  await learner(page, { labKind: 'quiz' });
  await page.goto(`/labs/${IDS.ex}`);
  await expect(page.getByRole('heading', { name: 'Question set' })).toBeVisible();
  const save = page.getByRole('button', { name: 'Save & check' });
  await expect(save).toBeDisabled();
  await page.getByLabel('print("Hi")').check();
  await page.getByLabel('3.5').check();
  await page.getByLabel('"42"').check();
  await save.click();
  await expect(page.getByText('✕ Not correct. // divides and rounds down.')).toBeVisible();
  await expect(page.getByText('Needs work')).toBeVisible();
  await page.getByLabel('3', { exact: true }).check();
  await save.click();
  await expect(page.getByRole('heading', { name: 'Passed' })).toBeVisible();
});

test('written lab: the learner sends text, the teacher marks it against the rubric, the learner sees the decision', async ({ page, browser }) => {
  const state = await learner(page, { labKind: 'written' });
  await page.goto(`/labs/${IDS.ex}`);
  await expect(page.getByRole('heading', { name: 'Written task' })).toBeVisible();
  await expect(page.getByText('Names the problem clearly')).toBeVisible();
  await page.getByLabel('Your answer').fill('The delivery app predicts arrival time from traffic data; I checked it against three real orders.');
  await page.getByRole('button', { name: 'Save & send for review' }).click();
  await expect(page.getByText('Sent to your teacher.')).toBeVisible();
  // the teacher, sharing the same mocked state
  const t = await (await browser.newContext()).newPage();
  const teacherState = { ...state, opts: { ...state.opts, role: 'teacher' as const, name: 'Tara Teacher', email: 'teacher@neuromind.test' } };
  await installMocks(t, teacherState);
  await signedIn(t, 'teacher@neuromind.test');
  await t.goto('/teacher');
  await t.getByRole('link', { name: 'Reviews waiting for you' }).click();
  await expect(t.getByRole('rowheader', { name: 'Asha Rao' })).toBeVisible();
  await t.getByRole('link', { name: 'Review' }).click();
  await expect(t.getByRole('heading', { name: 'Written answer' })).toBeVisible();
  await expect(t.getByText(/predicts arrival time/)).toBeVisible();
  await t.getByLabel('Points for Names the problem clearly').fill('2');
  await t.getByLabel('Points for Gives evidence').fill('3');
  await t.getByLabel('Pass', { exact: true }).check();
  await t.getByLabel('Feedback for the learner').fill('Clear problem and real evidence. Well done.');
  await t.getByRole('button', { name: 'Save decision' }).click();
  await expect(t.getByText('Decision saved.')).toBeVisible();
  await t.context().close();
  await page.reload();
  await expect(page.getByText("Teacher's decision: passed.")).toBeVisible();
  await expect(page.getByText('Clear problem and real evidence. Well done.').first()).toBeVisible();
});

test('upload lab: the link must be https and every checklist item ticked', async ({ page }) => {
  await learner(page, { labKind: 'upload' });
  await page.goto(`/labs/${IDS.ex}`);
  await expect(page.getByRole('heading', { name: 'Project upload' })).toBeVisible();
  await page.getByLabel('Deployed to a hosting service').check();
  await page.getByLabel('README explains purpose and limits').check();
  await page.getByLabel('Link to your work (https)').fill('https://github.com/asha/capstone');
  await page.getByRole('button', { name: 'Save & send for review' }).click();
  await expect(page.getByText('Sent to your teacher.')).toBeVisible();
});

test('administrator: every check of a lab is visible, hidden ones included', async ({ page }) => {
  const state = newState({ role: 'admin', name: 'Owner', email: 'admin@neuromind.test' });
  await installMocks(page, state);
  await signedIn(page, 'admin@neuromind.test');
  await page.goto('/admin/content');
  await page.getByRole('button', { name: 'Show checks' }).click();
  await expect(page.getByText('The printed text matches student_name')).toBeVisible();
  await expect(page.getByText('"check":"stdout_equals_variable"')).toBeVisible();
  await expect(page.locator('.badge', { hasText: 'hidden' })).toBeVisible();
});
