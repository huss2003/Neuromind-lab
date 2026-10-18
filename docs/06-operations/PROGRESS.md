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

## Session 2026-10-13 (f) — Flow spec v1.0 + UX screens spec v1.0
- Backend (committed earlier): enrolment gating, lecture prerequisites/states, remediation mapping, richer exercise fields, status vocabulary. pytest 97 passed, ruff clean.
- Frontend: orientation screen, intro section, course map states, flow-spec exercise panel and statuses; plus, from the UX spec, new screens S02 `/recover`, S03 `/welcome`, S15 `/exercises/:id/attempts`, S18 `/help` (guidance only), progress-calculation explanation, skeleton component.
- Gap analysis against the UX spec: `docs/09-audit/UX_SPEC_CONFORMANCE.md` (what is built, partial, missing, and the five decisions needed).
- Tests run: eslint + tsc clean, vitest 34 passed, `pnpm test:ui` (Chromium, NETWORK MOCKED) 35 passed (34 in the full run + the one selector fix re-run singly).
- NOT yet applied to Supabase: migration 0005, seeds 003 and 004 (enrolments are now required, so learners see no course until they are applied). Vercel still serves the older commit until redeployed.
- Not built / unverified: see the conformance doc (authoring, cohorts, queue/outbox/leases, admin screens, load and latency measurement).

## Session 2026-10-13 (g) — Applied DB changes + redeploy
- Supabase (project `neuronetwrks`): applied migration `flow_v1_b` (0005) and the statements of seeds 003 and 004. Checked afterwards: 3 enrolments, Lecture 9 sections are intro, video, checkpoint, video, checkpoint, video, exercise, exit check; 3 tests carry objectives.
- Vercel: frontend `dpl_3nvm4toE…` and API `dpl_2UfvMwsr…` both READY at commit 1c97cec. The first API attempt failed with FASTAPI_ENTRYPOINT_NOT_FOUND until the root directory was set to `backend`.
- NOT verified: no request was made to either deployment (the fetch tool was denied and Bash cannot reach Vercel), so sign-in and the new screens on the live site are untested.

## Session 2026-10-13 (h) — Production-readiness pass (see docs/09-audit/PRODUCTION_READINESS_REPORT.md)
- Decision: **NO-GO** (Docker sandbox, real E2E, key rotation, content, load, a11y not done).
- Code: required-env dev password; secret scan + CI workflow; split-process grader harness + adversarial tests; DB-backed grading queue (migration 0006 **applied to the dev Supabase project and verified in a rolled-back transaction**), worker API (`/api/v1/internal/grader/*`), pull worker `grader/worker.py`, polling back-off.
- Tests: backend 109 passed; grader 31 passed, 1 skipped; frontend lint/tsc/vitest clean. UI suite not re-run after the polling edit.
- AWS (measured): Free plan, $100 credit, expires 2027-04-13, SCP denies EC2/ECS/SQS/Lambda/etc. Nothing provisioned. See AWS_COST_AND_RESOURCE_PLAN.md.
- Capacity claims (100/200 learners) remain **unmeasured**; do not quote either.
- New docs: ADR_HOSTED_GRADING, AWS_COST_AND_RESOURCE_PLAN, GRADER_THREAT_MODEL, E2E_LEARNER_JOURNEY, PRODUCTION_RELEASE_CHECKLIST, PRODUCTION_READINESS_REPORT.

## Session 2026-10-13 (i) — AWS worker deployed and drilled
- Owner approved AWS; budget $15/month created; EC2 worker (Sydney) running `grader/worker.py` via systemd; Vercel API now `GRADER_MODE=queue` (deployment `dpl_7gXhcdnb…`, commit b34d710).
- Real Docker sandbox tests 9/9 and adversarial 13/13 passed on the worker host; staging drills (auth, journey, restart, dead-letter) all passed. Details and caveats: PRODUCTION_READINESS_REPORT.md (update section).
- Owner decision: Supabase key and dev passwords are NOT being rotated (risk stays open).
- Created data: synthetic learner3 now has attempts/progress in the dev database.
- Resource inventory and cleanup: see AWS_COST_AND_RESOURCE_PLAN.md and the readiness report.

## Session 2026-10-13 (j) — Real content, UI v2, live E2E
- Placeholders removed (seed 005 applied via REST because large SQL calls timed out in the Supabase tool). UI v2 deployed. Frontend project fixed (root directory). Live browser E2E A/B/C and smoke passed.
- Fixed leaked sandbox processes (container deadline, die-with-parent, start-up sweep). Worker host updated and re-tested: 25 passed.
- Decision unchanged: NO-GO for real learners; see the update section at the end of PRODUCTION_READINESS_REPORT.md.

