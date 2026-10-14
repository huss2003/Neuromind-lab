import { expect, test, type Page } from '@playwright/test';
import { IDS, installMocks, newState, signedIn } from './mockServer';

/** Structure checks for what a screen reader user relies on (landmarks, headings, titles, focus after navigation, announcements).
 *  This is NOT a test with a real screen reader (NVDA, JAWS, VoiceOver, TalkBack); it checks the accessibility tree and focus. */
async function outline(page: Page) {
  return page.evaluate(() => {
    const visible = (el: Element) => !!(el as HTMLElement).offsetParent || getComputedStyle(el).position === 'fixed';
    return {
      title: document.title,
      mains: [...document.querySelectorAll('main, [role=main]')].filter(visible).length,
      navs: [...document.querySelectorAll('nav, [role=navigation]')].filter(visible).map((n) => n.getAttribute('aria-label') ?? ''),
      levels: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible).map((h) => Number(h.tagName[1])),
      unlabeled: [...document.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(visible).filter((e) => {
        const el = e as HTMLInputElement;
        return !(el.labels?.length || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'));
      }).map((e) => e.outerHTML.slice(0, 80)),
      imgsNoAlt: [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length,
    };
  });
}

const SCREENS: [string, string][] = [['dashboard', '/'], ['course', `/courses/${IDS.course}`], ['progress', '/progress'], ['profile', '/profile'], ['help', '/help'], ['welcome', '/welcome'], ['orientation', `/lectures/${IDS.lecture}`]];

test('every learner screen has one main landmark, one h1, ordered headings, a labelled nav, labelled fields and its own title', async ({ page }) => {
  await installMocks(page, newState({}));
  await signedIn(page);
  const titles = new Set<string>();
  for (const [name, path] of SCREENS) {
    await page.goto(path);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.waitForLoadState('networkidle');
    const o = await outline(page);
    expect(o.mains, `${name}: main landmarks`).toBe(1);
    expect(o.levels.filter((l) => l === 1), `${name}: h1 count`).toHaveLength(1);
    o.levels.forEach((l, i) => { if (i > 0) expect(l - o.levels[i - 1], `${name}: heading levels ${o.levels.join(',')}`).toBeLessThanOrEqual(1); });
    expect(o.navs.length, `${name}: nav landmarks`).toBeGreaterThan(0);
    expect(new Set(o.navs).size, `${name}: nav landmarks need distinct labels`).toBe(o.navs.length);
    expect(o.unlabeled, `${name}: unlabelled fields`).toEqual([]);
    expect(o.imgsNoAlt, `${name}: images without alt`).toBe(0);
    expect(o.title, `${name}: title`).not.toBe('');
    titles.add(o.title);
  }
  expect(titles.size, 'screens should announce different document titles').toBeGreaterThan(3);
});

test('after in-app navigation, keyboard focus moves into the new page instead of staying on the old link', async ({ page }) => {
  await installMocks(page, newState({}));
  await signedIn(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('link', { name: 'Help' }).first().click();
  await expect(page.getByRole('heading', { name: /Help/ }).first()).toBeVisible();
  const inMain = await page.evaluate(() => {
    const a = document.activeElement;
    return !!a && (a === document.body ? false : !!a.closest('main') || a.tagName === 'MAIN' || a.tagName === 'H1' || a.id === 'main');
  });
  expect(inMain, 'focus should land on the new page heading or main region').toBe(true);
});

test('checkpoint options are a named group and the result is announced through a status live region', async ({ page }) => {
  await installMocks(page, newState({}));
  await signedIn(page);
  await page.goto(`/lectures/${IDS.lecture}`);
  await page.getByRole('button', { name: 'Start lecture' }).click();
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: /finished this video/ }).click();
  // the options belong to a named group (the question is the legend), so each radio is announced in context
  await expect(page.getByRole('group', { name: /Which statement prints text in Python/ })).toBeVisible();
  await page.getByLabel('Option B', { exact: true }).check();
  await page.getByRole('button', { name: 'Submit answer' }).click();
  const status = page.getByRole('status').filter({ hasText: /Correct|Not quite/ });
  await expect(status).toBeVisible(); // announced politely: role=status is a live region
});

test('a signed-out visit to the home page is redirected to sign-in with the skip link still the first thing Tab reaches', async ({ page }) => {
  await installMocks(page, newState({}));
  await page.goto('/');
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
});
