# Project Memory — NeuroMind AI Learning Lab
Last updated: 2026-10-13 | Phase: pre-implementation planning

## Objective
Build a data-driven lecture player and coding lab, validate one sample lecture, then expand to the 104-lecture course.

## Confirmed decisions
- Solo developer using AI tools.
- Free/local prototype first; no paid services without approval.
- React/TypeScript + Cloudflare Pages Free.
- FastAPI local or Render Free preview.
- Supabase Free Auth/Postgres.
- Segmented video Approach B.
- Test Google Drive for source/playback; use HTML5-compatible media events for reliable transitions, potentially R2 for sample assets.
- Both execution modes: Pyodide practice and local Docker official grader.
- Grader remains local/private; never expose Docker publicly.
- Lecture 9 recommended sample.
- 100 concurrent learner sessions is a future target, not a current guarantee.

## Status
PRD, user stories, architecture, data model, API, AI rules, UI flows, wireframes, security, testing, NFR, edge cases, environment, deployment, implementation plan, ADRs and references are drafted in this pack.
Application code: started (2026-10-13): API shell (T04), initial schema + RLS (T06) applied to Supabase project `neuronetwrks`. Video recording: not started. Boss demo: not started.

## Open risks/decisions
1. Verify dependency versions together before install.
2. Confirm repository name, OS and Docker availability.
3. Test Drive player events vs R2/HTML5 playback.
4. Define code submission retention before real learner use.
5. Verify free-plan quotas and billing controls.
6. Keep local grader private.
7. Review published-content versioning before implementing editing.

## Next task
T00: review pack, confirm constraints/accounts and verify runtime pins. Then T01/T02. Do not build all screens at once.

## Session update template
Date / Task / Summary / Files changed / Tests run and results / Decisions / Open issues / Next task.

## Session 2026-10-13
Task: import pack; T02 skeleton (partial); T04 API shell; T06 migrations/RLS applied to Supabase `neuronetwrks` (ddiwlgbllhwcdykqjfne).
Tests: backend pytest 2 passed; ruff clean. Supabase security advisors: only intentional INFO (API-only tables) after revoking handle_new_user execute.
Also done: T03 frontend shell (routes, sign-in page, loading/error/not-found states; vitest 3 passed, eslint+tsc clean, build ok), T05 backend auth (token verification, /me, role guard; pytest 5 passed). Note: installed pnpm is 10.28.0, not the 9.15.4 pin.
Not done: live sign-in test against Supabase (needs service-role key in .env), seed data, two-learner RLS tests.
Next: T07 course/lecture APIs, then T06 seed + RLS tests.

