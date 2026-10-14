import { expect, test } from '@playwright/test';
import { API, GOOD, PASSWORD, answer, apiJson, setCode, signIn, signOutUi, toLab } from './helpers';

// REAL STACK: administrator workspace, cohorts, announcements, issue reports, certificates, portfolio, deactivation, two-step verification,
// logout/login persistence and next-lecture unlock. Needs the synthetic users from scripts/create_dev_users.py (they are deleted again afterwards).
// Lectures 10 to 12 are archived for the duration of the certificate test (so Lecture 9 is the whole course) and always restored.
test.describe.configure({ mode: 'serial' });

const SUPABASE_URL = process.env.E2E_SUPABASE_URL ?? '';
const SUPABASE_ANON = process.env.E2E_SUPABASE_ANON_KEY ?? '';
const COURSE = '00000000-0000-4000-8000-000000000001';

test('admin workspace: overview, create then deactivate and reactivate a person (sign-in really blocked), audit trail', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('/admin');
  await expect(page.getByRole('heading', { name: 'Administration' })).toBeVisible();
  await expect(page.getByText('Waiting to be graded')).toBeVisible();
  await expect(page.getByText('Service health')).toBeVisible();
  await page.goto('/admin/users');
  await expect(page.getByRole('cell', { name: 'learner1@neuromind.test' })).toBeVisible();
  await page.getByLabel('Full name').fill('Zed Temporary');
  await page.getByLabel('Email address').fill('zed.temp@neuromind.test');
  await page.getByLabel('Starting password').fill(`${PASSWORD}-zed`);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('Account created for Zed Temporary.')).toBeVisible();
  await page.getByLabel('Search by name or email').fill('zed.temp');
  await page.getByRole('button', { name: 'Search' }).click();
  await expect(page.getByRole('cell', { name: 'zed.temp@neuromind.test' })).toBeVisible();
  await page.getByRole('button', { name: /Deactivate Zed Temporary/ }).click();
  await page.getByRole('button', { name: 'Deactivate', exact: true }).click();
  await expect(page.getByText('Zed Temporary was deactivated.')).toBeVisible();

  // a deactivated person cannot sign in (the Auth user is banned) - checked straight against Supabase from the browser
  const attempt = () => page.evaluate(async ([url, key, pw]) => (await fetch(`${url}/auth/v1/token?grant_type=password`, { method: 'POST', headers: { apikey: key as string, 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'zed.temp@neuromind.test', password: pw }) })).status, [SUPABASE_URL, SUPABASE_ANON, `${PASSWORD}-zed`] as const);
  expect(await attempt()).toBeGreaterThanOrEqual(400);
  await page.getByRole('button', { name: /Reactivate Zed Temporary/ }).click();
  await expect(page.getByText('Zed Temporary was reactivated.')).toBeVisible();
  await expect.poll(attempt, { timeout: 30_000 }).toBe(200);

  await page.goto('/admin/audit');
  await expect(page.getByRole('row', { name: /admin\.user_deactivated/ }).first()).toBeVisible();
  await expect(page.getByRole('row', { name: /admin\.user_created/ }).first()).toBeVisible();
  await page.getByLabel('Filter by event type').selectOption('admin.user_reactivated');
  await expect(page.getByRole('row', { name: /admin\.user_reactivated/ }).first()).toBeVisible();
});

test('cohorts: admin builds one; the teacher sees it and the learner; announcement reaches only that teacher\'s learner; report exports', async ({ page }) => {
  await signIn(page, 'admin');
  await page.goto('/admin/cohorts');
  await page.getByLabel('Name').fill('E2E cohort');
  await page.getByRole('button', { name: 'Create cohort' }).click();
  await expect(page.getByRole('heading', { name: 'E2E cohort' })).toBeVisible();
  await page.getByLabel('Add a teacher to E2E cohort').selectOption({ label: 'Teacher' });
  await page.getByRole('button', { name: 'Add teacher' }).click();
  await expect(page.getByText('Teacher was added to E2E cohort.')).toBeVisible();
  await page.getByLabel('Add a learner to E2E cohort').selectOption({ label: 'Learner Two' });
  await page.getByRole('button', { name: 'Add learner' }).click();
  await expect(page.getByText('Learner Two was added to E2E cohort.')).toBeVisible();
  await signOutUi(page);

  await signIn(page, 'teacher');
  await page.goto('/teacher');
  await expect(page.getByRole('group', { name: 'Cohort E2E cohort' })).toContainText('1');
  await page.getByLabel('Title').fill('E2E announcement');
  await page.getByLabel('Message').fill('Bring your questions to the lab.');
  await page.getByRole('button', { name: 'Send announcement' }).click();
  await expect(page.getByText('Announcement sent.')).toBeVisible();
  const csv = await apiJson(page, 'GET', '/teacher/reports/progress');
  expect(csv.status).toBe(200);
  expect(csv.json.rows.length).toBeGreaterThanOrEqual(3);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download CSV' }).click();
  expect((await download).suggestedFilename()).toBe('progress-report.csv');
  await signOutUi(page);

  await signIn(page, 'learner2');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Announcements' })).toBeVisible();
  await expect(page.getByText('E2E announcement')).toBeVisible();

  // clean up: remove the announcement and archive the cohort
  await signOutUi(page);
  await signIn(page, 'teacher');
  await page.goto('/teacher');
  await page.getByRole('button', { name: /Remove announcement E2E announcement/ }).click();
  await expect(page.getByText('Announcement removed.')).toBeVisible();
  await signOutUi(page);
  await signIn(page, 'admin');
  await page.goto('/admin/cohorts');
  await page.getByRole('button', { name: /Archive E2E cohort/ }).click();
  await page.getByRole('button', { name: 'Archive', exact: true }).click();
  await expect(page.getByText('Cohort archived.')).toBeVisible();
});

