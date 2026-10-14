/* Browser-boundary mock of Supabase Auth + the NeuroMind API. Mirrors the documented API rules closely enough to
   exercise the real UI. Anything it proves is about the UI, not the real backend. */
import type { Page, Route } from '@playwright/test';

const J = { 'content-type': 'application/json', 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
const ok = (r: Route, body: unknown, status = 200) => r.fulfill({ status, headers: J, body: JSON.stringify(body) });
const err = (r: Route, status: number, code: string, message: string) => ok(r, { error: { code, message, details: [], request_id: 'req-mock-1234' } }, status);

export const IDS = { course: 'c-1', module: 'm-1', lecture: 'l-9', cp1: 'cp-1', cp2: 'cp-2', cp3: 'cp-3', q1: 'q-1', q2: 'q-2', q3: 'q-3', ex: 'ex-1', learner: 'lrn-1', learner2: 'lrn-2' };
const SEG = (n: number) => `seg-${n}`;
const opts = [{ id: 'a', text: 'Option A' }, { id: 'b', text: 'Option B' }, { id: 'c', text: 'Option C' }];
const CORRECT: Record<string, string> = { [IDS.q1]: 'b', [IDS.q2]: 'a', [IDS.q3]: 'a' };
const EXPL = { right: 'Right because it is.', wrong: 'Not this one — see the lesson.' };

export interface MockOpts { role?: 'learner' | 'teacher' | 'admin'; email?: string; name?: string; graderDown?: boolean; apiDown401?: boolean; videoFails?: boolean; unenrolled?: boolean; lockedLecture?: boolean; forceStatus?: 'runtime_error' | 'timeout' | 'expired'; draftFails?: boolean }
export interface MockState {
  version: number; current: string; position: number; status: 'in_progress' | 'completed'; started: boolean;
  attempts: { cp: string; correct: boolean; at: number }[]; completedCps: Set<string>; submissions: any[]; drafts: Record<string, string>;
  ext: Ext; hintsShown: number; feedback: { id: string; body: string; published: boolean }[]; calls: string[]; auditPatches: number; opts: MockOpts;
}

export interface Ext {
  users: { id: string; email: string; display_name: string; role: string; deactivated: boolean; last_sign_in_at: string | null; created_at: string; email_confirmed: boolean }[];
  cohorts: { id: string; course_id: string; name: string; learners: { id: string; display_name: string }[]; teachers: { id: string; display_name: string }[] }[];
  issues: { id: string; reference: string; category: string; message: string; page: string | null; status: string; admin_note: string | null; created_at: string; reporter: string }[];
  deadLetters: { submission_id: string; exercise_id: string; created_at: string; claim_count: number }[];
  certificates: { id: string; serial: string; course: string; issued_at: string; completed_lectures: number; holder: string }[];
  portfolio: { id: string; title: string; note: string; created_at: string; exercise: string; score: number; submission_id: string; source_code: string }[];
  announcements: { id: string; title: string; body: string; created_at: string; from: string }[];
  teacherAnnouncements: { id: string; title: string; body: string; scope: string; course_id: string; created_at: string }[];
  factors: { id: string; factor_type: 'totp'; status: 'verified' | 'unverified' }[]; signups: string[]; oauth: string[]; imports: { lecture_number: number; publish: boolean; replace: boolean }[];
  lectureStatus: string; reported: { category: string; message: string }[]; requeued: string[];
}

export function newState(opts: MockOpts = {}): MockState {
  return { version: 1, current: SEG(0), position: 0, status: 'in_progress', started: false, attempts: [], completedCps: new Set(), submissions: [], drafts: {}, ext: { users: [
    { id: 'u-1', email: 'asha@example.test', display_name: 'Asha Rao', role: 'learner', deactivated: false, last_sign_in_at: '2026-10-13T09:00:00Z', created_at: '2026-10-01T00:00:00Z', email_confirmed: true },
    { id: 'u-2', email: 'tara@example.test', display_name: 'Tara Teacher', role: 'teacher', deactivated: false, last_sign_in_at: null, created_at: '2026-10-01T00:00:00Z', email_confirmed: true },
    { id: IDS.learner, email: 'owner@example.test', display_name: 'Owner', role: 'admin', deactivated: false, last_sign_in_at: '2026-10-14T05:00:00Z', created_at: '2026-10-01T00:00:00Z', email_confirmed: true }],
    cohorts: [], issues: [{ id: 'i-1', reference: 'I1ABCDEF', category: 'content', message: 'There is a typo in lesson two', page: '/lectures/l-9', status: 'open', admin_note: null, created_at: '2026-10-14T05:00:00Z', reporter: 'Asha Rao' }],
    deadLetters: [{ submission_id: 'dead0001-aaaa', exercise_id: 'ex-1', created_at: '2026-10-14T04:00:00Z', claim_count: 3 }], certificates: [], portfolio: [], announcements: [], teacherAnnouncements: [], lectureStatus: 'published', reported: [], requeued: [], factors: [], signups: [], oauth: [], imports: [] },
  hintsShown: 0, feedback: [], calls: [], auditPatches: 0, opts };
}

const segments = [
  { id: SEG(0), order: 0, type: 'intro', title: 'Introduction: what you will do today', required: true, body: 'Today you will set up Python and write your first program.', next_action: { type: 'next_segment' } },
  { id: SEG(1), order: 1, type: 'video', title: 'Introduction and first concept', required: true, media: { provider: 'external', url: 'http://media.mock.test/1.mp4', captions_url: null, transcript: 'Transcript of the first video.' }, next_action: { type: 'next_segment' } },
  { id: SEG(2), order: 2, type: 'checkpoint', title: 'Knowledge check 1', required: true, checkpoint: { id: IDS.cp1, type: 'mcq', required: true, question: { id: IDS.q1, prompt: 'Which statement prints text in Python?', options: opts } }, next_action: { type: 'next_segment' } },
  { id: SEG(3), order: 3, type: 'video', title: 'Second concept', required: true, media: { provider: 'external', url: 'http://media.mock.test/2.mp4' }, next_action: { type: 'next_segment' } },
  { id: SEG(4), order: 4, type: 'checkpoint', title: 'Knowledge check 2', required: true, checkpoint: { id: IDS.cp2, type: 'mcq', required: true, question: { id: IDS.q2, prompt: 'What is a notebook cell?', options: opts } }, next_action: { type: 'next_segment' } },
  { id: SEG(5), order: 5, type: 'video', title: 'Practical demonstration', required: true, media: { provider: 'external', url: 'http://media.mock.test/3.mp4' }, next_action: { type: 'open_exercise', exercise_id: IDS.ex } },
  { id: SEG(6), order: 6, type: 'exercise', title: 'Guided exercise', required: true, exercise_id: IDS.ex, next_action: { type: 'next_segment' } },
  { id: SEG(7), order: 7, type: 'exit_check', title: 'Exit check', required: true, checkpoint: { id: IDS.cp3, type: 'exit_check', required: true, question: { id: IDS.q3, prompt: 'Which symbol assigns a value?', options: opts } }, next_action: { type: 'next_segment' } },
];

const passedEx = (s: MockState) => s.submissions.some((x) => x.status === 'passed');
const gates = (s: MockState) => [[2, s.completedCps.has(IDS.cp1)], [4, s.completedCps.has(IDS.cp2)], [6, passedEx(s)], [7, s.completedCps.has(IDS.cp3)]] as const;
const reach = (s: MockState) => (gates(s).find(([, done]) => !done)?.[0] ?? 7);
const dashboardView = (s: MockState) => {
  if (s.opts.unenrolled) return { enrolled: false, course: null, continue: null, recent_attempts: [], remediation_queue: [] };
  const failed = s.submissions.filter((x) => ['failed', 'runtime_error'].includes(x.status));
  const last = s.submissions[s.submissions.length - 1];
  return {
    enrolled: true,
    course: { id: IDS.course, title: 'NeuroMind AI Foundations', description: 'A practical path from your first Python program to building AI systems.', completed_lectures: s.status === 'completed' ? 1 : 0, total_lectures: 1 },
    continue: { lecture_id: IDS.lecture, lecture_number: 9, title: 'Python setup, notebooks and the first program', state: s.started ? 'in_progress' : 'available' },
    recent_attempts: s.submissions.slice(-5).reverse().map((x) => ({ submission_id: x.id, exercise: 'Print your name', lecture_id: IDS.lecture, number: x.number, status: x.status, score: x.score, best_score: bestScore(s), created_at: new Date(x.at).toISOString() })),
    remediation_queue: failed.length && !passedEx(s) && last ? [{ exercise_id: IDS.ex, exercise: 'Print your name', lecture_id: IDS.lecture, lecture: 'Lecture 9: Python setup, notebooks and the first program', last_status: last.status, objectives: last.criteria.filter((c: any) => !c.passed && c.objective).map((c: any) => c.objective), steps: last.criteria.filter((c: any) => !c.passed && c.remediation).map((c: any) => ({ criterion: c.label, text: c.remediation, objective: c.objective, review_title: c.review_title })) }] : [],
  };
};
const bestScore = (s: MockState) => { const v = s.submissions.filter((x) => ['passed', 'failed'].includes(x.status) && x.score != null).map((x) => x.score); return v.length ? Math.max(...v) : null; };

function sessionView(s: MockState) {
  const cur = Number(s.current.split('-')[1]);
  const results: Record<string, unknown> = {};
  for (const a of s.attempts) results[a.cp] = { attempt_id: `a-${a.at}`, is_correct: a.correct, score: a.correct ? 1 : 0, explanation: a.correct ? EXPL.right : EXPL.wrong, checkpoint_completed: s.completedCps.has(a.cp) };
  const lastSub = s.submissions[s.submissions.length - 1];
  const lectureState = s.status === 'completed' ? 'COMPLETED' : s.submissions.some((x) => x.status === 'queued' || x.status === 'running') ? 'GRADING_PENDING'
    : lastSub && ['failed', 'runtime_error'].includes(lastSub.status) && !passedEx(s) ? 'REMEDIATION_REQUIRED'
    : s.attempts.length === 0 && s.submissions.length === 0 && s.current === SEG(0) && !s.position ? 'NOT_STARTED' : 'IN_PROGRESS';
  return {
    lecture_state: lectureState,
    lecture_id: IDS.lecture, current_segment_id: s.current, playback_position_seconds: s.position, status: s.status,
    completed_checkpoint_ids: [...s.completedCps], completed_exercise_ids: passedEx(s) ? [IDS.ex] : [], checkpoint_results: results,
    max_reachable_order: reach(s), state_version: s.version,
    progress: { media: { done: [1, 3, 5].filter((o) => o < cur || s.status === 'completed').length, total: 3 }, checkpoints: { done: s.completedCps.size, total: 3 }, labs: { done: passedEx(s) ? 1 : 0, total: 1 }, mastery: { best_exercise_score: bestScore(s), pass_mark: 80, lecture_completed: s.status === 'completed' } },
  };
}

const HINTS = ['Create a variable called student_name.', 'Use print(student_name).', 'Print the variable, not a new string.'];
function exerciseView(s: MockState) {
  return { id: IDS.ex, title: 'Print your name', instructions: 'Create a variable called student_name and print it.', language: 'python', starter_code: 'student_name = ""\nprint(student_name)\n', practice_mode: 'both', pass_threshold: 80, max_attempts: null, hints_total: 3, hint_penalty_percent: 10, hints_revealed: HINTS.slice(0, s.hintsShown), best_score: bestScore(s), attempts_used: s.submissions.length, draft: s.drafts[IDS.ex] ?? null, draft_stale: false, content_version: 1,
    objective: 'Create a text variable and print it.', constraints: 'Use a variable named student_name and print() once.', success_criteria: ['Your program prints a line of text', 'What you print matches student_name'],
    visible_examples: [{ description: 'Example', code: 'student_name = "Aarav"\nprint(student_name)', expected_output: 'Aarav' }], runtime: 'Python 3 — practice runs in your browser; official grading runs on the server',
    hints_policy: 'Hints are optional. Each one lowers that attempt\'s score by 10 points; it never lowers a score you already earned.', unlocked: reach(s) >= 6 };
}

function gradeOf(code: string, hints: number) {
  const hasVar = /student_name\s*=\s*['"][^'"]+['"]/.test(code);
  const prints = /print\(\s*student_name\s*\)/.test(code);
  const raw = (hasVar ? 50 : 0) + (prints ? 50 : 0);
  const score = Math.max(0, raw - hints * 10);
  return { raw, score, criteria: [{ label: 'student_name holds text', hidden: false, passed: hasVar, remediation: hasVar ? null : 'Create student_name = "Aarav".', objective: hasVar ? null : 'Store text in a variable', review_segment_id: hasVar ? null : SEG(3), review_title: hasVar ? null : 'Second concept' }, { label: 'Hidden check 1', hidden: true, passed: prints, remediation: prints ? null : 'Print the variable with print(student_name).', objective: prints ? null : 'Print output with print()', review_segment_id: prints ? null : SEG(5), review_title: prints ? null : 'Practical demonstration' }] };
}

const submissionView = (x: any) => ({
  submission_id: x.id, submission_number: x.number, status: x.status, score: x.score, raw_score: x.raw, max_score: 100, pass_threshold: 80, hints_used: x.hints, hint_penalty: x.hints * 10,
  passed_tests: x.criteria.filter((c: any) => c.passed).length, total_tests: 2, execution_ms: 12, feedback: ['error', 'expired'].includes(x.status) ? [{ kind: 'infrastructure', message: 'The grading service is unavailable. Your code was not judged. Please try again.' }] : [{ kind: x.status === 'passed' ? 'success' : 'failure', message: x.status === 'passed' ? 'All required tests passed.' : 'Some checks are not passed yet.' }],
  criteria: ['error', 'expired'].includes(x.status) ? [] : x.criteria, remediation: ['error', 'expired'].includes(x.status) ? [] : x.criteria.filter((c: any) => !c.passed && c.remediation).map((c: any) => ({ criterion: c.label, text: c.remediation, objective: c.objective, review_segment_id: c.review_segment_id, review_title: c.review_title })),
  infrastructure_error: ['error', 'expired', 'cancelled'].includes(x.status), created_at: new Date(x.at).toISOString(), content_version: 1, test_suite_version: 1,
});

const learners = Array.from({ length: 13 }, (_, i) => ({ id: i === 0 ? IDS.learner : `lrn-${i + 1}`, display_name: i === 0 ? 'Asha Rao' : `Learner ${String(i + 1).padStart(2, '0')}` }));

export function token(email: string, aal: 'aal1' | 'aal2' = 'aal1', factors: { id: string; factor_type: string; status: string }[] = []) {
  const b = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const exp = Math.floor(Date.now() / 1000) + 3600;
  const jwt = `${b({ alg: 'HS256', typ: 'JWT' })}.${b({ sub: IDS.learner, email, exp, role: 'authenticated', aal, amr: [{ method: 'password', timestamp: 1 }] })}.sig`;
  return { access_token: jwt, token_type: 'bearer', expires_in: 3600, expires_at: exp, refresh_token: 'refresh-mock', user: { id: IDS.learner, aud: 'authenticated', role: 'authenticated', email, app_metadata: {}, user_metadata: {}, created_at: new Date().toISOString(), factors } };
}

/** Pre-seeds a signed-in browser session (as supabase-js would store it). */
export async function signedIn(page: Page, email = 'learner1@neuromind.test', session = token(email)) {
  await page.addInitScript(([key, value]) => localStorage.setItem(key, value), ['sb-mock-auth-token', JSON.stringify(session)]);
}

export async function installMocks(page: Page, state: MockState) {
  // A healthy-but-slow media server: the request stays pending, so the player shows its normal loading state.
  await page.route('http://media.mock.test/**', (r) => (state.opts.videoFails ? r.abort() : undefined));
  await page.route('https://mock.supabase.test/**', async (r) => {
    const req = r.request();
    const url = new URL(req.url());
    if (req.method() === 'OPTIONS') return r.fulfill({ status: 204, headers: J });
    if (url.pathname.endsWith('/auth/v1/token')) {
      const body = req.postDataJSON?.() ?? {};
      if (url.searchParams.get('grant_type') === 'password') {
        if (body.password !== 'correct-password') return ok(r, { error: 'invalid_grant', error_description: 'Invalid login credentials' }, 400);
        return ok(r, token(body.email));
      }
      return ok(r, { error: 'invalid_grant' }, 400); // refresh fails
    }
    const userView = () => ({ ...token('learner1@neuromind.test').user, factors: state.ext.factors });
    if (url.pathname.endsWith('/auth/v1/user')) return ok(r, userView());
    if (url.pathname.endsWith('/auth/v1/signup')) { state.ext.signups.push(req.postDataJSON?.().email); return ok(r, { id: 'new', email: req.postDataJSON?.().email, identities: [] }); }
    if (url.pathname.endsWith('/auth/v1/resend')) { state.calls.push('POST /auth/v1/resend'); return ok(r, {}); }
    if (url.pathname.endsWith('/auth/v1/authorize')) { state.ext.oauth.push(url.searchParams.get('provider') ?? ''); return r.fulfill({ status: 200, headers: J, body: '{}' }); }
    if (url.pathname.endsWith('/auth/v1/factors') && req.method() === 'POST') { state.ext.factors.push({ id: 'f-new', factor_type: 'totp', status: 'unverified' }); return ok(r, { id: 'f-new', type: 'totp', totp: { qr_code: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', secret: 'JBSWY3DPEHPK3PXP', uri: 'otpauth://totp/x' } }); }
    const fm = url.pathname.match(/\/auth\/v1\/factors\/([^/]+)(?:\/(challenge|verify))?$/);
    if (fm && req.method() === 'DELETE') { state.ext.factors = state.ext.factors.filter((f) => f.id !== fm[1]); return ok(r, { id: fm[1] }); }
    if (fm && fm[2] === 'challenge') return ok(r, { id: 'ch-1', type: 'totp', expires_at: Math.floor(Date.now() / 1000) + 300 });
    if (fm && fm[2] === 'verify') {
      if (req.postDataJSON?.().code !== '123456') return ok(r, { code: 400, error_code: 'mfa_verification_failed', msg: 'Invalid TOTP code entered' }, 400);
      state.ext.factors = state.ext.factors.map((f) => (f.id === fm[1] ? { ...f, status: 'verified' } : f));
      return ok(r, token('learner1@neuromind.test', 'aal2', state.ext.factors));
    }
    if (url.pathname.endsWith('/auth/v1/recover')) { state.calls.push('POST /auth/v1/recover'); return r.fulfill({ status: 200, headers: J, body: '{}' }); }
    if (url.pathname.endsWith('/auth/v1/logout')) return r.fulfill({ status: 204, headers: J });
    return ok(r, {});
  });

  await page.route('http://api.mock.test/**', async (r) => {
    const req = r.request();
    const url = new URL(req.url());
    const path = url.pathname.replace('/api/v1', '');
    const m = req.method();
    if (m === 'OPTIONS') return r.fulfill({ status: 204, headers: J });
    state.calls.push(`${m} ${path}`);
    if (state.opts.apiDown401) return err(r, 401, 'UNAUTHENTICATED', 'Request could not be processed');
    const role = state.opts.role ?? 'learner';
    const body = () => (req.postDataJSON?.() ?? {}) as any;

    if (path === '/me') return ok(r, { id: IDS.learner, role, email: state.opts.email ?? 'learner1@neuromind.test', display_name: state.opts.name ?? 'Asha Rao' });
    if (path === '/me/dashboard') return ok(r, dashboardView(state));
    if (path === '/courses') return ok(r, { courses: state.opts.unenrolled ? [] : [{ id: IDS.course, slug: 'c', title: 'NeuroMind AI Foundations', description: 'A practical path from your first Python program to building AI systems.' }] });
    if (path === `/courses/${IDS.course}`) {
      const lec = { state: state.opts.lockedLecture ? 'locked' : state.status === 'completed' ? 'completed' : state.submissions.length && !passedEx(state) ? 'needs_attention' : state.started ? 'in_progress' : 'available', id: IDS.lecture, module_id: IDS.module, lecture_number: 9, title: 'Python setup, notebooks and the first program', summary: 'Set up Python, run a notebook cell and write your first program.', duration_seconds: 3600 };
      return ok(r, { id: IDS.course, slug: 'c', title: 'NeuroMind AI Foundations', description: 'A practical path from your first Python program to building AI systems.', lectures: [lec], modules: [{ id: IDS.module, module_number: 2, title: 'Python for AI', description: '', lectures: [lec] }] });
    }
    if (path === '/me/progress') return ok(r, { sessions: state.started ? [{ lecture_id: IDS.lecture, status: state.status, current_segment_id: state.current, completed_at: state.status === 'completed' ? new Date().toISOString() : null }] : [] });
    if (path === '/me/feedback') return ok(r, { feedback: state.feedback.filter((f) => f.published).map((f) => ({ ...f, created_at: new Date().toISOString() })) });
    if (path.startsWith(`/lectures/${IDS.lecture}`) && state.opts.lockedLecture) return err(r, 400, 'LECTURE_LOCKED', 'Complete the earlier lecture first to unlock this one.');
    if (path === `/lectures/${IDS.lecture}`) return ok(r, { estimated_minutes: 60, prerequisites: [], completion_criteria: ['Answer 3 knowledge checks (including the exit check).', 'Pass the practical lab with at least 80%.', 'Completion is confirmed by the server, not by finishing the videos.'], attempt_policy: 'You can practise as often as you like. Practice runs in your browser and never counts. Each official submission is saved, and your best valid score is kept.', id: IDS.lecture, lecture_number: 9, title: 'Python setup, notebooks and the first program', summary: '', learning_objectives: ['Set up Python', 'Run a notebook cell', 'Write a first program'], duration_seconds: 3600, content_version: 1, segments });
    if (path === `/lectures/${IDS.lecture}/session`) {
      if (m === 'GET') { state.started = true; return ok(r, sessionView(state)); }
      const b = body();
      if (b.state_version !== state.version) return err(r, 409, 'STALE_STATE', 'Lecture state changed elsewhere; reload and try again');
      const order = Number(String(b.current_segment_id).split('-')[1]);
      if (order > reach(state)) return err(r, 400, 'CHECKPOINT_REQUIRED', 'A required checkpoint must be completed first');
      state.current = b.current_segment_id; state.position = b.playback_position_seconds; state.version++; state.auditPatches++;
      return ok(r, sessionView(state));
    }
    if (path === `/lectures/${IDS.lecture}/complete`) {
      if (gates(state).some(([, d]) => !d)) return err(r, 400, 'REQUIREMENTS_NOT_MET', 'Required steps are not complete');
      state.status = 'completed'; return ok(r, sessionView(state));
    }
    const cpm = path.match(/^\/checkpoints\/(cp-\d)\/attempts$/);
    if (cpm && m === 'POST') {
      const b = body(); const cp = cpm[1];
      const need = { 'cp-1': 2, 'cp-2': 4, 'cp-3': 7 }[cp] as number;
      if (need > reach(state)) return err(r, 400, 'CHECKPOINT_REQUIRED', 'An earlier required checkpoint must be completed first');
      const correct = CORRECT[b.question_id] === b.selected_option_id;
      state.attempts.push({ cp, correct, at: Date.now() });
      if (cp !== IDS.cp3 || correct) state.completedCps.add(cp);
      return ok(r, { attempt_id: `a-${Date.now()}`, is_correct: correct, score: correct ? 1 : 0, explanation: correct ? EXPL.right : EXPL.wrong, checkpoint_completed: state.completedCps.has(cp), next_action: { type: 'next_segment' } });
    }
    if (path === `/exercises/${IDS.ex}`) { if (reach(state) < 6) return err(r, 400, 'CHECKPOINT_REQUIRED', 'Complete earlier required checkpoints first'); return ok(r, exerciseView(state)); }
    if (path === `/exercises/${IDS.ex}/hints`) { const b = body(); if (b.hint_index !== state.hintsShown) return err(r, 409, 'HINT_ORDER', 'Reveal hints in order'); state.hintsShown++; return ok(r, { hint_index: b.hint_index, text: HINTS[b.hint_index], hints_revealed: state.hintsShown, hints_total: 3, penalty_percent: state.hintsShown * 10 }); }
    if (path === `/exercises/${IDS.ex}/draft`) { if (state.opts.draftFails) return err(r, 503, 'DEPENDENCY_UNAVAILABLE', 'Request could not be processed'); state.drafts[IDS.ex] = body().source_code; return r.fulfill({ status: 204, headers: J }); }
    if (path === `/exercises/${IDS.ex}/submissions`) {
      if (m === 'GET') return ok(r, { submissions: state.submissions.map(submissionView), best_score: bestScore(state) });
      if (state.submissions.filter((x) => Date.now() - x.at < 60_000).length >= 6) return err(r, 429, 'RATE_LIMITED', "You're submitting very quickly. Wait a few seconds, then try again.");
      const code = body().source_code as string; const g = gradeOf(code, state.hintsShown);
      const crashed = /1\/0/.test(code);
      const status = state.opts.graderDown ? 'error' : state.opts.forceStatus ?? (crashed ? 'runtime_error' : g.score >= 80 ? 'passed' : 'failed');
      const unscored = state.opts.graderDown || state.opts.forceStatus === 'expired';
      state.submissions.push({ id: `s-${state.submissions.length + 1}`, number: state.submissions.length + 1, status, score: unscored ? null : crashed ? 0 : g.score, raw: g.raw, hints: state.hintsShown, criteria: g.criteria, at: Date.now() });
      state.hintsShown = 0;
      return ok(r, { submission_id: `s-${state.submissions.length}`, status: 'queued', status_url: '' }, 202);
    }
    const sm = path.match(/^\/submissions\/(s-\d+)$/);
    if (sm) { const x = state.submissions.find((s) => s.id === sm[1]); return x ? ok(r, submissionView(x)) : err(r, 404, 'NOT_FOUND', 'Request could not be processed'); }


    // ---- certificates, portfolio, announcements, issue reports ----
    if (path === '/me/certificates') return ok(r, { certificates: state.ext.certificates });
    if (path === '/me/announcements') return ok(r, { announcements: state.ext.announcements });
    if (path === '/me/portfolio' && m === 'GET') return ok(r, { items: state.ext.portfolio });
    if (path === '/me/portfolio' && m === 'POST') {
      const b = body(); if (!state.submissions.some((x) => x.id === b.submission_id && x.status === 'passed')) return err(r, 422, 'VALIDATION_ERROR', 'Only passed submissions can be added');
      state.ext.portfolio.push({ id: `pf-${state.ext.portfolio.length + 1}`, title: b.title, note: b.note ?? '', created_at: new Date().toISOString(), exercise: 'Print your name', score: 100, submission_id: b.submission_id, source_code: 'student_name = "Aarav"\nprint(student_name)\n' });
      return ok(r, { id: 'pf', already_added: false }, 201);
    }
    const pfm = path.match(/^\/me\/portfolio\/(pf-\d+)$/);
    if (pfm && m === 'DELETE') { state.ext.portfolio = state.ext.portfolio.filter((x) => x.id !== pfm[1]); return r.fulfill({ status: 204, headers: J }); }
    if (path === '/me/issues' && m === 'POST') { const b = body(); state.ext.reported.push({ category: b.category, message: b.message }); return ok(r, { id: 'i-9', reference: 'I9ABCDEF' }, 201); }
    if (path.startsWith('/certificates/verify/')) { const sr = path.split('/').pop(); return ok(r, sr === 'NM-2026-ABCD1234' ? { valid: true, serial: sr, course: 'NeuroMind AI Foundations', issued_at: '2026-10-14T00:00:00Z', holder: 'Asha R.' } : { valid: false }); }

    // ---- administrator ----
    if (path.startsWith('/admin')) {
      if (role !== 'admin') return err(r, 403, 'FORBIDDEN', 'Request could not be processed');
      const u = state.ext;
      if (path === '/admin/overview') return ok(r, { users: { learners: 1, teachers: 1, admins: 1, deactivated: u.users.filter((x) => x.deactivated).length }, content: { courses_published: 1, lectures_published: 1, lectures_total: 1 }, queue: { queued: 0, running: 0, oldest_queued_seconds: null }, grading_24h: { sample: 3, by_status: { passed: 2, failed: 1 }, queue_wait_seconds: { p50: 2.5, p95: 4.2, max: 5 }, execution_seconds: { p50: 1.1, p95: 2, max: 2.4 }, end_to_end_seconds: { p50: 4, p95: 6, max: 7 } }, dead_letters: u.deadLetters.length, open_issues: u.issues.filter((i) => i.status === 'open').length, health: { api: true, database: true, checked_at: new Date().toISOString() } });
      if (path === '/admin/users' && m === 'GET') {
        const q = (url.searchParams.get('q') ?? '').toLowerCase(); const rl = url.searchParams.get('role'); const st = url.searchParams.get('status');
        const rows = u.users.filter((x) => (!q || x.email.includes(q) || x.display_name.toLowerCase().includes(q)) && (!rl || x.role === rl) && (!st || x.deactivated === (st === 'deactivated')));
        return ok(r, { users: rows, total: rows.length, limit: 15, offset: 0 });
      }
      if (path === '/admin/users' && m === 'POST') { const b = body(); u.users.push({ id: `u-${u.users.length + 1}`, email: b.email, display_name: b.display_name, role: b.role, deactivated: false, last_sign_in_at: null, created_at: new Date().toISOString(), email_confirmed: true }); return ok(r, { id: 'u-new', email: b.email, role: b.role }, 201); }
      const um = path.match(/^\/admin\/users\/(u-\d+)\/(deactivate|reactivate|role)$/);
      if (um) { const t = u.users.find((x) => x.id === um[1]); if (!t) return err(r, 404, 'NOT_FOUND', 'x'); if (um[2] === 'role') t.role = body().role; else t.deactivated = um[2] === 'deactivate'; return ok(r, { user_id: t.id, active: !t.deactivated }); }
      if (path === '/admin/queue') return ok(r, { queue: { queued: 0, running: 0, oldest_queued_seconds: null }, grading_24h: { sample: 3, by_status: { passed: 3 }, queue_wait_seconds: { p50: 2.5, p95: 4.2, max: 5 }, execution_seconds: { p50: 1.1, p95: 2, max: 2.4 }, end_to_end_seconds: { p50: 4, p95: 6, max: 7 } }, dead_letters: u.deadLetters, procedure: 'Open the failure reason in the runbook, confirm the worker is healthy, then requeue.' });
      const rq = path.match(/^\/admin\/submissions\/(.+)\/requeue$/);
      if (rq) { u.requeued.push(rq[1]); u.deadLetters = u.deadLetters.filter((d) => d.submission_id !== rq[1]); return ok(r, { submission_id: rq[1], status: 'queued' }); }
      if (path === '/admin/audit') { const t = url.searchParams.get('event_type'); const ev = [{ id: 'a1', actor_id: 'u-3aaaaaaa', event_type: 'admin.user_created', resource_type: 'user', resource_id: 'u-1bbbbbbb', request_id: 'r1', metadata: { new_role: 'learner' }, created_at: '2026-10-14T05:00:00Z' }, { id: 'a2', actor_id: null, event_type: 'auth.denied', resource_type: 'route', resource_id: null, request_id: 'r2', metadata: { role: 'learner' }, created_at: '2026-10-14T04:00:00Z' }].filter((e) => !t || e.event_type === t); return ok(r, { events: ev, total: ev.length, limit: 25, offset: 0 }); }
      if (path === '/admin/courses') return ok(r, { courses: [{ id: IDS.course, title: 'NeuroMind AI Foundations', status: 'published', learners_enrolled: 1, lectures: [{ id: IDS.lecture, lecture_number: 9, title: 'Python setup', status: u.lectureStatus, content_version: 2, exercises: [{ id: IDS.ex, title: 'Print your name', status: 'published', test_suite_version: 1, pass_threshold: 80, max_attempts: null }] }] }], note: 'Published content is cached for up to 15 seconds.' });
      if (path === '/admin/content/packs/validate' || path === '/admin/content/packs/import') {
        const b = body(); const missing = (b.pack?.lab?.tests ?? []).map((t: { key: string }) => t.key).filter((k: string) => !(k in (b.tests ?? {})));
        const problems = b.pack?.title ? [] : ['title: Field required'];
        const valid = problems.length === 0 && missing.length === 0;
        if (path.endsWith('validate')) return ok(r, { valid, problems, missing_tests: missing, ...(b.pack?.title ? { summary: { lecture_number: b.pack.lecture_number, title: b.pack.title, segments: b.pack.segments.length, checkpoints: b.pack.checkpoints.length, lab_tests: b.pack.lab.tests.length } } : {}) });
        if (!valid) return err(r, 422, 'VALIDATION_ERROR', 'The pack is not valid');
        if (b.pack.lecture_number === 9 && !b.publish && !b.replace_published) return err(r, 409, 'CONFLICT', 'Lecture 9 is published. Importing as a draft would hide it from learners.');
        u.imports.push({ lecture_number: b.pack.lecture_number, publish: !!b.publish, replace: !!b.replace_published });
        return ok(r, { lecture_id: 'l-new', lecture_number: b.pack.lecture_number, status: b.publish ? 'published' : 'draft', created: true });
      }
      const ls = path.match(/^\/admin\/lectures\/(.+)\/status$/);
      if (ls) { u.lectureStatus = body().status; return ok(r, { lecture_id: ls[1], status: u.lectureStatus, previous_status: 'published' }); }
      if (path === '/admin/cohorts' && m === 'GET') return ok(r, { cohorts: u.cohorts });
      if (path === '/admin/cohorts' && m === 'POST') { const b = body(); u.cohorts.push({ id: `co-${u.cohorts.length + 1}`, course_id: b.course_id, name: b.name, learners: [], teachers: [] }); return ok(r, { id: `co-${u.cohorts.length}`, name: b.name }, 201); }
      const cm = path.match(/^\/admin\/cohorts\/(co-\d+)(?:\/(members|teachers)\/(u-\d+))?$/);
      if (cm) {
        const c = u.cohorts.find((x) => x.id === cm[1]); if (!c) return err(r, 404, 'NOT_FOUND', 'x');
        if (!cm[2]) { u.cohorts = u.cohorts.filter((x) => x !== c); return r.fulfill({ status: 204, headers: J }); }
        const person = u.users.find((x) => x.id === cm[3]); if (!person) return err(r, 404, 'NOT_FOUND', 'x');
        const list = cm[2] === 'members' ? c.learners : c.teachers;
        if (m === 'PUT') { if (!list.some((x) => x.id === person.id)) list.push({ id: person.id, display_name: person.display_name }); } else { const i = list.findIndex((x) => x.id === person.id); if (i >= 0) list.splice(i, 1); }
        return r.fulfill({ status: 204, headers: J });
      }
      if (path === '/admin/issues' && m === 'GET') { const st = url.searchParams.get('status') ?? 'open'; const rows = u.issues.filter((i) => st === 'any' || i.status === st); return ok(r, { issues: rows, total: rows.length, limit: 10, offset: 0 }); }
      const im = path.match(/^\/admin\/issues\/(i-\d+)$/);
      if (im && m === 'PATCH') { const i = u.issues.find((x) => x.id === im[1]); if (i) { i.status = body().status; i.admin_note = body().admin_note ?? null; } return ok(r, { id: im[1], status: body().status }); }
      if (path === '/admin/settings') return ok(r, { read_only: true, settings: [{ label: 'Grading mode', value: 'queue', note: 'queue = a private worker grades' }, { label: 'Submissions per learner per minute', value: '6', note: 'Rate limit' }] });
      return err(r, 404, 'NOT_FOUND', 'Request could not be processed');
    }

    // teacher
    if (path.startsWith('/teacher') && role === 'learner') return err(r, 403, 'FORBIDDEN', 'Request could not be processed');

    if (path === '/teacher/cohorts') return ok(r, { cohorts: [{ id: 'co-1', name: 'Autumn evening group', course_id: IDS.course, learners: 6, lectures_completed: 2, in_progress: 3, needs_support: 1 }] });
    if (path === '/teacher/announcements' && m === 'GET') return ok(r, { announcements: state.ext.teacherAnnouncements });
    if (path === '/teacher/announcements' && m === 'POST') { const b = body(); state.ext.teacherAnnouncements.push({ id: `an-${state.ext.teacherAnnouncements.length + 1}`, title: b.title, body: b.body, scope: b.scope, course_id: b.course_id, created_at: new Date().toISOString() }); return ok(r, { id: 'an' }, 201); }
    const anm = path.match(/^\/teacher\/announcements\/(an-\d+)$/);
    if (anm && m === 'DELETE') { state.ext.teacherAnnouncements = state.ext.teacherAnnouncements.filter((x) => x.id !== anm[1]); return r.fulfill({ status: 204, headers: J }); }
    if (path === '/teacher/reports/progress') {
      if (url.searchParams.get('format') === 'csv') return r.fulfill({ status: 200, headers: { ...J, 'content-type': 'text/csv', 'content-disposition': 'attachment; filename="progress-report.csv"' }, body: 'learner,lectures_completed\nAsha Rao,1\n' });
      return ok(r, { rows: [{ learner: 'Asha Rao', lectures_completed: 1, lectures_in_progress: 0, exercises_passed: 1, attempts: 3, average_best_score: 92.5, needs_support: false, last_active: '2026-10-13T09:00:00Z' }] });
    }
    if (path === '/teacher/summary') return ok(r, { assigned_learners: 13, lectures_completed: 4, lectures_in_progress: 6, submissions_passed: 9, submissions_needing_retry: 5, infrastructure_failures: 1 });
    if (path === '/teacher/learners') {
      const q = (url.searchParams.get('q') ?? '').toLowerCase(); const limit = Number(url.searchParams.get('limit') ?? 25); const offset = Number(url.searchParams.get('offset') ?? 0);
      const rows = learners.filter((l) => l.display_name.toLowerCase().includes(q));
      const ns = url.searchParams.get('needs_support') === 'true';
      const enriched = rows.map((l, i) => ({ ...l, lectures_completed: i === 0 ? 0 : i % 3 === 0 ? 1 : 0, lectures_in_progress: i === 0 ? 1 : 0, needs_support: i === 0, grader_problems: i === 0 ? 1 : 0, last_active: new Date().toISOString() })).filter((l) => !ns || l.needs_support);
      return ok(r, { learners: enriched.slice(offset, offset + limit), total: enriched.length, limit, offset });
    }
    if (path === '/teacher/analytics/exercises') return ok(r, { exercises: [{ exercise_id: IDS.ex, exercise: 'Print your name', attempts: 7, learners: 4, completion_rate: 50, average_score: 62.5, system_errors: 1, score_distribution: { below_50: 2, '50_to_79': 3, '80_and_above': 2 }, common_failures: [{ criterion: 'Hidden check 1', count: 4 }, { criterion: 'student_name holds text', count: 2 }] }] });
    if (path === '/teacher/content-status') return ok(r, { lectures: [{ id: IDS.lecture, lecture_number: 9, title: 'Python setup, notebooks and the first program', status: 'published', version: 1 }] });
    if (path === `/teacher/learners/${IDS.learner}/results`) {
      return ok(r, {
        learner: learners[0], sessions: [{ lecture_id: IDS.lecture, lecture: 'Lecture 9: Python setup, notebooks and the first program', status: 'in_progress', completed_at: null, last_seen_at: new Date().toISOString() }],
        checkpoint_attempts: [{ checkpoint_id: IDS.cp1, checkpoint: 'Knowledge check 1', is_correct: true, score: 1, submitted_at: new Date().toISOString() }],
        submissions: [{ submission_id: 's-1', exercise_id: IDS.ex, exercise: 'Print your name', number: 1, status: 'failed', score: 50, raw_score: 50, hints_used: 0, passed_tests: 1, total_tests: 2, infrastructure_failure: false, created_at: new Date().toISOString() }, { submission_id: 's-2', exercise_id: IDS.ex, exercise: 'Print your name', number: 2, status: 'error', score: null, raw_score: null, hints_used: 0, passed_tests: 0, total_tests: 0, infrastructure_failure: true, created_at: new Date().toISOString() }],
        best_scores: [{ exercise_id: IDS.ex, exercise: 'Print your name', best_score: 50 }],
        feedback: state.feedback.map((f) => ({ ...f, created_at: new Date().toISOString(), submission_id: null })),
      });
    }
    if (path === `/teacher/learners/${IDS.learner}/feedback` && m === 'POST') { const b = body(); state.feedback.push({ id: `f-${state.feedback.length}`, body: b.body, published: b.publish }); return ok(r, { id: 'f', published: b.publish }, 201); }
    if (path === '/teacher/submissions/s-1') {
      return ok(r, { submission_id: 's-1', exercise: 'Print your name', number: 1, status: 'failed', score: 50, raw_score: 50, max_score: 100, pass_threshold: 80, hints_used: 0, hint_penalty: 0, source_code: 'student_name = "Aarav"\nprint("hello")\n', criteria: [{ label: 'student_name holds text', hidden: false, passed: true }, { label: 'Hidden check 1', hidden: true, passed: false }], feedback_messages: [], execution_ms: 12, created_at: new Date().toISOString(), infrastructure_failure: false, evidence: { grader_version: '1.1.0', test_suite_version: 1, content_version: 1, correlation_id: 'req-abc123', started_at: new Date().toISOString(), finished_at: new Date().toISOString() } });
    }
    return err(r, 404, 'NOT_FOUND', 'Request could not be processed');
  });
}
