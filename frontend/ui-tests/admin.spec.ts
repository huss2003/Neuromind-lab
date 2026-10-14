import { expect, test, type Page } from '@playwright/test';
import { IDS, installMocks, newState, signedIn, type MockOpts } from './mockServer';

async function asRole(page: Page, role: 'admin' | 'teacher' | 'learner', opts: MockOpts = {}) {
  const state = newState({ role, name: role === 'admin' ? 'Owner' : 'Tara Teacher', email: `${role}@neuromind.test`, ...opts });
  await installMocks(page, state);
  await signedIn(page, `${role}@neuromind.test`);
  return state;
}

test('administration is for administrators only, in the menu and in the API', async ({ page }) => {
  await asRole(page, 'learner');
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Administration' })).toHaveCount(0);
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Not available' })).toBeVisible();
  const t = await page.context().newPage();
  await asRole(t, 'teacher');
  await t.goto('/admin/users');
  await expect(t.getByRole('heading', { name: 'Not available' })).toBeVisible();
});

test('overview shows health, queue and a dead-letter warning; every section is reachable from the sub-menu', async ({ page }) => {
  await asRole(page, 'admin');
  await page.goto('/');
  await page.getByRole('link', { name: 'Administration' }).click();
  await expect(page.getByRole('heading', { name: 'Administration' })).toBeVisible();
  await expect(page.getByText('Waiting to be graded')).toBeVisible();
  await expect(page.getByText('1 attempt could not be graded.')).toBeVisible();
  for (const [link, heading] of [['Users', 'People'], ['Cohorts', 'New cohort'], ['Content', 'NeuroMind AI Foundations'], ['Grading queue', 'Timing, last 24 hours'], ['Audit log', 'Events'], ['Issue reports', 'Report I1ABCDEF'], ['Settings', 'Backups and recovery']] as const) {
    await page.getByRole('navigation', { name: 'Administration sections' }).getByRole('link', { name: link, exact: true }).click();
    await expect(page.getByRole('heading', { name: new RegExp(heading) }).or(page.getByText(heading)).first()).toBeVisible();
  }
});

