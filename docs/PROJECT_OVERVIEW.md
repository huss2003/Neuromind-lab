# NeuroMind AI Learning Lab — What We Built, How It Works

Version of this document: 2026-10-13 · Repository: `huss2003/Neuromind-lab` · Branch: `claude/determined-bardeen-ip8pup`

**How to read the status marks.** ✅ built and covered by automated tests · 🟡 built but only partly, or tested only against fakes/mocks · ❌ not built · ⚠️ built but never verified in this environment.
This document describes the repository as it is. Where something was never run against the real system, it says so.

---

## 1. What the product is

NeuroMind Lab is a **data-driven learning platform for one sample lecture** (Lecture 9: "Python setup, notebooks and the first program"). The full course has 104 lectures, but the rule from the project brief is: *build one reusable lecture engine first, never 104 hand-made pages*. Every lecture is described by rows in a database; one player renders any of them.

A learner can:
1. Sign in and see the course and their next task.
2. Watch a lecture in short video sections.
3. Answer multiple-choice checkpoints and get an explanation.
4. Practise Python in the browser (private, unlimited).
5. Submit code for **official grading**, which is run by a separate sandboxed grader.
6. Get a score, per-requirement feedback, hints and targeted review if something fails, then retry.
7. Finish the lecture only when the **server** says the completion rules are met.

A teacher can see their assigned learners, who needs help, each learner's progress and attempts, the submitted code, and leave feedback.

An administrator can (through the API only) change roles and enrol learners.

---

## 2. System at a glance

```
 Browser (React + TypeScript, Vite)                       Vercel project "neuromind-lab"
   ├─ Supabase JS ──────────── sign-in / session token ──► Supabase Auth
   ├─ API client (zod-validated) ── Bearer token ────────► FastAPI service /api/v1      Vercel project "neuromind-lab-api"
   ├─ Pyodide in a Web Worker (private practice runs)         │
   └─ <video> player (HTML5 media events)                     ├─► Supabase Postgres (PostgREST, service role, RLS as 2nd defence)
                                                              └─► Grader service (private) ──► Docker sandbox (no network)
```

| Layer | Technology | Where it lives |
|---|---|---|
| Frontend | React, TypeScript (strict), Vite, React Router, TanStack Query, zod, Monaco editor (with plain-text fallback) | `frontend/` |
| API | Python, FastAPI, Pydantic | `backend/app/` |
| Auth + database | Supabase (Auth, Postgres, Row Level Security) | `database/` |
| Browser practice | Pyodide in a terminable Web Worker | `frontend/public/pyodide-worker.js`, `frontend/src/features/lab/` |
| Official grading | Separate FastAPI grader + Docker runner | `grader/` |
| Hosting | Two Vercel projects (frontend, API) deployed from GitHub | `frontend/vercel.json` |
| Tests | pytest, ruff, vitest, eslint, tsc, Playwright | `backend/tests`, `grader/tests`, `frontend/` |

Everything uses free plans. No Redis, paid queue, paid AI API or GPU is used.

---

## 3. Repository map

| Path | Contents |
|---|---|
| `README.md` | Run guide, test-suite table, Vercel notes |
| `CLAUDE.md`, `AGENTS.md` | Rules for AI coding sessions (small steps, honest reporting, no secrets, server-authoritative scoring) |
| `docs/01-product … 09-audit` | The planning pack (PRD, user stories, architecture, data model, API spec, security, tests, design system, wireframes, ADRs, glossary) plus our audits |
| `docs/06-operations/PROGRESS.md` | Session-by-session log: what was done, tests run, what is unverified |
| `docs/09-audit/` | `AUDIT_2026-10-13.md`, `DECISIONS_v1.md`, `UX_SPEC_CONFORMANCE.md` |
| `database/migrations/0001–0005` | Schema, grants, RLS, requirement and flow changes |
| `database/seed/001–004` | Lecture 9 sample content and later content fields |
| `database/tests/rls_two_learners.sql` | Script to re-check learner isolation on a dev project |
| `backend/app/` | API: `main.py`, `auth.py`, `errors.py`, `repository.py`, `grader_client.py`, `logging_setup.py`, `routers/`, `services/` |
| `grader/` | `grader_service/` (app, evaluate, runner), `sandbox/harness.py`, `Dockerfile` |
| `frontend/src/` | `services/`, `auth/`, `components/`, `features/lecture/`, `features/lab/`, `pages/`, `styles.css` |
| `frontend/ui-tests/`, `frontend/e2e/` | Mocked-network browser tests, and real-stack journey specs |
| `scripts/` | `create_dev_users.py`, `dev.sh` |
| `sample-content/` | Sample lecture material |

