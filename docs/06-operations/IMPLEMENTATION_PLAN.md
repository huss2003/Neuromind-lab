# Ordered Implementation Plan
One task at a time. Recommended sample: Lecture 9. Each task must be independently tested.

## Phase 0 — Baseline
**T00 Review pack:** confirm scope, OS, accounts, Docker and open decisions. Pass: owner baseline confirmed and PROGRESS updated.
**T01 Verify versions:** test runtime/package compatibility, pin exact versions, build minimal frontend/API. Pass: install/build/tests work and lockfiles committed.

## Phase 1 — Foundation
**T02 Repository skeleton:** frontend/backend/grader/database/sample-content, gitignore, env example, tests. Pass: clean checkout installs; no secrets.
**T03 Frontend shell:** routes, app shell, loading/error/not-found states. Pass: lint/typecheck/tests.
**T04 API shell:** FastAPI health, request IDs, CORS, structured errors. Pass: API tests.
**T05 Auth:** Supabase sign-in, token verification, role guards. Pass: 401/403 tests; no service key in browser.

## Phase 2 — Data
**T06 Migrations/RLS:** tables, constraints, indexes, seed. Pass: clean migration and two-learner RLS tests.
**T07 Course/lecture APIs:** published course list and safe manifest. Pass: no hidden answers/tests returned.

## Phase 3 — Player
**T08 Session API/UI:** create/load/save session and resume. Pass: refresh restores state.
**T09 Segmented media player:** ordered HTML5 segments, retry/fallback; test Drive and R2 separately. Pass: end advances once; media failure doesn't complete.
**T10 Checkpoint state machine:** required pause and no bypass. Pass: refresh/seek cannot bypass.

## Phase 4 — MCQ
**T11 MCQ UI:** question/options/loading/result. Pass: keyboard tests and no answer key pre-submit.
**T12 Scoring API:** validate, score, persist, idempotency. Pass: correct/incorrect/invalid/duplicate tests.
**T13 Result/resume:** explanation and server-confirmed continuation. Pass: network failure doesn't unlock next segment.

## Phase 5 — Coding
**T14 Monaco:** editor, starter code, output. Pass: works at desktop target.
**T15 Pyodide:** browser worker, stdout/stderr, timeout/output limit. Pass: basic run and infinite-loop termination.
**T16 Local Docker worker:** protocol, temp workspace, limits, no network/secrets/host mounts. Pass: pass/fail/timeout/cleanup tests and security review.
**T17 Submission API:** submission records, worker adapter, status/result endpoint. Pass: idempotent lifecycle; worker outage is infrastructure error.
**T18 Feedback/retry:** result panel, attempt history, retry policy. Pass: fail then pass works and completion updates once.

## Phase 6 — Completion
**T19 Practical transition:** link practical segment to exercise, `ended` event and accessible fallback. Pass: correct exercise opens once.
**T20 Lecture completion:** exit check and server validation. Pass: prerequisites enforced; refresh preserves completion.

## Phase 7 — Teacher
**T21 Lecture/segment editor:** draft, order, references, validation. Pass: invalid sequence cannot publish.
**T22 Question/exercise editor:** tests, thresholds, versioning. Pass: hidden tests protected and content validated.
**T23 Teacher results:** scoped learner progress/results. Pass: learner cannot access teacher data.

## Phase 8 — Demonstration
**T24 Configure sample Lecture 9:** placeholder segments, two MCQs, practical video, exercise and tests. Pass: data validation.
**T25 E2E happy path:** sign-in through completion. Pass: repeatable.
**T26 E2E fail/retry/resume:** wrong answer/code, retry, refresh, worker outage. Pass: no bypass/false success.
**T27 Security review:** IDOR, role escalation, hidden data, RLS, limits. Pass: no known critical/high issue for controlled demo.
**T28 Preview deployment:** free plans, CORS, secrets, media. Pass: works with demo data; grader remains private.
**T29 Boss demo pack:** walkthrough and honest limitations/cost/upgrade path. Pass: implemented vs placeholder is clear.

## Phase 9 — After approval
**T30 Populate remaining lecture data** in batches and validate each.
**T31 Design hosted production grading** after threat model and budget approval.
**T32 Load test** 100 sessions separately from 10/25/50/100 grading jobs; document p50/p95, errors, CPU/RAM, queue wait and cost.

Do not ask AI to implement multiple phases at once.