## Session 2026-10-13 (production push)
Done: load test (objectives fixed first, baseline 3 to 5 s, fixes: pooled upstream client, token cache, hnd1 region, concurrent reads, 15 s published-content cache, audit off request path; final run server p95 at most 473 ms, two client-side objectives narrowly missed, results in LOAD_TEST_PLAN); worker idle poll 5 s and concurrency 2 (burst grading p95 10.4 s); CloudWatch metrics, 4 alarms, SNS topic; backup/restore scripts, local DR rehearsal (19/19 tables), runbook; retention proposals; Lectures 10 to 12 applied to dev DB; live Monaco/Pyodide E2E passed; privacy/terms in axe scan; readiness report final update (CONDITIONAL GO, supervised pilot).
Tests run: backend 112 passed + ruff; grader worker tests passed; frontend lint/tsc/vitest 37; test:ui 38/38 (+ legal pages a11y re-run); live practice E2E and smoke passed. Not run: CI on GitHub (no main branch), 100-user load, screen reader audit.
Open: owner decisions on credentials (not rotated by choice), staging project, legal review, SNS e-mail confirmation, merging the working branch to `main`, more lectures.

## Session 2026-10-14 (b) — PR 5 merged, AWS verified, content pipeline
- PR 5 merged to `main` (CI green: secrets, grader incl. Docker tests, backend, frontend). Synthetic dev accounts: none remain (only the admin account exists; verified in the database).
- AWS verified with the connector: alarm forced to ALARM and the SNS notification action succeeded (owner confirmed email arrives); queue-wait/execution p95 metrics now published by the updated host script (old script kept as `.bak`); budget `neuromind-monthly-15usd` has 4 alerts; month-to-date cost $0. Credit balance: owner said to skip.
- Incident contacts set to the owner's email; alerts go to the same address.
- Branch protection could NOT be applied from this session (the GitHub proxy blocks settings writes). Owner must apply it: Settings > Branches > Add rule for `main`: require a pull request, require status checks `secrets`, `backend`, `grader`, `frontend` (up to date), no force pushes, no deletions.
- New: content pipeline (see PHASE7_CONTENT_PIPELINE_PLAN.md and CONTENT_PACK_GUIDE.md). Backend 151 passed (20 new), ruff clean. The import command was dry-run against production and correctly refused to unpublish lecture 10; nothing was written.
- **PENDING (owner): human screen-reader test (NVDA or VoiceOver) of the learner flow. Remind the owner at the end of the project. Not done.**
- Still open: policy details (placeholders stay until owner supplies them), admin password change (owner, later), Supabase key rotation (declined), staging (not possible on free plan), 100 more lectures (owner will upload later).

## Session 2026-10-14 (c) — Admin lecture import
- Built: admin API to validate/import lecture packs, repository `upsert_content` (allow-listed content tables only) and `set_content_status`, status change now cascades to questions and labs, Administration > Content "Import a lecture" screen, docs.
- Tests run: backend 160 passed, ruff clean; frontend lint, tsc, 37 unit; UI suite 59 (57 earlier + 2 new) — all passed after pointing Playwright at the installed Chromium (`PLAYWRIGHT_CHROMIUM_PATH`); first run failed only because the pinned Playwright expects a different browser build.
- Not run: live production test (not deployed yet: no deploy was requested); real Postgres upsert path (`upsert_content` is exercised only against the in-memory repository; first real use should be a draft import on production followed by a check).

## Session 2026-10-14 (d) — Deployed admin import and verified it live
- Deployed commit ceebaeb to production from the branch: API `dpl_2TcQnMAcyuQzxdN5ixkz519Qn1py` (hnd1) and frontend `dpl_7yKZ2QadJYRyNuBSukUFPQ1QC9bH`, both READY and aliased to the production domains. Database backup taken first (git-ignored `private/backups`).
- Live check with temporary accounts and a throwaway lecture 99, all 17 checks passed: validate accepts a good pack and reports a broken one; learner and teacher get 403 on import; import creates a draft (lecture, lab and questions all draft, no publish date, 8 sections, 3 tests with 1 hidden) and a second import updates the same rows; the draft is invisible to learners (not in the course map, 404 on open) but listed for the admin; a draft import over published lecture 10 is refused with 409 and lecture 10 is unchanged; hidden test definitions are not in any response or in the audit log; the audit event is recorded.
- Cleanup verified: throwaway lecture removed; the five temporary accounts deleted; only the admin account remains. The publish-cascade path (draft to published) was NOT exercised live, to avoid exposing a test lecture to learners; it is covered by backend tests only.
- Note: one audit row for the test import remains (counts and lecture number only).