---

## 4. Features, in the order a learner meets them

### 4.1 Sign-in and account (screens S01, S02, S03, S17, S18)
- **Sign in** with email and password through Supabase Auth. Errors are generic ("check your email and password") and never reveal which part was wrong. Loading state, show/hide password. ✅
- **Account recovery** (`/recover`): asks for an email and always shows the same confirmation, so it cannot be used to discover who has an account. The email itself is sent by Supabase; delivery was never verified. 🟡⚠️
- **Welcome** (`/welcome`): how the lab works, browser requirements, acceptable use and privacy summary. It is a static page you can open any time; it is not forced on first login. 🟡
- **Profile**: name, email, role (role cannot be changed by the user), sign-out. Signing out clears all cached data so the next person never sees the previous user's data. ✅
- **Help** (`/help`): FAQ and a warning not to share secrets. There is **no report form** yet (needs a database table that needs your approval). 🟡
- **Session expiry**: if the token expires, the learner is sent to sign-in with an explanation, and saved progress is safe. ✅

### 4.2 Dashboard and course map (S04, S05, S06)
- **Dashboard**: a *Continue* card (the server picks the next task), module progress, recent attempts, and a remediation queue built from the last failed attempt. If the learner is not enrolled, a clear empty state is shown, not an error. ✅ No announcements (no data source). 🟡
- **Course map**: modules and lectures with order, duration, and a server-decided state: *locked, available, in progress, needs attention, grading pending, completed*. A locked lecture cannot be opened. No search/filter. 🟡
- **Lecture overview / orientation** ("Before you start"): objectives, prerequisites, estimated duration, completion rule, the practice policy, then a Start/Resume button. A short **intro section** follows. ✅
- Enrolment is required: a learner sees only courses they are enrolled in.

### 4.3 The lecture player (S07, S08, S09, S10)
- The lecture is a list of **segments** (intro, videos, checkpoints, practical, exit check). The player shows the current section, progress, and a stage stepper. ✅
- **Video**: HTML5 player; the section only counts as finished when the learner confirms/finishes it. A media failure shows a recoverable error and **never** marks anything complete. Captions and transcript are shown when provided; otherwise the page says they are unavailable. ✅
- **Checkpoint (MCQ)**: accessible radio choices, keyboard operable, no correct answer shown before submitting, validation when nothing is selected. After submitting: correct / "Not quite", an explanation, and Continue or Retry. Options can be shuffled by the server. ✅ The result does not repeat the selected answer back. 🟡
- **Resume**: leave and come back and you resume at the saved position. ✅
- **Seeking ahead** past a checkpoint is refused by the *server*, not only hidden in the UI. ✅
- **Outline**: a side list to jump to sections already reached. There is no Previous/Next button pair. 🟡
- **Practical video**: after it, the exercise opens automatically. ✅

### 4.4 The Python lab (S11)
- **Task panel**: objective, task, constraints, "you will pass when" criteria, visible examples, hint policy, pass mark. ✅
- **Editor**: Monaco, with a **simple text editor** fallback if Monaco cannot load. Tabs on small screens (task / code / output). ✅
- **Run practice** (browser only): runs in Pyodide inside a Web Worker. It is private, unlimited, and not graded. A run that takes too long terminates the worker and a fresh one loads. Output is bounded. ✅ (⚠️ Pyodide loads from a CDN that this environment cannot reach, so real execution was never exercised here.) There is **no Stop button**; the time limit ends a run. 🟡
- **Submit for grading**: clearly separate from Run. Explains it creates an official attempt. Disabled while in flight and idempotent on the server. ✅
- **Hints**: revealed in order, one at a time. Each hint used on the *current* attempt costs 10 points (default; the owner still has to confirm the formula). ✅
- **Reset to starter**: asks for confirmation before replacing code. ✅
- **Autosave**: debounced; the label says *Saving / All changes saved / Not saved yet*. "Saved" appears only after the server confirms. If the server cannot be reached, the draft is kept **on the device**, labelled as local-only, and restored after a refresh. An unsaved-work warning appears before leaving. ✅
- **Drafts carry a content version**: if the exercise was updated, the old draft is not loaded and the learner is told why. ✅

