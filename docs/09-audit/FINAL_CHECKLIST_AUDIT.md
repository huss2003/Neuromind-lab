# Audit against "NeuroMind AI Learning Lab: Final Production Checklist" (v1.0, 14 Oct 2026)

Audited 2026-10-14 against `main` at `1a40d2a` (production frontend built from `08b8b61`, API from `3515c90`; later commits are docs and tests only). Evidence rule from the checklist is followed: an item is marked verified only when a test, service response or deployed behaviour can be pointed to.

**Status codes** (the checklist's own labels, plus two):
**PV** production verified (live site and API, current build) · **RS** real-service verified (real Supabase/AWS/Docker, but an earlier commit or a non-production path) · **T** automated test passed (mocked, in-memory or CI; not a real service) · **S** implemented in source only · **P** partial · **NB** not built · **OWN** needs the owner, or blocked.

## Headline
| | Count (approx.) |
|---|---|
| Items verified on production (PV) | the whole learner journey, grading, practice runtime, titles and focus, learner-to-teacher access denial |
| Items built and tested, not production-exercised (T/RS) | most of the API rules, teacher screens, sandbox hardening, restore |
| Not built (NB) | admin screens, certificates, announcements, report export, MFA/OAuth/sign-up, named cohorts, assignment-management UI for teachers, report-an-issue form, an incident-response document |
| Owner or human required (OWN) | key rotation (declined), policy owner details and legal review, retention approval, real screen-reader review, pilot cohort and support owner, staging project |

**Not everything in the checklist is implemented.** The learner product is; the administrator workspace and several teacher and learner extras are not.

## New evidence collected for this audit (2026-10-14, production)
* Created four temporary test accounts, enrolled them, ran against the live site and API: **A** full lecture to "Lecture complete" and still complete after reload: pass · **B** wrong code fails officially with criterion feedback, retry passes, both attempts kept, best score 100%: pass · **C** learner blocked from teacher pages and API (403) and from another learner's submission (404): pass · **practice** Monaco loads, Pyodide runs code, an infinite loop is stopped after 5 s: pass · **titles** five screens have distinct titles and focus moves into the page after navigation: pass (5 of 5). Accounts deleted again afterwards; only the admin account remains.
* Post-merge CI on `main`: runs for `1a40d2a`, `08b8b61` and `47847187` passed. The first run for `3515c90` **failed** in the grader job on `test_infinite_loop_times_out_and_container_is_removed`; a second run on the same commit passed. Cause: the test checked for container removal immediately after `docker kill`, before the daemon finished `--rm`. This is a test race, not a leak; the test now waits up to 10 s (the assertion is unchanged). That change is not yet merged and was not run locally (no Docker here).
* Supabase security advisor: RLS enabled on every table. Three tables have RLS and no policy by design (`audit_logs`, `exercise_tests`, `mcq_questions`: service-only). One warning: leaked-password protection is disabled (an Auth setting; I cannot change it from here and it may need a paid plan).
* Production bundle contains no `service_role` string; lesson "expected output" strings in the bundle are public worked examples, not hidden tests.

## 3. Visual design and navigation
| Item | Status | Evidence / gap |
|---|---|---|
| Dashboard prioritises next lesson and Continue | PV | journey A starts from it |
| Course navigation: modules, lectures, prerequisites, state | T | UI tests, backend lock tests; only 4 lectures exist |
| Lecture player keeps theory, checkpoints, practical together | PV | journey A |
| Coding area separates editor, output, submission state, feedback | PV | journey B, practice test |
| Teacher workspace: overview, learners needing help, progress, feedback | P (T) | roster, needs-support filter, analytics; no cohort cards; not browsed on production this session |
| Admin workspace | **NB** | no admin screens; role, enrolment and assignment changes exist only as API calls and scripts |
| Meaningful page titles, focus after navigation | PV | `e2e/titles.spec.ts` on production (defect found and fixed earlier today) |
| No dead buttons, dummy data, unexplained messages | P | Help states honestly that there is no report form; no recorded videos exist |

## 4. Core learner journey (14 steps)
| Step | Status | Note |
|---|---|---|
| 1 Sign in, 2 Dashboard | PV | |
| 3 Theory with captions/transcript | P | written lessons PV; **no videos are published**; captions supported in code (T) |
| 4 to 6 Checkpoints, persisted, retry rules | PV | |
| 7 Practical demonstration | P | worked example as text, not a recorded demo |
| 8 Python practice: edit, run in browser, reset | PV (reset: T) | |
| 9 Official submit, queued/running | PV | real Docker worker on AWS |
| 10 Incorrect code fails with criterion feedback | PV | journey B |
| 11 Remediation | PV | "How to fix it" |
| 12 Retry passes through official grader | PV | |
| 13 Completion persisted after refresh | PV | **logout then login was not tested explicitly** |
| 14 Progress updates and next lecture unlocks | P (T) | unlock rule is tested with fakes; not exercised live (needs Lecture 9 completed then Lecture 10) |

## 5. Lecture timing
**P.** The structure (intro, theory, checks, practical, exit check) exists. The minute budget is advisory only and no recorded media exists, so it is not verified.

## 6. Student checklist
| Area | Status | Notes |
|---|---|---|
| Sign in/out, session expiry | PV / T | |
| Password recovery | S + OWN | page built; email delivery depends on Supabase's default mail and was never confirmed |
| Course, prerequisite states, profile, help | T | no preferences/settings beyond profile |
| Video controls, progress | S/T | no video content to test |
| Captions/transcript, resume, media failure and retry | T | resume PV |
| MCQ: readable, explained, persisted, keyboard/SR | PV / T | retry rules shown in UI; no standalone written rule document |
| Python practice: run, output, reset, errors | PV / T | |
| stdout and stderr distinguished | T | separate output blocks |
| Drafts autosave, unsaved signalled | T (+RS: draft writes ran in the load test) | |
| Practice isolated from privileged services | PV | runs in a browser worker |
| Official grading separate from browser | PV | |
| Result, score, criterion feedback | PV | |
| Hidden tests not disclosed | T + bundle check | an early placeholder test definition is still in **public Git history**; the live definitions are different (no verbatim match found; the comparison was not rigorous) |
| Hints, remediation | T / PV | |
| Attempt history: timestamps, status, **exercise version** | **P** | timestamp and status shown; exercise/content version is stored but not shown |
| Best score kept, hint penalty per attempt, evidence kept | PV / T / PV | |
| Progress matches server, prerequisites server-side, exit checks | PV / T / PV | |
| Certificates | **NB** | |
| Project/portfolio evidence | **NB** | |

## 7. Teacher workspace
| Item | Status |
|---|---|
| Assigned learners only | T (backend scope tests); named **cohorts** not built (teacher-to-learner assignments only) |
| Progress, completion, class metrics | T |
| Filter/search, needs-help | T |
| Learner detail, scores, attempts, evidence, failed criteria, remediation history | T |
| Feedback and notes | T (never changes scores: tested) |
| Manage assignments | P: API only, no screen |
| Announcements / guidance messages | **NB** |
| Export reports | **NB** |
| View lecture content and resources | P: read-only content status page; no resource library |
| Cannot reach unassigned learners, change scores, see hidden tests/secrets | T; learner-to-teacher denial PV |
| Sensitive actions logged | T (allow-listed audit metadata) |

## 8. Administrator workspace
Almost entirely **NB as a workspace**. What exists: role change, enrolment and teacher-assignment API calls (audited, tested with fakes); scripts for creating the admin and test users; backup and restore scripts; `/api/v1/health`, `/api/v1/ready` and a worker queue-health endpoint; CloudWatch alarms. Missing: user create/deactivate UI, course/lecture/exercise management UI, rubric/version management UI, queue and worker monitoring screen, audit-log viewer, platform settings, analytics, session revocation (done in the Supabase dashboard). No endpoint exists that edits an official score, which satisfies the last item.

## 9. Screen inventory
Built: sign in, recovery, dashboard, course, lecture player, MCQ, practice, submission status, results/remediation, attempt history, progress, profile, help, welcome, policies (6), teacher dashboard/learner/submission, not-found, error boundary, loading/empty/error states. **Not built:** sign-up (not enabled), email verification, certificates, all admin screens, announcements, settings, report-an-issue.

## 10. Grading integrity and sandbox
| Item | Status | Evidence |
|---|---|---|
| Real Docker image, resource limits, minimal privilege, no network incl. metadata, read-only root | RS | 10 container tests on the AWS host (2026-10-13); also run on GitHub's runner in CI |
| Hidden tests private (bundle, API, logs) | T + bundle check | history caveat above |
| Trusted logic outside learner process; forged output, JSON, monkey-patching, imports | RS/T | 15 adversarial tests including killing the parent |
| Filesystem, env, path, network probes | RS | |
| Infinite loop, memory, fork bomb, huge output, malformed input | RS | |
| Abrupt termination, timeout, cleanup, concurrent isolation | RS | cleanup test had a timing race in CI (see above) |
| Forged API requests, another learner's submission | PV (denial) / T | |
| Persist identity, version, submission ID, result | T/PV | |
| Fail safe on missing/malformed/duplicate results | RS/T | |
| Diagnostic evidence kept without leaking | P | |

## 11. Durable hosted grading
| Item | Status |
|---|---|
| Durable queue: restarts, leases, retries, dead-letter | RS: Postgres queue; drills 2026-10-13 (kill worker mid-job, duplicate result, dead-letter after 3 claims) on an **earlier commit**; not repeated today |
| Transactional outbox | Justified equivalent: the submission row **is** the queue, so there is no publish step to lose |
| Stable IDs and idempotency | RS (idempotency key tested live) |
| Recover abandoned jobs, bounded retries, no blind retry of learner failures | RS |
| Dead-letter handled with a documented operator procedure | **P**: state and query documented in the ADR; no step-by-step runbook |
| Per-learner and system-wide limits | PV/RS: 6 submissions/min and 2 in flight per learner; worker concurrency 2 |
| API restart, worker restart, duplicate delivery, persistence/queue failure | RS for worker kill and duplicate; API restart is inherent to serverless; persistence failure only with fakes |
| Measure queue wait, execution, end-to-end, errors | P: end-to-end and acknowledgement measured; queue wait not recorded separately |
| Never silently mock or pass | PV: unavailable grading shows "system issue, not marked incorrect" |

## 12. Architecture and deployment
Browser has no service-role key (PV bundle check). API enforces role, ownership, enrolment, teacher scope (T + PV denial). RLS reviewed with the advisor (see above). **Separate dev/staging/production: NB** (Supabase refused a second project three times). Migrations 0001 to 0006 apply from empty (RS local) and are repeatable. Backups before schema changes: script exists. Deployed commit verified through deployment metadata and the served bundle. Worker network: no inbound rules, outbound only; IAM limited to one SSM parameter, metrics in one namespace, SSM core. Health/readiness endpoints exist. CI: four jobs run on GitHub. Rollback: documented (re-alias previous deployment), **not exercised**.

## 13. AWS budget and operations
Budget `neuromind-monthly-15usd` exists; estimated about $13.6/month; alert email subscription confirmed by the owner; **budget alert delivery and alarm delivery were never triggered end to end** (OWN). Credit balance and expiry were **not** inspected (no billing access through the tools used). Resources tagged `project=neuromind`; inventory in `AWS_COST_AND_RESOURCE_PLAN.md`. No NAT gateway or load balancer. Log retention on the host is the OS default, not set (P). Post-credit cost and cleanup: described, not rehearsed.

## 14. Performance and load
Targets were fixed before testing; 10/25/40 learners for 60 s each plus a burst of 12 submissions; results in `LOAD_TEST_PLAN.md` (server p95 at most 473 ms; client-side dashboard p95 and submit-acknowledgement p95 narrowly missed; 0 to 0.06% errors). **Maximum demonstrated capacity: 40 concurrent synthetic learners for 60 seconds.** No 100-user or sustained test. The test ran against the production stack (the only stack), staged and with synthetic accounts.

## 15. Accessibility
Automated axe scans (T), keyboard path and skip link (T/PV), titles and focus (PV), headings/labels/landmarks (T), dialogs (ConfirmDialog, T). Queued/running states use live regions; the final result announcement was **not separately tested** (P). Contrast and 360 px overflow checked (T/PV); browser zoom not tested. **Human screen-reader review: not done (OWN).** No WCAG conformance is claimed.

## 16. Curriculum and content
4 of 104 lectures (9 to 12), written lessons instead of recordings, topic-specific questions and explanations, labs with private tests. They were authored by this project and have **not had an independent subject-matter review**. Certification alignment is not documented. 100 lectures are not authored.

## 17. Privacy, policies, support
Six policy pages exist as drafts. **OWN:** real organisation and monitored contact, legal review, retention approval. Access to learner records is restricted (T/PV). Deletion and deactivation are manual (documented). Support for recovery, failed grading and disputed results: **not defined**. Credential rotation: runbook written, **not performed (owner declined)**. **Incident response document: NB.** Backup restoration tested locally and recorded.

## 18. Release gates
| Gate | Result |
|---|---|
| 1 Security | **Not passed.** Service-role key not rotated (owner decision); no default credentials remain (accounts deleted, old password verified dead); ownership/scope tests pass; Docker and forgery tests pass; an early placeholder test definition is in public history. |
| 2 End to end | **Passed on production** (A and B above). |
| 3 Reliability | Mostly: queue, restart, duplicate drills passed on an earlier commit; hosted grader works on production; alert delivery not proven. |
| 4 Product quality | Not passed: no human screen-reader review; content only for 4 lectures and unreviewed independently. |
| 5 Operations | Partly: backups and restore (local), load measured with two narrow misses, commit verified; incident response and retention approval missing. |
| 6 Launch approval | Not passed: first admin exists, but policy owner details, legal review, pilot cohort, support owner and risk owners are not defined. |

## 19. Decision against the checklist's own rubric
The rubric says a failed mandatory gate means **NO-GO**, and Gate 1 (key rotation) is failed by the owner's choice. It permits **CONDITIONAL GO** only when the remaining limitations are explicitly approved by the owner with compensating controls and a release plan. So:
* **CONDITIONAL GO** for a small, supervised pilot **only if** the owner records approval of these limitations: unrotated service-role key, single shared database, draft policies, no human screen-reader review, four lectures, no admin UI. Compensating controls that exist: key held only in Vercel and a local git-ignored file, no real learner data yet, one admin account, backups and a restore procedure, alarms on the grading worker.
* **NO-GO** for an open or large launch.

## Appendix A quick pilot checklist
1. Latest `main` CI and deployed commit: done (see above; one grader test race fixed in a pending change).
2. Titles and focus on production: **done** (PV).
3. First administrator: **done** (signs in; role admin via the API); the password is weak and was shared in chat, so change it.
4. Rotate service-role key: **not done (owner declined)**.
5. Real end-to-end journey on a controlled account: **done** (PV today).
6. Sandbox adversarial tests: **done** (host and CI).
7. Teacher scope negative tests: tests with fakes pass; **live teacher-scope negative test not run** (needs a teacher and a non-assigned learner).
8. Monitoring and AWS alert email delivery: alarms and subscription exist; **delivery not proven**.
9. Offered lectures free of placeholders: done for 9 to 12.
10. Privacy/contact details and pilot terms: **OWN**.
11. Support owner and escalation: **OWN**.
12. Limit enrolment to demonstrated capacity: **recommend at most about 40 concurrent learners**.