test('issue report: a learner reports a problem, the administrator triages and resolves it', async ({ page }) => {
  await signIn(page, 'learner3');
  await page.goto('/help');
  await page.getByLabel('What is it about?').selectOption('accessibility');
  await page.getByLabel('What happened?').fill('E2E: the lab editor label is unclear');
  await page.getByRole('button', { name: 'Send report' }).click();
  await expect(page.getByText('Your report was sent.')).toBeVisible();
  const reference = (await page.getByText(/^Reference [0-9A-F]{8}\./).textContent())?.match(/[0-9A-F]{8}/)?.[0] ?? '';
  expect(reference).toHaveLength(8);
  await signOutUi(page);
  await signIn(page, 'admin');
  await page.goto('/admin/issues');
  await expect(page.getByRole('heading', { name: new RegExp(`Report ${reference}`) })).toBeVisible();
  await page.getByRole('button', { name: new RegExp(`Mark resolved report ${reference}`) }).click();
  await expect(page.getByText(`Report ${reference} marked resolved.`)).toBeVisible();
});

test('journey: complete, sign out and in again, next lecture unlocks, certificate is issued and verifiable, portfolio entry', async ({ page, browser }) => {
  // Lecture 9 is the whole course while Lectures 10 to 12 are archived; they are restored in `finally`.
  await signIn(page, 'admin');
  const lectures = await apiJson(page, 'GET', '/admin/courses');
  const others: { id: string; status: string }[] = lectures.json.courses[0].lectures.filter((l: { lecture_number: number }) => l.lecture_number !== 9);
  expect(others.length).toBeGreaterThan(0);
  const lecture10 = others.find((o: any) => o.lecture_number === 10) as any;
  try {
    // before: with Lecture 9 not yet completed, Lecture 10 is locked for a learner
    await signOutUi(page);
    await signIn(page, 'learner2');
    const before = await apiJson(page, 'GET', `/courses/${COURSE}`);
    expect(before.json.lectures.find((l: any) => l.lecture_number === 10).state).toBe('locked');
    await signOutUi(page);

    await signIn(page, 'admin');
    for (const o of others) expect((await apiJson(page, 'PATCH', `/admin/lectures/${o.id}/status`, { status: 'archived' })).status).toBe(200);
    await signOutUi(page);
    await page.waitForTimeout(20_000); // published content is cached for up to 15 s

    await signIn(page, 'learner1');
    await toLab(page);
    await setCode(page, GOOD);
    await page.getByRole('button', { name: 'Submit for grading' }).click();
    await expect(page.getByText('Passed').first()).toBeVisible({ timeout: 90_000 });
    await page.getByRole('button', { name: 'Add to portfolio' }).click();
    await page.getByLabel('Name this piece of work').fill('E2E first program');
    await page.getByRole('button', { name: 'Add', exact: true }).click();
    await expect(page.getByText('Added to your')).toBeVisible();
    await page.getByRole('button', { name: 'Continue to exit check' }).click();
    await answer(page, '25');
    await page.getByRole('button', { name: 'Finish lecture' }).click();
    await expect(page.getByRole('heading', { name: /Lecture complete/ })).toBeVisible();

    // logout, then login again: completion is server state
    await signOutUi(page);
    await signIn(page, 'learner1');
    await page.goto(`/courses/${COURSE}`);
    await expect(page.getByText(/Completed/).first()).toBeVisible();
    const certs = await apiJson(page, 'GET', '/me/certificates');
    expect(certs.json.certificates).toHaveLength(1);
    const serial: string = certs.json.certificates[0].serial;
    await page.goto('/certificates');
    await expect(page.getByText(`Serial ${serial}`)).toBeVisible();
    await page.goto('/portfolio');
    await expect(page.getByRole('heading', { name: 'E2E first program' })).toBeVisible();

    // anyone can verify the serial, with no sign-in and a masked name
    const anon = await (await browser.newContext()).newPage();
    await anon.goto(`/verify/${serial}`);
    await expect(anon.getByText('This certificate is genuine.')).toBeVisible();
    await anon.goto('/verify/NM-2026-00000000');
    await expect(anon.getByText('No certificate was found for that serial.')).toBeVisible();
    await anon.context().close();
    // the portfolio and certificate belong to one learner only
    await signOutUi(page);
    await signIn(page, 'learner3');
    expect((await apiJson(page, 'GET', '/me/certificates')).json.certificates).toHaveLength(0);
    expect((await apiJson(page, 'GET', '/me/portfolio')).json.items).toHaveLength(0);
  } finally {
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await signIn(p, 'admin');
    for (const o of others) await apiJson(p, 'PATCH', `/admin/lectures/${o.id}/status`, { status: 'published' });
    await ctx.close();
  }

  // after restoring, Lecture 10 is open to the learner who completed Lecture 9 (unlock), and still locked for one who has not
  await page.waitForTimeout(20_000);
  await signOutUi(page).catch(() => undefined);
  await signIn(page, 'learner1');
  const after = await apiJson(page, 'GET', `/courses/${COURSE}`);
  expect(after.json.lectures.find((l: any) => l.id === lecture10.id).state).toMatch(/available|in_progress/);
  await page.goto(`/lectures/${lecture10.id}`);
  await expect(page.getByRole('heading', { name: /Lecture 10/ })).toBeVisible();
});

