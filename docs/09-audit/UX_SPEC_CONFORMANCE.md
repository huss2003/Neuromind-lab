# Conformance to "Student & Teacher UX Screens and System Performance Spec v1.0"

Date: 2026-10-13. Basis: reading the code and running the network-mocked browser tests. Nothing here was measured against the live stack. Legend: ✅ built and covered by a test · 🟡 partly built · ❌ not built · 🔒 not built on purpose, needs an owner decision or infrastructure.

**Short answer: the learner journey (S01–S15) is largely there; the teacher and admin screens and the whole queue/performance layer are not "exactly like" the spec.**

## Student screens

| ID | Status | Notes |
|---|---|---|
| S01 Sign in | ✅ | Generic error, loading, show/hide password, recovery link. No terms/privacy links (no documents exist). |
| S02 Account recovery | ✅ (UI) | Same confirmation whether or not the account exists. Email delivery depends on Supabase mail settings and is unverified. |
| S03 Onboarding | 🟡 | `/welcome` walkthrough, requirements, acceptable use. Not shown automatically on first login; enrolment status not on the page. Retention wording is "to be confirmed". |
| S04 Dashboard | 🟡 | Continue, module progress, recent attempts, remediation, empty/error states. No announcements (no data source). |
| S05 Course map | 🟡 | Order, duration, server-decided status, prerequisites, locked lectures. No search/filter. |
| S06 Lecture overview | ✅ | Objectives, prerequisites, duration, completion rule, Start/Resume. |
| S07 Lesson player | 🟡 | Section progress, resume, captions/transcript, checkpoint and lab gating. No explicit Previous button (outline navigation only); no "report content issue" (no backend). |
| S08 MCQ checkpoint | ✅ | Keyboard operable; answer not revealed before submit. |
| S09 Checkpoint result | 🟡 | Result, explanation, retry/continue. Does not echo the selected answer. |
| S10 Practical demo | 🟡 | Video then the linked exercise opens. Setup notes are minimal. |
| S11 Python lab | 🟡 | Task, objective, constraints, starter code, Monaco + plain-text fallback, Run vs Submit, reset with confirmation, hints, draft status, limits. **No Stop button**: runs end by the time limit that terminates the worker. |
| S12 Submission status | 🟡 | Attempt number, short reference, queued/running, never a fake percentage. Exercise version and submitted time are not on that panel. |
| S13 Grading result | ✅ | Score, status, criteria, bounded output, best score, history, next action; no hidden-test data. |
| S14 Remediation | ✅ | Failed objective in plain language, replay the section, return to the task. |
| S15 Attempt history | ✅ (new) | `/exercises/:id/attempts`, linked from the lab. Does not show feedback text or content version per row. |
| S16 Progress/skills | 🟡 | Lecture list plus "how progress is calculated". No mastery by objective, no trends. |
| S17 Profile/preferences | 🟡 | Profile and sign-out. No accessibility/notification preferences or session controls. |
| S18 Help/report | 🟡 | FAQ and a no-secrets warning. **No report form**: it needs a new table (owner approval). The page says so rather than pretending. |

## Teacher screens

| ID | Status | Notes |
|---|---|---|
| T01 Overview | 🟡 | Summary counts and learners needing support. No cohort cards, recent teacher actions or system notices. |
| T02 Cohort list / T03 Cohort analytics | 🔒 | The data model has teacher→learner assignments, not named cohorts. Needs a decision. Exercise analytics exist (completion, pass rate, common failed criteria). |
| T04 Roster | ✅ | Search, needs-support filter, pagination (server-side). |
| T05 Learner detail | ✅ | Progress, attempts, best score, evidence, feedback. |
| T06 Attempt review | ✅ | Code snapshot, criteria, status, feedback composer. |
| T07 Remediation/feedback | 🟡 | Feedback with learner-visible toggle. No assignable remediation, no due date (spec says only if supported). |
| T08 Assessment analytics | 🟡 | Per exercise, system errors kept separate. No score bands or trends. |
| T09 Content library | 🟡 | Read-only content status. |
| T10–T14 Authoring, validation, publish | 🔒 | Not built. Requires the authoring-permission, review and versioning decisions (the spec's own phase 6). |
| T15 Profile / T16 Help | 🟡 | Shared with the learner pages. |

## Admin screens

| ID | Status | Notes |
|---|---|---|
| A01 Role management / A02 Enrolment | 🟡 | Server endpoints exist and are audited. No UI. |
| A03 Queue health / A04 Service health | ❌ | Only `/health` and `/ready`. No metrics, no percentiles. |
| A05 Audit log | 🟡 | Events are written with an allow-listed metadata set. No viewer. |
| A06 Content issue queue | ❌ | Depends on a report-issue backend. |

## Shared states
Loading (spinner and new skeleton), empty vs error, plain-language errors with retry, confirmation dialogs with focus handling, status never by colour alone, responsive checks at 360–1440 px: ✅. Correlation IDs on errors, and filters/pagination kept in the URL: 🟡 (the roster uses local state). Toasts: not used; status is shown on the page.

## System behaviour (sections 10–17)

| Area | Status |
|---|---|
| Idempotent submissions, server-authoritative score/completion, 404 for out-of-scope resources, rate limits (6/min, 2 in flight) | ✅ tested against fakes |
| Draft autosave (debounced), saved/unsaved/local-only labels, reconcile by content version | ✅ |
| `/api/v1` prefix | ✅ every router is mounted under `/api/v1` (correction: an earlier draft of this report wrongly said it was missing) |
| Durable queue, transactional outbox, worker leases, retry with jitter, dead-letter, fair scheduling, shutdown handling | 🔒 Grading is a background task calling the grader over HTTP. A crash can leave an attempt unfinished until it expires. Queue technology and hosting are an open decision (no Redis/paid service without approval). |
| Latency targets (p95/p99), queue-wait target, 10→100-user load test, hostile-code probes | ❌ **Never measured.** No claim of meeting any target is made. The sandbox could not be run here (no Docker daemon). |
| Polling 1–2 s with back-off | 🟡 polling exists; back-off should be checked |
| Security (ownership checks, hidden tests private, no secrets in logs) | ✅ in tests; live RLS and sandbox probes unverified |

## What this change set did
Added S02, S03, S15, S18 (guidance only), a help link in the navigation, a "how progress is calculated" explanation, skeleton placeholders, and tests for them. Everything else above is unchanged.

## Decisions needed from you
1. Named cohorts (T02/T03) or keep teacher→learner assignments.
2. A table for problem reports (S18/T16/A06).
3. Authoring and publishing workflow (T10–T14).
4. Queue technology and hosting (A03/A04, section 12).
