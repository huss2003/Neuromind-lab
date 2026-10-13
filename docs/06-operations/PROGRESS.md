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
Not done: T03 frontend shell, T05 auth/role guards, seed data, two-learner RLS tests.
Next: T03 frontend shell, then T05.