### 4.5 Official grading, results and recovery (S12, S13, S14, S15)
- **Submission status**: attempt number and a short reference, queued → running → result. No fake progress percentage. ✅ (Exercise version and submitted time are not shown on that panel. 🟡)
- **Result**: score, status, per-criterion results, bounded output, run time, best score, history, next action. Hidden tests are never shown. ✅
- **Status vocabulary**: *Queued, Running, Passed, Needs work, Runtime error, Time limit, System error — not your fault, Expired — not your fault, Cancelled*. Platform faults are explained as not the learner's mistake and **never lower the best score**. ✅
- **Scoring policy**: unlimited attempts with abuse limits (6 submissions a minute, 2 in flight; the API then answers 429 with plain-language text). **Best valid score** = highest score among passed/failed/runtime-error attempts. Pass mark is per exercise (80 in the seed). ✅
- **Remediation**: a failed criterion is mapped to a learning objective and to the section to review. "Replay section" takes the learner back and the code is kept. ✅
- **Attempt history** (`/exercises/:id/attempts`, linked from the lab): newest first, with time, result, score and tests passed, plus the best score. Feedback text and content version per row are not shown. 🟡
- **Completion**: the learner presses *Finish lecture* and the **server** checks every requirement before it records completion. The summary then shows what counted. ✅

### 4.6 Progress (S16)
"My progress" lists lectures with status and completion date, plus an explanation: *a lecture is complete only when the server has recorded every required section, the checkpoints, the exit check and a passing lab score; watching a video alone does not complete it*. No mastery-by-objective or trend charts yet. 🟡

### 4.7 Teacher workspace (T01, T04–T09)
- **Overview**: counts and learners needing support. 🟡
- **Roster**: search, "needs support" filter, server-side pagination ("Showing 1–1 of 1"). ✅
- **Learner detail**: progress, attempts, best score, evidence, feedback history. ✅
- **Submission review**: the code snapshot, status, criteria, grader/test/content versions, timing, and a feedback composer (visible to the learner or private). ✅
- **Analytics**: per-exercise attempts, completion and pass rate, most common failed criteria, system errors counted separately. 🟡
- **Content status**: read-only list of content and versions. Editing/publishing is not available and the page says so. 🟡
- **Scope**: a teacher sees only learners assigned to them. Anything outside that scope returns "not found" (404), not "forbidden", so existence is not leaked. ✅
- Named cohorts, assignable remediation, due dates: ❌ (decision needed).

### 4.8 Administration
Only API endpoints exist: change a user's role, enrol a learner in a course, assign a learner to a teacher. All are admin-only and audited. There is no admin UI, no queue/service health screen, no audit-log viewer. ❌

---

## 5. How it works, step by step

### 5.1 Identity and permissions
1. The browser signs in with Supabase and receives a JWT.
2. Every API call carries it as a Bearer token. The API validates it server-side and loads the user's **role from the database profile**, never from the request.
3. Role guards (`require_roles`) protect teacher/admin routes; a denial is written to the audit log.
4. Ownership and enrolment are checked on every learner operation. Teacher access is checked against the assignment table.
5. Row Level Security in Postgres is the second line of defence: the `anon` role has no table access, and `authenticated` is read-only under RLS. The API uses a server-only service-role key.

### 5.2 Opening a lecture
`GET /api/v1/lectures/{id}` returns a **manifest**: the ordered segments, which are reachable, checkpoints (questions without correct answers), and the exercise summary. It is built by `services/manifest.py` from the database. The frontend's pure state machine (`features/lecture/timeline.ts`) turns the manifest and the saved session into "what is on screen now". The state machine has its own unit tests and contains all timeline logic.

### 5.3 Saving progress
`PATCH /lectures/{id}/session` stores the current segment and position with a **state version** (optimistic concurrency). A stale version gets a conflict, so two tabs cannot silently overwrite each other. Gates (checkpoint, exit check, exercise) are enforced by `max_reachable_order`, computed on the server.

