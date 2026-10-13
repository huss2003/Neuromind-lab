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
