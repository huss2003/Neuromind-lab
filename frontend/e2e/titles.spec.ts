import { expect, test } from '@playwright/test';
import { signIn } from './helpers';

// Production check of the accessibility behaviour: every screen has its own title and in-app navigation moves focus into the content.
test('page titles differ per screen and focus moves into the page after in-app navigation', async ({ page }) => {
  await signIn(page, 'learner3');
  const titles: string[] = [];
  for (const path of ['/', '/progress', '/help', '/profile', '/policies']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect.poll(() => page.title()).toMatch(/NeuroMind Lab$/);
    titles.push(await page.title());
  }
  expect(new Set(titles).size).toBe(titles.length);
  await page.goto('/');
  await page.getByRole('link', { name: 'Help' }).first().click();
  await expect(page.getByRole('heading', { name: /Help/ }).first()).toBeVisible();
  expect(await page.evaluate(() => !!document.activeElement?.closest('#main, main'))).toBe(true);
});