### 5.4 Answering a checkpoint
`POST /checkpoints/{id}/attempts` with the chosen option and an **idempotency key**. The server compares with the stored correct answer, saves the attempt, and returns correctness, explanation and next action. A repeated key returns the same result and creates no second attempt.

### 5.5 A graded submission, end to end
1. The learner presses *Submit for grading*. The browser creates an idempotency key and sends the code, key and the content version it saw.
2. The API checks: auth, enrolment, the exercise is unlocked, source size (50 000 bytes by default), content version matches, rate limits.
3. It **stores a queued attempt first** and returns `202` with the attempt id. Only then does grading start.
4. A background task sends the code and variable names to the **grader service** over HTTP with a shared secret.
5. The grader runs the learner's code in a **Docker container** with: no network, read-only filesystem, a small `tmpfs`, all capabilities dropped, `no-new-privileges`, non-root user, 128 MB memory and no swap, 1 CPU, 32 processes, file-size and open-file limits, and a hard timeout that also kills the container. Only the code and a list of variable names go in. No host mounts, no Docker socket, no environment secrets.
6. The sandbox harness prints the requested variable values and output, wrapped with a one-time nonce so learner output cannot forge a result.
7. **Hidden tests are evaluated on the host side** (in the grader process), not inside the sandbox, using the values the sandbox returned. The learner never receives the tests.
8. The result (per-criterion pass/fail, grader version, runtime error, timings) goes back to the API, which verifies it and stores it with evidence (grader, test-suite and content versions, correlation id).
9. The browser polls the attempt every 1–2 seconds until it is final. The learner can close the page and reopen the attempt later.
10. If the grader is unreachable, the attempt becomes *System error — not your fault*: no score penalty, retry allowed.

### 5.6 Scoring rules (server-authoritative)
Raw score comes from passed criteria. A hint penalty (10 points per hint used on that attempt) is subtracted. The client never sends a score, correctness, role or completion flag. The **best valid score** is kept separately from the latest attempt. Completion is recomputed by the server from stored facts.

### 5.7 Teacher feedback
`POST /teacher/learners/{id}/feedback` stores a note, optionally tied to a submission and optionally visible to the learner. The learner sees visible notes through `/me/feedback`. Every teacher action is attributed and timestamped.

### 5.8 Audit trail
Sensitive events (denied access, role change, enrolment, rate limiting, feedback) are written to `audit_logs` with a **fixed allow-list of metadata fields**. Code, passwords and tokens are not logged.

### 5.9 Errors
All API errors share one shape: a stable code, a plain-language message and a correlation id. The UI turns known codes into friendly text, offers *Try again*, and never shows stack traces. Logs are structured JSON without secrets.

---

## 6. API reference (all under `/api/v1`)

| Area | Endpoints |
|---|---|
| Health | `/health`, `/ready` (config and dependency check), `/me` |
| Content | `GET /courses`, `GET /courses/{id}`, `GET /lectures/{id}` |
| Session | `GET/PATCH /lectures/{id}/session`, `POST /lectures/{id}/complete`, `GET /me/progress`, `GET /me/dashboard`, `GET /me/feedback` |
| Checkpoints | `POST/GET /checkpoints/{id}/attempts` |
| Exercises | `GET /exercises/{id}`, `POST /exercises/{id}/hints`, `PUT /exercises/{id}/draft`, `POST/GET /exercises/{id}/submissions`, `GET /submissions/{id}` |
| Teacher | `/teacher/summary`, `/learners`, `/analytics/exercises`, `/content-status`, `/learners/{id}/results`, `/submissions/{id}`, `POST /learners/{id}/feedback` |
| Admin | `PATCH /admin/users/{id}/role`, `PUT …/enrollments/{learner}`, `PUT …/teachers/{teacher}/learners/{learner}` |

Contract details are in `docs/02-architecture/API_SPEC.md`.

---

## 7. Database

Migrations are numbered SQL files; nothing is changed by hand.

