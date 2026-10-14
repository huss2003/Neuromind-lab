import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { IDS, installMocks, newState, signedIn } from './mockServer';

/** Automated WCAG 2.1 A/AA scan (axe-core). This finds a subset of problems; it is NOT proof of full accessibility. */
async function scan(page: Page, where: string) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const bad = results.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(' | ')}`);
  expect(bad, `axe violations on ${where}`).toEqual([]);
}

for (const vp of [{ w: 1440, h: 900 }, { w: 390, h: 844 }]) {
  test(`axe: learner screens at ${vp.w}px have no WCAG A/AA violations`, async ({ page }) => {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    const state = newState({});
    await installMocks(page, state);
    await signedIn(page);
    for (const [name, path] of [['dashboard', '/'], ['course', `/courses/${IDS.course}`], ['progress', '/progress'], ['profile', '/profile'], ['help', '/help'], ['welcome', '/welcome'], ['orientation', `/lectures/${IDS.lecture}`]]) {
      await page.goto(path);
      await expect(page.locator('main, [role=main]').first()).toBeVisible();
      await page.waitForLoadState('networkidle');
      await scan(page, `${name} @${vp.w}`);
    }
    await page.goto(`/lectures/${IDS.lecture}`);
    await page.getByRole('button', { name: 'Start lecture' }).click();
    await expect(page.getByText('Today you will set up Python and write your first program.')).toBeVisible();
    await scan(page, `intro @${vp.w}`);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByRole('button', { name: /finished this video/ })).toBeVisible();
    await scan(page, `video @${vp.w}`);
    await page.getByRole('button', { name: /finished this video/ }).click();
    await expect(page.getByRole('button', { name: 'Submit answer' })).toBeVisible();
    await scan(page, `checkpoint @${vp.w}`);
    await page.getByLabel('Option B', { exact: true }).check();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
    await scan(page, `checkpoint result @${vp.w}`);
  });
}

test('axe: sign-in, recovery and teacher screens', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const state = newState({ role: 'teacher', name: 'Mr Teacher', email: 'teacher@neuromind.test' });
  await installMocks(page, state);
  await page.goto('/sign-in');
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  await scan(page, 'sign-in');
  await page.goto('/recover');
  await expect(page.getByRole('heading', { name: 'Recover your account' })).toBeVisible();
  await scan(page, 'recover');
  for (const [name, path] of [['policies', '/policies'], ['privacy', '/privacy'], ['terms', '/terms'], ['acceptable use', '/policies/acceptable-use'], ['retention', '/policies/retention'], ['accessibility', '/policies/accessibility'], ['security', '/policies/security']]) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await scan(page, name);
  }
  await signedIn(page, 'teacher@neuromind.test');
  await page.goto('/teacher');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.waitForLoadState('networkidle');
  await scan(page, 'teacher dashboard');
});