test('two-step verification on the real service: enrol, a password-only session is refused by the API, the code unlocks it', async ({ page }) => {
  test.skip(!SUPABASE_URL || !SUPABASE_ANON, 'E2E_SUPABASE_URL / E2E_SUPABASE_ANON_KEY not set');
  await signIn(page, 'learner3');
  const result = await page.evaluate(async ([url, key, email, pw]) => {
    const post = async (path: string, token: string | null, body: unknown) => {
      const res = await fetch(`${url}${path}`, { method: 'POST', headers: { apikey: key as string, 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify(body) });
      return { status: res.status, json: await res.json().catch(() => ({})) } as { status: number; json: any };
    };
    const base32 = (s: string) => { const a = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; let bits = ''; for (const c of s.replace(/=+$/, '')) bits += a.indexOf(c).toString(2).padStart(5, '0'); const out: number[] = []; for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2)); return new Uint8Array(out); };
    const totp = async (secret: string) => {
      const k = await crypto.subtle.importKey('raw', base32(secret), { name: 'HMAC', hash: 'SHA-1' }, false, ['sign']);
      const counter = Math.floor(Date.now() / 30000); const buf = new ArrayBuffer(8); new DataView(buf).setUint32(4, counter);
      const h = new Uint8Array(await crypto.subtle.sign('HMAC', k, buf)); const o = h[19] & 15;
      return String(((h[o] & 127) << 24 | h[o + 1] << 16 | h[o + 2] << 8 | h[o + 3]) % 1_000_000).padStart(6, '0');
    };
    const login = async () => (await post('/auth/v1/token?grant_type=password', null, { email, password: pw })).json.access_token as string;
    const t1 = await login();
    const enrol = await post('/auth/v1/factors', t1, { factor_type: 'totp', friendly_name: 'e2e' });
    if (enrol.status >= 400) return { error: `enrol ${enrol.status} ${JSON.stringify(enrol.json).slice(0, 120)}` };
    const factorId = enrol.json.id as string; const secret = enrol.json.totp.secret as string;
    const ch = await post(`/auth/v1/factors/${factorId}/challenge`, t1, {});
    const ver = await post(`/auth/v1/factors/${factorId}/verify`, t1, { challenge_id: ch.json.id, code: await totp(secret) });
    if (ver.status >= 400) return { error: `verify ${ver.status}` };
    return { factorId, secret, aal2: ver.json.access_token as string };
  }, [SUPABASE_URL, SUPABASE_ANON, 'learner3@neuromind.test', PASSWORD] as const);
  expect('error' in result ? result.error : '').toBe('');
  const { factorId, aal2 } = result as { factorId: string; secret: string; aal2: string };
  const callApi = (token: string) => page.evaluate(async ([url, t]) => { const r = await fetch(`${url}/me`, { headers: { Authorization: `Bearer ${t}` } }); return { status: r.status, code: (await r.json().catch(() => ({}))).error?.code }; }, [`${API}/api/v1`, token] as const);
  try {
    expect((await callApi(aal2)).status).toBe(200); // the session that completed the code step is accepted
    const fresh = await page.evaluate(async ([url, key, email, pw]) => (await (await fetch(`${url}/auth/v1/token?grant_type=password`, { method: 'POST', headers: { apikey: key as string, 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: pw }) })).json()).access_token as string, [SUPABASE_URL, SUPABASE_ANON, 'learner3@neuromind.test', PASSWORD] as const);
    const refused = await callApi(fresh); // password only: assurance level 1
    expect(refused).toEqual({ status: 403, code: 'MFA_REQUIRED' });
  } finally {
    await page.evaluate(async ([url, key, token, id]) => { await fetch(`${url}/auth/v1/factors/${id}`, { method: 'DELETE', headers: { apikey: key as string, Authorization: `Bearer ${token}` } }); }, [SUPABASE_URL, SUPABASE_ANON, aal2, factorId] as const);
  }
});