| Table | Purpose |
|---|---|
| `profiles` | user id, display name, role (created by a trigger on sign-up) |
| `courses`, `modules`, `lectures` | content hierarchy; lectures have prerequisites (JSON) |
| `lecture_segments` | ordered sections (type, media, settings, required) |
| `lecture_checkpoints`, `mcq_questions` | checkpoints, questions, options, explanations, shuffle/reveal policy |
| `lecture_exercises`, `exercise_tests` | exercise text, starter code, objectives, pass mark; hidden tests with remediation mapping |
| `enrollments` | which learner may see which course |
| `lecture_sessions`, `student_progress` | position, state version, status, completion |
| `checkpoint_attempts` | each MCQ attempt, with idempotency key |
| `lab_submissions` | each official attempt with status, score, criteria, evidence, idempotency key |
| `lab_drafts` | saved code drafts with content version |
| `exercise_hint_reveals` | which hints were revealed on which attempt |
| `teacher_assignments`, `teacher_feedback` | teacher scope and notes |
| `audit_logs` | allow-listed audit events |

Applied to the dev Supabase project: **0001–0004 and seeds 001–002.** **Not yet applied: `0005_flow_v1_b.sql` and seeds `003`, `004`.** Because enrolment is now required, learners will see no course until seed 003 is applied.

---

## 8. Frontend structure

- **`services/`**: `api.ts` (fetch wrapper, error mapping, correlation id), `lectureApi.ts` (all endpoints, zod-validated), `types.ts`, `supabase.ts`.
- **`auth/`**: `AuthProvider` (session, profile, sign-out cache clear, expiry event) and `RequireAuth` (role-aware route guard).
- **`features/lecture/`**: `timeline.ts` (pure reducer state machine), `LecturePage.tsx`, `Outline.tsx`.
- **`features/lab/`**: `ExerciseLab.tsx`, `usePyodide.ts`.
- **`components/`**: AppShell (skip link, responsive nav), Badge (icon + text, not colour only), ConfirmDialog (focus trap), McqCheckpoint, VideoSegment, Progress bars, SubmissionStatus, ReviewDialog, FeedbackForm, States (loading, skeleton, error, empty), Icon, LectureStatus.
- **`pages/`**: SignIn, Recover, Welcome, Home, CourseOverview, MyProgress, AttemptHistory, Profile, Help, NotFound, TeacherDashboard, TeacherLearner, TeacherSubmission. Teacher pages are lazy-loaded.
- **Design**: tokens in `styles.css` (colour, spacing, radius, focus ring), based on `docs/04-ui-ux/DESIGN_SYSTEM.md`. Visible focus, reduced-motion support, semantic HTML, labels on every control, status announced with `role="status"`/`alert`. Layout checked at 360, 390, 768, 1366 and 1440 px.

---

## 9. Security design

- Server-side identity, role, ownership, enrolment and teacher-scope checks on every protected route; 404 for out-of-scope resources.
- Client values for role, user id, score, correctness and completion are ignored.
- Learner code never runs in the API process. Official code runs only in the isolated container (section 5.5). Practice code runs in the learner's own browser worker.
- Hidden tests stay on the server side; the learner bundle contains no answers (correct options are not sent).
- Student output is rendered as text, never as HTML.
- Secrets: service-role key and grader secret are server-only; the frontend only has the public anon key. `.env` is not committed.
- Rate limits and size limits on submissions; idempotency on submissions and checkpoint answers.
- CORS restricted to the configured frontend origin.
- A startup check refuses to run with missing configuration.

**Known open security items (action needed from you):**
1. The **service-role key and dev passwords were pasted into chat**: rotate the key and update Vercel's `SUPABASE_SERVICE_ROLE_KEY`.
2. The repository is public and mentions the default dev password. Change or delete the dev accounts (`learner1-3`, `teacher`).
3. Supabase "leaked password protection" is off; sign-up policy has not been reviewed.
4. The sandbox was never run here (no Docker). Hostile-code probes (CPU loop, memory, output flood, process spawn, filesystem/network escape) were not performed. Do **not** call this production-secure.

---

## 10. Tests: what ran and what it proves