test('users: search, change a role, add a person, deactivate with confirmation and reactivate', async ({ page }) => {
  const state = await asRole(page, 'admin');
  await page.goto('/admin/users');
  await expect(page.getByRole('cell', { name: 'asha@example.test' })).toBeVisible();
  await page.getByLabel('Search by name or email').fill('tara');
  await page.getByRole('button', { name: 'Search' }).click();
  await expect(page.getByRole('cell', { name: 'asha@example.test' })).toHaveCount(0);
  await page.getByLabel('Search by name or email').fill('');
  await page.getByRole('button', { name: 'Search' }).click();
  await page.getByLabel('Role for Asha Rao').selectOption('teacher');
  await expect(page.getByText('Asha Rao is now a teacher.')).toBeVisible();
  expect(state.ext.users.find((u) => u.id === 'u-1')?.role).toBe('teacher');
  await page.getByLabel('Full name').fill('Bilal Khan');
  await page.getByLabel('Email address').fill('bilal@example.test');
  await page.getByLabel('Starting password').fill('a-long-password-123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('Account created for Bilal Khan.')).toBeVisible();
  await page.getByRole('button', { name: /Deactivate Bilal Khan/ }).click();
  await expect(page.getByRole('heading', { name: 'Deactivate Bilal Khan?' })).toBeVisible();
  await page.getByRole('button', { name: 'Deactivate', exact: true }).click();
  await expect(page.getByText('Bilal Khan was deactivated.')).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Deactivated' })).toBeVisible();
  await page.getByRole('button', { name: /Reactivate Bilal Khan/ }).click();
  await expect(page.getByText('Bilal Khan was reactivated.')).toBeVisible();
  await expect(page.getByRole('button', { name: /Deactivate Owner/ })).toHaveCount(0); // never offered for yourself
});

test('cohorts: create, add a teacher and a learner, remove one, archive', async ({ page }) => {
  const state = await asRole(page, 'admin');
  await page.goto('/admin/cohorts');
  await page.getByLabel('Name').fill('Autumn evening group');
  await page.getByRole('button', { name: 'Create cohort' }).click();
  await expect(page.getByRole('heading', { name: 'Autumn evening group' })).toBeVisible();
  await page.getByLabel('Add a teacher to Autumn evening group').selectOption({ label: 'Tara Teacher' });
  await page.getByRole('button', { name: 'Add teacher' }).click();
  await expect(page.getByText('Tara Teacher was added to Autumn evening group.')).toBeVisible();
  await page.getByLabel('Add a learner to Autumn evening group').selectOption({ label: 'Asha Rao' });
  await page.getByRole('button', { name: 'Add learner' }).click();
  await expect(page.getByText('Asha Rao was added to Autumn evening group.')).toBeVisible();
  expect(state.ext.cohorts[0].learners.map((l) => l.display_name)).toEqual(['Asha Rao']);
  await page.getByRole('button', { name: /Remove Asha Rao from Autumn evening group/ }).click();
  await expect(page.getByText('Asha Rao was removed from Autumn evening group.')).toBeVisible();
  await page.getByRole('button', { name: /Archive Autumn evening group/ }).click();
  await page.getByRole('button', { name: 'Archive', exact: true }).click();
  await expect(page.getByText('No cohorts yet')).toBeVisible();
});

test('content, queue, audit, issues and settings: act on each', async ({ page }) => {
  const state = await asRole(page, 'admin');
  await page.goto('/admin/content');
  await page.getByLabel('Status of lecture 9').selectOption('archived');
  await expect(page.getByText('Lecture 9 is now archived.')).toBeVisible();
  expect(state.ext.lectureStatus).toBe('archived');

  await page.goto('/admin/queue');
  await expect(page.getByRole('row', { name: /dead0001/ })).toBeVisible();
  await page.getByRole('button', { name: /Retry attempt dead0001/ }).click();
  await page.getByRole('button', { name: 'Put back in the queue' }).click();
  await expect(page.getByText('The attempt is back in the queue.')).toBeVisible();
  await expect(page.getByText('Nothing stuck')).toBeVisible();
  expect(state.ext.requeued).toEqual(['dead0001-aaaa']);

  await page.goto('/admin/audit');
  await expect(page.getByRole('row', { name: /admin\.user_created/ })).toBeVisible();
  await page.getByLabel('Filter by event type').selectOption('auth.denied');
  await expect(page.getByRole('row', { name: /admin\.user_created/ })).toHaveCount(0);
  await expect(page.getByRole('row', { name: /auth\.denied/ })).toBeVisible();

  await page.goto('/admin/issues');
  await expect(page.getByText('There is a typo in lesson two')).toBeVisible();
  await page.getByLabel('Note (visible to administrators only)').fill('Fixed in version 3');
  await page.getByRole('button', { name: /Mark resolved/ }).click();
  await expect(page.getByText('Report I1ABCDEF marked resolved.')).toBeVisible();
  await expect(page.getByText('No reports here')).toBeVisible();

  await page.goto('/admin/settings');
  await expect(page.getByRole('row', { name: /Grading mode/ })).toContainText('queue');
});

test('teacher tools: cohorts, announcements, and the progress report as CSV and printable page', async ({ page }) => {
  const state = await asRole(page, 'teacher');
  await page.goto('/teacher');
  await expect(page.getByRole('group', { name: 'Cohort Autumn evening group' })).toContainText('3 in progress');
  await page.getByLabel('Title').fill('Lab on Friday');
  await page.getByLabel('Message').fill('Bring your questions.');
  await page.getByRole('button', { name: 'Send announcement' }).click();
  await expect(page.getByText('Announcement sent.')).toBeVisible();
  expect(state.ext.teacherAnnouncements[0]).toMatchObject({ title: 'Lab on Friday', scope: 'assigned' });
  await expect(page.getByLabel('Who sees it')).toHaveCount(0); // only administrators can address the whole course
  await page.getByRole('button', { name: /Remove announcement Lab on Friday/ }).click();
  await expect(page.getByText('Announcement removed.')).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download CSV' }).click();
  expect((await download).suggestedFilename()).toBe('progress-report.csv');
  await page.getByRole('link', { name: 'Open printable report (PDF)' }).click();
  await expect(page.getByRole('heading', { name: 'Progress report' })).toBeVisible();
  await expect(page.getByRole('cell', { name: '92.5' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Print or save as PDF' })).toBeVisible();
  expect(IDS.course).toBeTruthy();
});
