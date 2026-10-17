import { expect, test, type Page } from '@playwright/test';
import { BAD, GOOD, apiJson, setCode, signIn, signOutUi, toLab } from './helpers';

// REAL STACK: Practical Labs (Block 1) against production. Needs the temporary neuromind.test accounts (scripts/create_dev_users.py)
// and, for the second test, learner3 with lectures 9–23 marked completed (so the requests and numpy labs are reachable).
// The browser quick check (Pyodide) is asserted; the official server verdict is recorded in the log, not asserted, because the
// grader host may still run the previous image.
test.describe.configure({ mode: 'serial' });

const SOLUTION_24 = `import numpy as np

scores_list = [72, 85, 90, 64, 58, 95, 77, 81]

scores = np.array(scores_list)

mean_score = scores.mean()
highest = scores.max()
lowest = scores.min()
spread = scores.std()

curved = scores + 5

print("Mean:", mean_score)
print("Highest:", highest)
print("Lowest:", lowest)
print("Standard deviation:", round(spread, 2))
print("Curved:", curved.tolist())
`;

const SOLUTION_23 = `import requests

URL = "https://api.neuromind.lab/v1/weather"


def weather_sentence(city):
    response = requests.get(URL, params={"city": city})
    if response.status_code == 200:
        data = response.json()
        return f"The temperature in {city} is {data['temperature_c']} degrees."
    else:
        return f"Sorry, {city} was not found."


print(weather_sentence("Pune"))
print(weather_sentence("Atlantis"))
`;

interface LabRow { lecture_number: number; exercise_id: string; state: string; lecture_state: string; packages: string[]; title: string }

async function labRows(page: Page): Promise<LabRow[]> {
  const r = await apiJson(page, 'GET', '/labs');
  expect(r.status).toBe(200);
  return r.json.courses[0].modules.flatMap((m: { labs: LabRow[] }) => m.labs);
}

async function quickCheck(page: Page, code: string): Promise<'passed' | 'failed'> {
  await setCode(page, code);
  await page.getByRole('button', { name: 'Save & check' }).click();
  const dialog = page.getByTestId('check-dialog');
  const passed = dialog.getByText(/Looks right in the browser/);
  const failed = dialog.getByRole('heading', { name: 'Not quite right yet' });
  await expect(passed.or(failed).first()).toBeVisible({ timeout: 180_000 }); // the first run downloads Pyodide and the lab's packages
  return (await passed.isVisible()) ? 'passed' : 'failed';
}

/** Waits (bounded) for the official verdict and logs it; never fails the test on it. */
async function officialVerdict(page: Page, exerciseId: string): Promise<string> {
  const dialog = page.getByTestId('check-dialog');
  const final = dialog.getByRole('heading', { name: /Lab passed|Not quite right yet|The checker had a problem/ });
  await final.waitFor({ timeout: 90_000 }).catch(() => undefined);
  const subs = await apiJson(page, 'GET', `/exercises/${exerciseId}/submissions`);
  const latest = subs.json?.submissions?.at(-1);
  const verdict = latest ? `${latest.status} (${latest.passed_tests ?? '?'}/${latest.total_tests ?? '?'} checks)` : 'no submission';
  console.log(`OFFICIAL VERDICT for ${exerciseId}: ${verdict}`);
  await dialog.getByRole('button', { name: /Dismiss|Close/ }).first().click();
  await expect(dialog).toBeHidden();
  return latest?.status ?? 'none';
}