## Session 2026-10-13 (b)
Tasks: T06 (seed + RLS verification), T07 (course/lecture APIs).
- Seed `database/seed/001_lecture9_sample.sql` (repeatable, `on conflict do nothing`) applied to dev Supabase: 1 course, 1 module, Lecture 9, 3 questions, 3 checkpoints (2 MCQ + exit check), 1 exercise with 3 tests (1 hidden), 7 segments. ALL CONTENT IS PLACEHOLDER; video is a CC0 MDN sample mp4 (external, supports range requests).
- RLS two-user test `database/tests/rls_two_learners.sql` run on dev DB (rolled back): other learner sees 0 sessions/0 submissions, only own profile, published content visible, mcq_questions and exercise_tests invisible (0 rows), self role-escalation updates 0 rows, direct attempt insert denied. A teacher-scoped RLS case is not yet tested (teacher access is server-side via API).
- API: GET /courses, /courses/{id}, /lectures/{id} (learner-safe manifest; no answer keys). Practical->exercise link is explicit via segment `settings.on_end` (documented here; schema unchanged). Malformed/unknown ids -> 404; broken content config -> 500 (never silent completion).
- Tests: backend pytest 10 passed, ruff clean. Not run against live PostgREST (service-role key not available in this environment): PostgrestRepository is unverified.
- Doc conflict/gap: the pack has no curriculum document, so Lecture 9 learning objectives are placeholders; title comes from API_SPEC. Docs live under docs/ (the prompt's paths omit this prefix); PROGRESS.md is docs/06-operations/PROGRESS.md.
- Next: T08 lecture session API (create/load/PATCH with state_version), then T09 player.

## Session 2026-10-13 (c) — vertical slice implemented
Tasks: T08 session API, T10-T13 checkpoint rules/MCQ scoring/results, T14-T15 Monaco + Pyodide worker, T16 grader service, T17-T18 submissions/feedback/retry, T19-T20 practical transition + completion, T23 teacher results (basic), T24 Lecture 9 seed (earlier), E2E specs written.
### Environment limits in this cloud container (why some items are UNVERIFIED)
- Egress policy blocks `ddiwlgbllhwcdykqjfne.supabase.co`, so the API could not be run against the live Supabase project from here. `PostgrestRepository` has never executed against real PostgREST.
- No Docker daemon here, so the Docker sandbox runner, `docker build`, and the real-Docker test were never executed.
- No localhost access for the user from this container: the app must be run on the user's machine (README).
### Tests actually run (all in this container)
- backend: `ruff check` clean; `pytest` 36 passed (in-memory repository + fake grader; covers 401/403/404, checkpoint bypass, seek-ahead, score tampering, answer-key/hidden-test non-disclosure, idempotency 200/409, stale state 409, attempt limits, infra error not a learner failure, cross-user access, teacher scoping, completion rules).
- grader: `pytest` 12 passed, 1 skipped (real Docker). Harness+evaluation verified via a NON-isolated subprocess test runner (pass, fail, runtime error, syntax error, infinite loop timeout, output truncation). Docker flags are asserted by string (`--network none`, `--read-only`, `--cap-drop=ALL`, `--pids-limit`, memory/cpu, non-root, no mounts/env) but NOT executed.
- frontend: eslint clean, `tsc` clean, vitest 23 passed (timeline state machine 13, MCQ 4, video fallbacks 2, routing/guards 3, sign-in 1), `vite build` ok, Playwright smoke 3 passed in real Chromium (sign-in redirect, skip link/focus, 404, teacher guard, no overflow at 360px).
- Real server smoke: uvicorn started; `/health` ok, `/courses` without token -> 401 structured error, CORS allows only the configured origin.
- NOT run: E2E journeys A-E (`frontend/e2e/lecture.spec.ts`; typechecked only), live Supabase auth/RLS-through-API, Docker grading, Pyodide in a browser (loads from jsDelivr; blocked here), Monaco loading, real video playback, 100-user/grading load tests.
### Decisions / deviations
- Python 3.13 and pnpm 10.28 used instead of pinned 3.12 / 9.15.4; frontend pins follow the doc except `@monaco-editor/react 4.7.0` (4.6.0 lacks React 19 peer support), eslint plugins pinned to versions compatible with ESLint 9.19.
- Grader design: only variable NAMES and student code enter the container; test definitions (incl. hidden) stay on the host and are evaluated against captured stdout/variables. Known limitation: hostile code could try to forge the harness result line (nonce-protected but same process); the container protects the host, not grade integrity. Needs the security review (T27).
- Additive API endpoints documented in API_SPEC.md (need approval).
### Outstanding / open
1. Run the stack locally and fix whatever the first real run reveals (most likely areas: PostgREST filter syntax, Supabase `/auth/v1/user` check, Monaco/Pyodide CDN loading).
2. Teacher scope (course assignment) and teacher authoring screens (T21-T22) not built.
3. Audit-log writes for denied actions not implemented; no rate limiting yet; student_progress recompute only on completion.
4. Replace placeholder content/videos; supply real Lecture 9 objectives.
5. T26 (E2E fail/retry/resume), T27 security review, T28 preview deployment, T29 demo pack, T32 load tests.
### Next
Run `scripts/dev.sh` locally per README, then `pnpm e2e`; report failures back for fixing.

## Session 2026-10-13 (d) — Deployment + audit
- Deployed to Vercel (projects `neuromind-lab`, `neuromind-lab-api`) from branch commit b533f79 via the Vercel connector; both READY. Not browser-verified (network blocked here).
- Dev users created in Supabase via SQL (learner1-3, teacher). Public repo + default dev password: see audit F-01.
- Audit against Requirements v1.0: `docs/09-audit/AUDIT_2026-10-13.md`. No application code changed. Next: rotate credentials, run local E2E, owner decisions F-09/F-10/F-12.

## Session 2026-10-13 (e) — Requirements v1.0 implementation + UI/UX rebuild
Built (MVP scope §2.1 plus audit gaps; see docs/09-audit/DECISIONS_v1.md):
- DB migration 0003 applied to dev Supabase + seed 002: evidence/version columns, hints, remediation text, `lab_drafts`, `exercise_hint_reveals`, `teacher_assignments`, `teacher_feedback`, grant hardening (anon has no table access; authenticated is read-only under RLS).
- API: unlimited attempts + abuse limits (429), best valid score, hints with per-attempt penalty, per-criterion results + remediation, evidence persisted (grader/test-suite/content versions, correlation id, timings), drafts autosave, progress breakdown (media/checkpoints/labs/mastery), course modules, teacher scope via assignments (404 for out of scope), teacher summary/search/pagination/evidence/feedback, audit events (allow-listed metadata), JSON logs, `/ready`, startup config check.
- Grader: per-criterion results and grader_version.
- Frontend: full redesign (design tokens, app shell, dashboard, course/module view, my progress, profile, stage stepper, separate progress bars, accessible MCQ, lab with tabs on small screens, hints, reset-with-confirm, autosave + unsaved warning, stdout/stderr panes, result/remediation/attempt history, completion summary, teacher dashboard/learner/submission evidence/feedback, sign-out cache clearing, expired-session redirect, lazy-loaded routes).
### Tests actually run in this environment
- backend: ruff clean, pytest 58 passed.  grader: pytest 14 passed, 1 skipped (Docker).
- frontend: eslint + tsc clean, vitest 29 passed, vite build ok, e2e specs typecheck.
- `pnpm test:ui` (real Chromium, built app, NETWORK MOCKED): 23 passed — overflow check on 9 screens at 360/390/768/1366/1440, full learner journey, fail/hint/retry, refresh/resume + seek refusal, draft persistence, reset confirm, grader outage, media failure, keyboard, non-colour status, expired session, sign-out isolation, teacher scope UI. These found and fixed two real defects: abs-positioned visually-hidden table text caused page-wide horizontal scroll; one-column grids needed minmax(0,1fr).
### Still unverified (no network/Docker/CDN here)
Live Supabase + PostgREST repository, real sign-in of the SQL-created users, hosted API behaviour, Docker sandbox, Pyodide and Monaco CDN loading, real video playback, `pnpm e2e`, load/capacity, accessibility audit with assistive tech.
### Not built (needs owner approval per requirements §2.2/§10/§21)
AI Tutor/RAG/agents, authoring/lab-lifecycle UI, multi-file IDE/terminal, appeals, proctoring, password reset, retention/privacy policy, load certification of 200 learners.
### Open decisions
Hint formula, teacher cohort rules, retention, appeals eligibility, real Lecture 9 content/objectives, free-tier limits.