## Session 2026-10-16/17 — Practical labs (platform + Block 1, lectures 9–24)
- Owner decisions recorded in docs/01-product/PRACTICAL_LABS_SPEC.md (predefined practice API, written/upload labs marked by teachers, exam lectures as auto-marked question sets, 3 bulb hints per cycle then Redo, test definitions visible to the admin, labs only for reached lectures, course document to be changed where it differs: docs/01-product/COURSE_DOCUMENT_CHANGE_NOTES.md).
- Built: migration 0009 (applied to production after a backup); grader harness with data files, probes, new check kinds, per-lab limits and the in-process practice API `labmock` (no internet, ever); sandbox image with numpy/pandas/matplotlib/scikit-learn/pillow/requests; backend labs listing, lab kinds, hint cycles and Redo, teacher review queue, admin test view, pack schema v2 importer with `--replace`, `course` and `export`; frontend Practical Labs section, lab page per kind, Pyodide runtime with packages/files/practice API and the browser quick check (byte-identical copy of the grader's `evaluate.py`), Save-and-check dialog (Dismiss / Show hint), bulb hints and Redo, teacher review screen, admin tests panel.
- Content: `content/course.json` (renamed course, 13 month-modules, 104 lecture records; 1–8 draft) and Block 1 packs 009–024 (9–12 full lectures with the document's projects replacing the old labs; 13–24 lab-only). `scripts/verify_labs.py`: 16 labs checked, 0 problems (solution passes, starter fails, hidden checks never inline).
- Tests run (this session's last state): backend 182 passed, ruff clean; grader 56 passed, 11 skipped (Docker-backed, run in CI); frontend lint, tsc, 37 unit, 68 UI (incl. axe) passed on commit 6060590/c8d87c8. Fixed today: the admin validate endpoint counted inline-defined visible checks as missing (now shares `missing_definitions` with the importer); a hidden check with an inline definition is now rejected by the validator; tests updated to the v2 packs (a v1-shaped fixture keeps score-mode coverage).
- NOT done yet: the EC2 worker still runs the previous image/harness, so official server grading of Block 1 labs fails until the host is updated (`git pull`, `docker build -t neuromind-grader-sandbox grader/`, restart `neuromind-worker`) — needs the AWS connector re-authenticated by the owner; browser quick checks work regardless. Block 1 not yet imported to production (import after deploy + backup). Blocks 2–6 pending.
- Stray: an empty `/lab` directory exists at the root of this development container (created by an early version of `nm_quickcheck` under CPython; harmless, could not be removed by the tool's safety check).

## Session 2026-10-17 — Block 1 live, Block 2 started, blueprint, live lab test
- Deployed API 86df129 and frontend 94a1664 to production. Backup taken, then lectures 9–24 imported as published (9–12 replaced, 13–24 lab-only).
- Blueprint written: docs/02-architecture/PRACTICAL_LABS_BLUEPRINT.md.
- Block 2: lectures 25–28 and 37–40 authored and verified (8 labs, 0 problems), committed, not yet imported. Lectures 29–36 still being authored.
- Bug found by the live test and fixed: pressing Save & check while Python was still loading skipped the browser check. It now waits. Unit test added (fails without the fix).
- Bug fixed: when the official checker fails, the popup now keeps the browser's findings.
- Live test against production (`frontend/e2e/labs.spec.ts`), 3 of 3 passed: catalogue and locks, browser check fails then passes, 3 hints then the 4th refused, Redo keeps history, numpy and the practice API run in the browser, teacher queue, admin sees all checks.
- NOT working: official server grading of the new labs. The EC2 worker still runs the old image: lecture 9 attempts end as "error", lectures 23–24 as "runtime_error" (no numpy/requests). Needs the host update, which needs the AWS connector re-authenticated. The full official journey (pass → lecture complete → next unlocks) is therefore not yet tested live.
- Temporary accounts learner1–3, teacher, admin @neuromind.test still exist for the remaining live test; delete them when it is done. learner3 has lectures 9–23 marked completed (test setup).
- Owner declined: deleting test learners' rows and running a worker without Docker from the dev container.

## Session 2026-10-17 (b) — Full test pass
- Automated suites, all green: secret scan; ruff; 24 packs validated and verified (0 problems; 16 more for lectures 29–36 verified separately); backend 182; grader 56 (11 Docker tests skipped locally, run in CI); frontend lint, typecheck, 41 unit, build; mocked UI + accessibility 69.
- Live against production: smoke, titles, browser practice, access control (lecture C), practical labs (3), admin workspace, cohorts, issue reports, two-step verification — all passed after fixes.
- Bug found live and fixed (1dee6bf, deployed): after the 3rd hint the Redo button did not appear until a reload. UI test added (fails without the fix).
- Test-data fixes: live specs now use unique cohort and account names per run.
- Still failing, as expected: lecture A and B live tests (they need an official verdict). The EC2 grader still runs the old image: new-lab attempts end as "error" or "runtime_error". AWS connector credentials remain expired.
- Not run: the extras "journey" test (it archives published lectures 10–12 in production during the run).
- Temporary accounts still in production: learner1–3, teacher, admin and two zed.* accounts @neuromind.test. Delete them after the official-grading test.

## Session 2026-10-17 (c) — Self-hosted grader (replaces the AWS host)
- Phase 1 report given to the owner (grading flow traced in code; old AWS image is the cause; the old grader records missing libraries as the learner's runtime_error, which breaks the "infrastructure fault is not a learner failure" rule).
- Owner's machine: Hussain-PC, Windows, i7-12700F, 16 GB, Wi-Fi, UPS; load about 5 learners at once; must be portable to another server.
- Built: design doc docs/06-operations/SELF_HOSTED_GRADER.md; capability handshake (worker measures its sandbox at start-up; the API refuses jobs to workers without harness v2 and all six lab packages, before claiming, so the job stays queued); gVisor runtime option (GRADER_RUNTIME=runsc|runc, validated); pinned sandbox runtime (Python 3.13 + requirements-sandbox.lock = the versions all labs were verified with); verify_labs --sandbox; portable installer, verify and update scripts (infra/selfhost), WSL hardening file; CI job grader-gvisor.
- New isolation tests: home-network/private ranges, Docker host, API and Supabase unreachable; only loopback interface; no files shared between jobs; hidden expected answer never visible; lab libraries work; practice API works while real hosts stay blocked.
- Tests run here: backend 183 passed; grader 65 passed, 16 skipped (Docker tests need Docker: they run in CI and on the machine); verify_labs 32 labs, 0 problems (full and partial modes). Docker/gVisor tests NOT run in this environment.
- Not done: the API change is not deployed yet (deploying it stops the old AWS worker from taking jobs); VM not installed (owner); token rotation and cut-over pending.

## Session 2026-10-17/18 (d) — Grader cut-over: GitHub Actions backup, then Hussain-PC (WSL2)
- Hyper-V could not be enabled (Windows component store corruption); VM plan dropped. Disk on C: freed from 8.7 GB to ~80 GB.
- Added `.github/workflows/grader-worker.yml` (same Docker + gVisor sandbox, ~5 h 40 min runs chained by schedule) as an interim/backup host; design doc §14 lists the GitHub-terms risk the owner accepted.
- Production deployed from the branch (API and frontend). New worker token set in Vercel, the GitHub secret and the PC grader; the old AWS worker can no longer authenticate. API redeployed after the rotation; health ok.
- Grader now runs in dedicated WSL2 distro `NeuroMind-Grader` (design doc §15): sealed `wsl.conf`, `install.sh` + `verify.sh` ALL CHECKS PASSED (runsc; 78 passed, 3 skipped; 32 labs graded, PARTIAL for hidden checks); service active, no refusal; Windows keep-alive task installed.
- Local test run on Windows: backend 183 passed; grader suite fails on Windows (POSIX-only harness), passes in CI and in the WSL grader.
- **Not done:** live production journey (nobody has the temporary users' password: reset it in Supabase or run an API-level check); lecture 25–40 import (hidden checks now in local `private/`); stopping EC2; deleting temporary accounts; PR 6 description; merge (needs owner approval).
- **Live production grading proven on 2026-10-18 (06:47 UTC):** two lecture-9 attempts queued for the temporary learner3 directly in `lab_submissions` (as the API would; the service key is not retrievable from Vercel, so the Supabase connector was used). The Hussain-PC grader (WSL, gVisor) claimed both: wrong code `failed` 33.33 (2/6 checks), right code `passed` 100 (6/6, incl. 1 hidden) in 4.1 s and 5.1 s end to end, ~0.3 s execution each; `submission.finished` audit events written; the PC's Docker log shows both sandbox containers. The GitHub Actions run active at the time held the pre-rotation token and could not claim. Not covered: the browser path (sign-in, Save & check button, lecture unlock): needs the test users' password.