test('learner: Block 1 catalogue, lecture 9 lab opens after its knowledge checks, browser check fails then passes, 3 hints then Redo', async ({ page }) => {
  await signIn(page, 'learner1');
  await page.getByRole('link', { name: 'Practical labs' }).click();
  await expect(page.getByRole('heading', { name: 'Practical labs', level: 1 })).toBeVisible();
  await expect(page.getByText('0 of 16 labs passed.')).toBeVisible();
  await expect(page.getByText('Not started').first()).toBeVisible();
  expect(await page.getByRole('button', { name: /Locked/ }).count()).toBe(15);
  const rows = await labRows(page);
  expect(rows.map((r) => r.lecture_number)).toEqual(Array.from({ length: 16 }, (_, i) => i + 9));
  const nine = rows.find((r) => r.lecture_number === 9)!;
  expect(nine.state).toBe('not_started');
  expect(rows.find((r) => r.lecture_number === 13)!.state).toBe('locked');

  // before the lecture's knowledge checks the lab page says what to do, and the API refuses the lab (400)
  await page.getByRole('link', { name: 'Open lab' }).first().click();
  await expect(page.getByText(/opens after the knowledge checks/)).toBeVisible();
  expect((await apiJson(page, 'GET', `/exercises/${nine.exercise_id}`)).status).toBe(400);

  // walk the lecture (answers the checks) and open the lab from Practical labs
  await page.goto('/');
  await toLab(page);
  await page.goto(`/labs/${nine.exercise_id}`);
  await expect(page.getByRole('heading', { name: /hello\.py/, level: 1 })).toBeVisible();
  await expect(page.getByRole('button', { name: /Hint: 0 of 3 used/ })).toBeVisible();
  const ex0 = await apiJson(page, 'GET', `/exercises/${nine.exercise_id}`);
  expect(ex0.json.scoring).toBe('pass_fail');
  expect(ex0.json.hints_max).toBe(3);
  expect(ex0.json.visible_checks).toHaveLength(5); // 6 checks, the hidden one never leaves the server
  expect(ex0.json.visible_checks.every((c: { definition: unknown }) => c.definition)).toBe(true);

  // wrong code: the browser check names what failed; Dismiss closes the popup
  expect(await quickCheck(page, BAD)).toBe('failed');
  const dialog = page.getByTestId('check-dialog');
  await expect(dialog.locator('.check-errors li').first()).toContainText('Not passed:');
  console.log('QUICK CHECK (bad code):', (await dialog.locator('.check-errors li').allInnerTexts()).join(' | '));
  await officialVerdict(page, nine.exercise_id);

  // the bulb gives 3 hints, the 4th is refused by the server, then Redo starts a fresh cycle with the starter code
  for (let i = 1; i <= 3; i++) {
    await page.getByRole('button', { name: new RegExp(`Hint: ${i - 1} of 3 used`) }).click();
    await expect(page.getByText(`Hint ${i}:`)).toBeVisible({ timeout: 20_000 });
  }
  await expect(page.getByRole('button', { name: /Hint: 3 of 3 used/ })).toBeDisabled();
  const fourth = await apiJson(page, 'POST', `/exercises/${nine.exercise_id}/hints`, { hint_index: 3 });
  expect(fourth.status).toBe(409);
  await page.getByRole('button', { name: /Redo the lab/ }).click();
  await expect(page.getByRole('button', { name: /Hint: 0 of 3 used/ })).toBeEnabled({ timeout: 20_000 });
  const ex1 = await apiJson(page, 'GET', `/exercises/${nine.exercise_id}`);
  expect([ex1.json.cycle, ex1.json.redo_count, ex1.json.hints_used]).toEqual([2, 1, 0]);
  await expect(page.locator('textarea.simple-editor')).toHaveValue(ex1.json.starter_code);

  // right code: the browser check passes and the attempt is recorded on the server
  expect(await quickCheck(page, GOOD)).toBe('passed');
  await officialVerdict(page, nine.exercise_id);
  const subs = await apiJson(page, 'GET', `/exercises/${nine.exercise_id}/submissions`);
  expect(subs.json.submissions).toHaveLength(2); // the history survives Redo
  await page.goto('/labs');
  await expect(page.getByText(/In progress|Passed|Try again/).first()).toBeVisible();
});

test('learner who reached lectures 23 and 24: the practice API (requests) and numpy run in the browser check', async ({ page }) => {
  await signIn(page, 'learner3');
  const rows = await labRows(page);
  for (const n of [24, 23]) {
    const row = rows.find((r) => r.lecture_number === n)!;
    expect(row.state, `lecture ${n} must be reachable for learner3`).toBe('not_started');
    await page.goto(`/labs/${row.exercise_id}`);
    await expect(page.getByRole('heading', { name: n === 24 ? /NumPy/ : /weather/i, level: 1 })).toBeVisible();
    expect(await quickCheck(page, n === 24 ? SOLUTION_24 : SOLUTION_23)).toBe('passed');
    await officialVerdict(page, row.exercise_id);
  }
});

test('teacher sees the review queue and the learner results; the administrator sees every check, the hidden one included', async ({ page }) => {
  await signIn(page, 'teacher');
  await page.getByRole('link', { name: 'Reviews waiting for you' }).click();
  await expect(page.getByRole('heading', { name: 'Reviews', level: 1 })).toBeVisible();
  const reviews = await apiJson(page, 'GET', '/teacher/reviews');
  expect(reviews.status).toBe(200);
  expect(Array.isArray(reviews.json.pending)).toBe(true);
  const learners = await apiJson(page, 'GET', '/teacher/learners');
  expect(learners.status).toBe(200);
  await signOutUi(page);

  await signIn(page, 'admin');
  const nine = (await labRows(page)).find((r) => r.lecture_number === 9)!;
  const tests = await apiJson(page, 'GET', `/admin/exercises/${nine.exercise_id}/tests`);
  expect(tests.status).toBe(200);
  expect(tests.json.tests).toHaveLength(6);
  expect(tests.json.tests.filter((t: { hidden: boolean }) => t.hidden)).toHaveLength(1);
  expect(tests.json.tests.every((t: { definition: unknown }) => t.definition)).toBe(true);
  await page.goto('/admin/content');
  await page.getByRole('button', { name: 'Show checks' }).first().click();
  await expect(page.locator('.badge', { hasText: 'hidden' }).first()).toBeVisible();
});