| Suite | Result at the last run | Proves | Does not prove |
|---|---|---|---|
| Backend `pytest` + `ruff` | 97 passed, lint clean | API rules against an in-memory repository: gating, scoring, hints, best score, idempotency, scope, audit, rate limits | queries against real Supabase |
| Grader `pytest` | 14 passed, 1 skipped (needs Docker) | harness and evaluation logic, the Docker flags (string level) | real sandbox isolation |
| Frontend `vitest`, `eslint`, `tsc` | 34 passed, clean | state machine and components | real browser layout |
| `pnpm test:ui` (Chromium, **network mocked**) | 34 of 35 passed in the full run; the 35th was fixed and re-run alone and passed | layout at 5 widths, full learner journey, fail → hint → retry, refresh/resume, server refusing early seeks, draft persistence, reset confirm, grader outage message, media failure, keyboard use, status not by colour only, session expiry, sign-out isolation, teacher scope and filters, new screens | the real backend, CDN-loaded editor/Pyodide, Docker |
| `pnpm e2e` (real stack) | specs written and type-checked; **never run** | — | — |

Not done at all: load/capacity tests, latency measurement, assistive-technology audit, backup-restore test, live RLS check of the new tables.

---

## 11. Deployment

- Two Vercel projects deployed from GitHub: `neuromind-lab` (frontend, ref root `frontend`, `vercel.json` rewrites all routes to the SPA) and `neuromind-lab-api` (FastAPI).
- Public frontend variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL`.
- Server variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CORS_ALLOWED_ORIGINS`, `GRADER_BASE_URL`, `GRADER_SHARED_SECRET`, size/time limits.
- **Hosted grading cannot work yet**: the grader needs Docker and is meant to stay private (never exposed to the internet). The hosted site therefore shows "system error — not your fault" for official submissions. Running locally with `scripts/dev.sh` (API :8000, grader 127.0.0.1:8010, frontend :5173) is the way to test grading.
- The live site currently runs an older commit. Redeploying the latest commit and applying migration 0005 / seeds 003–004 are still to do.

---

## 12. Local development

```bash
cp .env.example .env            # fill the Supabase and grader values
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
(cd frontend && pnpm install --frozen-lockfile)
# apply database/migrations/*.sql in order, then database/seed/*.sql
CONFIRM_DEV_PROJECT=yes backend/.venv/bin/python scripts/create_dev_users.py
docker build -t neuromind-grader-sandbox grader/
scripts/dev.sh
```
Checks: `ruff check . && pytest -q` (backend), `pytest -q` (grader), `pnpm lint && pnpm typecheck && pnpm test && pnpm build` (frontend), `pnpm test:ui`, `pnpm e2e`.

---

## 13. Decisions and the project's rules

Working rules (`CLAUDE.md`): one small task at a time; tests with each behaviour change; migrations for every schema change; server-authoritative score and completion; idempotent retries; no secrets in code; no paid services or scope growth without approval; report tests honestly.

Decisions recorded in `docs/09-audit/DECISIONS_v1.md` and still needing the owner: hint penalty formula; teacher cohort rules (named cohorts or assignments); retention of code, notes and logs; appeals (not enabled); real Lecture 9 content (current text is marked PLACEHOLDER); queue technology and hosting; manual score override policy; authoring and publishing workflow; a table for problem reports.

---

## 14. What is not built (on purpose or pending approval)

- Teacher/author **content editing, preview, validation and publishing** (T10–T14), content-issue queue (A06).
- **Named cohorts** and cohort analytics (T02/T03); assignable remediation.
- **Admin screens**: user management UI, queue and service health with p50/p95/p99, audit-log viewer (A01–A05).
- **Durable grading queue**: outbox, worker leases, retry with back-off and jitter, dead-letter, fair scheduling. Today grading is a background task; a crash can leave an attempt unfinished until it is expired.
- Load tests, latency targets, the 100-user capacity claim.
- Problem-report form, announcements, accessibility preferences, notification settings.
- AI tutor, RAG, agents, multi-file IDE/terminal, proctoring, portfolio sharing, the other 103 lectures.

---

## 15. Honest summary

| Area | State |
|---|---|
| One reusable, data-driven lecture engine with server-enforced gates | ✅ built, tested against fakes and mocked network |
| Learner flow (sign-in → lecture → checkpoints → lab → grading → remediation → completion) | ✅ tested in a mocked browser; ⚠️ not run against live services |
| Teacher evidence and feedback | ✅ same caveat |
| Safe official grading | 🟡 designed and unit-tested; sandbox never executed here |
| Hosted deployment | 🟡 deployed (older commit); official grading unavailable there; latest changes and DB migration pending |
| Production readiness, capacity, security certification | ❌ not claimed |
