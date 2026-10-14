# Production readiness report

Date: 2026-10-13 · Branch `claude/determined-bardeen-ip8pup`

## Decision: **CONDITIONAL GO — controlled pilot only** (see the final update at the end of this file; the sections below are the history that led here)

_Earlier decision on this page: NO-GO._
Official grading has never been run through a real sandbox, the real learner journey has not been run end to end, secrets are not confirmed rotated, content is placeholder, and no hosted grader exists. Several items below are real progress, but a green unit-test run is not a release.

## Gate status
| Gate | Status | Why |
|---|---|---|
| 0 Secrets and hidden tests | **NOT PASSED** | Default dev password removed from code and replaced by a required env var; secret scanner + CI added; hidden-test definition moved out of the seed. **But:** the old password is in public Git history and live accounts may still use it; the service-role key was pasted into chat and rotation is **not confirmed**; the repo is public. |
| 1 Real local journey | **NOT RUN** | No Docker daemon; Supabase unreachable from the shell here. Only mocked-network UI tests and in-memory API tests ran. |
| 2 Sandbox security | **PARTIAL** | Result-forgery boundary redesigned and 13 adversarial tests pass in a *local, non-isolated* subprocess. **Docker run NOT RUN.** |
| 3 Hosted grading | **PARTIAL / BLOCKED** | Postgres queue verified on the live database (rolled-back transaction); API worker endpoints, worker program and idempotency verified against fakes/mocks only. No worker host exists: the AWS account's SCP denies EC2/ECS/SQS/etc. |
| 4 Content, authorization, a11y, load | **NOT DONE** | Lecture 9 is still placeholder. Authorization tests exist against in-memory fakes. No axe scan, no load test. |
| 5 Production deploy | **NOT DONE** | Vercel serves commit `1c97cec`, which predates these changes; API `GRADER_MODE` stays `inline`, so hosted grading shows "system error — not your fault". |
| 6 CI/CD and runbooks | **PARTIAL** | CI workflow written, never executed on GitHub. Release checklist, ADR, cost plan, threat model, E2E guide written. No rollback/restore rehearsal. |

## Tests actually run (this session)
| Suite | Result | Kind |
|---|---|---|
| backend `pytest` + `ruff` | 109 passed, lint clean | MOCKED (in-memory repository) |
| grader `pytest` | 31 passed, 1 skipped (Docker) | harness tests local subprocess; Docker test SKIPPED |
| frontend `vitest`, `eslint`, `tsc` | clean | unit |
| `pnpm test:ui` | 34 of 35 passed in the last full run (the failing one fixed and re-run alone → passed) before this session's later changes; not re-run after the polling-backoff edit | MOCKED network |
| secret scan | clean (159 files) | local script |
| live DB `claim_next_submission` | claim exclusivity, lease reclaim, dead-letter at 3 claims, no rights for anon/authenticated: verified | REAL database, rolled back |
| `pnpm e2e`, Docker sandbox, load tests, a11y audit, CI on GitHub | **NOT RUN** | — |

## Security findings fixed
1. Hard-coded default password in `scripts/create_dev_users.py` and `frontend/e2e/helpers.ts` → now required from the environment; refused if short or equal to the leaked value; refused when `APP_ENV=production`.
2. Result forgery: the nonce lived in a local variable of the process running learner code → learner code now runs in a child process that never receives the nonce; strict schema for the child's report; fail-safe on anything malformed.
3. Hidden test definition in a public seed → placeholder in Git, private loader added (live database still holds the old definition until `load_private_tests.py` runs; Git history still contains it).
4. Queue durability: attempts previously depended on an in-memory background task → DB-backed leases, bounded retries, dead-letter, idempotent finalisation.

## Still open (blocking)
Rotate keys; change dev passwords; decide on history rewrite or private repo; run Docker sandbox and adversarial suite; provide a worker host (AWS SCP blocks EC2; or use a Docker host you control) and run staging failure drills; author real content; accessibility and load testing; apply seeds privately; redeploy; production smoke test.

## Capacity statement
No capacity is claimed. Earlier docs mention ~200 and ~100 learners; neither was measured. With one worker at concurrency 1–2, simultaneous submissions queue.


---
## Update 2026-10-13 (later): real worker on AWS, real Docker, real drills
Decision is still **NO-GO**, but Gates 2 and 3 now have real evidence.

**Infrastructure created (account 757968055032, ap-southeast-2, all tagged `project=neuromind`):** budget `neuromind-monthly-15usd` ($15, email alerts at 50/80/100% actual and 100% forecast); EC2 `i-018d91b05eae11535` (t4g.micro, 12 GB encrypted gp3, IMDSv2 required, hop limit 1, security group `sg-0b10f72ed14036306` with **no inbound rules**); IAM role/profile `neuromind-worker` (SSM core + read of one parameter); SSM SecureString `/neuromind/worker-token`. Estimated about $12.6/month.

| Gate | Evidence | Result |
|---|---|---|
| 2 Docker sandbox | `tests/test_docker_sandbox.py` on the real host: network (incl. 169.254.169.254) denied, no secrets in env, read-only root, no docker socket/host paths, non-root without capabilities, `/tmp` noexec and small, infinite loop times out and container is removed, memory bomb killed, fork bomb contained, output bounded | **9 passed** (first run 8 passed + 1 failed because the probe wrongly expected `/home` to be absent; test corrected, not the sandbox; re-run 9/9) |
| 2 Result forgery | `tests/test_adversarial.py` on the same host | **13 passed** (these use a local subprocess on that host, not a container) |
| 3 Hosted grading | `scripts/staging_drills.py` against the live API (`GRADER_MODE=queue`) and the real worker | see below |

Staging drills (synthetic learner `learner3`, real Supabase, real Vercel API, real Docker worker):
* auth: no token / wrong token / learner JWT on the worker interface → all rejected (3/3 pass)
* journey: wrong code → real `failed` with criteria (13.4 s end to end on the first, cold-poll attempt); correct code → `passed` 100 (0.8 s); same Idempotency-Key → same attempt; a later worse attempt keeps best 100; a duplicate/late worker result → `accepted:false`, status unchanged (5/5 pass)
* worker killed with SIGKILL mid-job: job re-claimed after the 60 s lease and finished (`timeout`) in 75 s (1/1 pass)
* worker stopped, three claims abandoned: job dead-lettered as `error` (system issue, no score, `infrastructure_error`) (1/1 pass)
Timings are single samples, **not a load test**. The first attempt's 13 s shows the cost of the 10 s idle poll interval.

**Still blocking:** Gate 0 (owner chose **not** to rotate the Supabase key or dev passwords; the old default password is in public history and live accounts still accept it, as these drills show); full browser end-to-end journey against the real stack not run; content is placeholder; no axe/screen-reader audit; no load test; hosted learner-facing UI journey not smoke-tested after the switch to queue mode; worker is a single instance with no alerting (an outage means submissions wait, then dead-letter after 3 claims).

---
## Update 2026-10-13 (final pass): real content, UI v2, live browser journey
**Decision: still NO-GO for real learners.** The product itself now works end to end on the live stack, but the credential gate is open by the owner's choice and several launch checks were never done (below).

**Placeholder removal.** Lecture 9 now has authored text (`database/seed/005_lecture9_content.sql`, applied to the dev database through `scripts/apply_lecture9_content.py`): a real introduction, three lessons (set up Python, notebooks and cells, variables and print), three reviewed multiple-choice questions with explanations, a lab with real instructions. The three placeholder videos were **replaced by written lessons** because no recordings exist; no placeholder text remains in the database (checked). Lecture content version is 2; earlier attempts keep version 1. Older seed files still contain the historical placeholder text and are superseded by seed 005. **Only Lecture 9 exists; the other 103 lectures are not authored.**

**UI v2.** New visual system ("Cortex": ink rail, mist workspace, one blue for actions, amber only for "you are here", pathway progress, Bricolage Grotesque / Instrument Sans / JetBrains Mono self-hosted, tinted code editor theme), split sign-in, dashboard hero, desktop lab workbench (task beside editor), lesson text renderer, error boundary, security headers. Live at https://neuromind-lab.vercel.app. Screenshots were reviewed at 360 and 1440 px.

**Tests run in this pass (actual results)**
| Suite | Result |
|---|---|
| backend pytest + ruff | 109 passed, lint clean (MOCKED repository) |
| grader pytest | 32 passed, 11 skipped locally (Docker tests need Docker) |
| frontend eslint, tsc, vitest | clean, 37 passed |
| `pnpm test:ui` (Chromium, MOCKED network) incl. **axe WCAG 2.1 A/AA scans** of 17 screens at 1440 and 390 px | 38 of 38 passed in the last full run; one keyboard test was updated afterwards for the new skip link and passed alone |
| Docker sandbox + adversarial suite **on the AWS worker host** | 25 passed (10 container-isolation probes, 15 forgery/robustness) |
| **Live browser E2E** (real Chromium → live site → live API → Supabase → AWS worker → Docker) | A: full lecture journey ending in "Lecture complete", still complete after reload: passed. B: failure with guidance, retry passes, both attempts kept, best score 100: passed. C: learner blocked from teacher page and API (403) and from another learner's submission (404): passed. Smoke tests: passed. |

**Defects found by this testing and fixed**
1. The frontend Vercel project had no root directory, so the live site returned 404 even though deployments said READY. Fixed by deploying with the `frontend` root; verified in a browser.
2. **Leaked CPU-burning sandbox processes.** After my worker-kill drill, an infinite-loop container and a harness child kept running for 2 hours and saturated both CPUs, making grading slow. Fixes: hard `timeout` inside the container, the learner process dies with its parent (PDEATHSIG), the worker removes stray sandbox containers at start-up. Tests added (including a real "kill the worker, the program still dies" container test) and run on the host.
3. Axe found low contrast on the success badge and an unfocusable scrolling stepper; both fixed and re-scanned.
4. The sign-in page had no skip link; added.
5. The e2e sign-in helper treated the sign-in page's own heading as success; fixed.

**Still open (why the answer is NO-GO)**
* Gate 0: the owner chose not to rotate the Supabase key or dev passwords; the old default password is in public Git history and still works on the dev accounts (the live tests logged in with it). The hidden test definition remains in the database and in public history of the old seed.
* Grading takes about 8 to 15 seconds, mostly the worker's idle polling interval (10 s). Acceptable for a pilot; measured with a handful of single attempts only. **No load test, no capacity figure.**
* One worker, no alerting: if it stops, submissions wait and then fail safe as "system issue".
* Accessibility: automated scans only; no screen-reader or keyboard-by-hand audit.
* Monaco editor and the Python practice runtime (CDN) were not exercised in the live run (tests used the plain-text editor); Run practice in a real browser is unverified.
* Real lecture videos, the other 103 lectures, teacher content tools and the admin screens do not exist.
* Retention, privacy policy and terms are not written.


---
## Update 2026-10-13 (final): load test, monitoring, content, restore rehearsal, live checks
**Decision: CONDITIONAL GO for a small, supervised pilot (tens of learners) on the current stack. NOT a GO for open or 100-user use.** What the conditions are is listed at the end; none of them was waived silently.

### Evidence
| Area | What was done | Result |
|---|---|---|
| Load test | `scripts/load_test.py`, objectives fixed beforehand in `LOAD_TEST_PLAN.md`, 10/25/40 concurrent synthetic learners for 60 s each, plus 12 simultaneous submissions | Baseline was 3 to 5 s per request; after fixes server-side p95 is at most 473 ms and client p95 mostly under 800 ms. **Objectives still missed:** dashboard read p95 (809 / 831 / 1036 ms vs 800) and burst acknowledgement p95 (1130 ms vs 1000), measured at the client. Errors 0 to 0.06% (generator connect timeouts). Every burst submission finished and passed. Details and caveats in `LOAD_TEST_PLAN.md`. |
| Grading latency | After idle poll 10 s to 5 s and worker concurrency 1 to 2 | Burst of 12: end to end p50 6.5 s, p95 10.4 s (was 13.7 / 17.2 s) |
| Monitoring and alerts | Worker host publishes `WorkerActive` and `OldestQueuedSeconds` each minute; CloudWatch alarms: queue backlog (oldest job over 120 s for 3 min), worker down or silent, API unreachable from the worker, EC2 status check; SNS topic `neuromind-alerts` | Metrics verified arriving; all 4 alarms OK. **The e-mail subscription to Hussainsingapuri24@gmail.com must be confirmed by clicking the link AWS sent; until then no alert e-mail is delivered.** Alarm delivery itself was not triggered end to end. |
| AWS cost | Budget `neuromind-monthly-15usd` exists; Cost Explorer shows no charges yet this month | Estimated about $12.6 plus about $1 for metrics and alarms, within the $15 limit; actual month-end figure not yet known |
| Content | Lectures 10 to 12 authored (reading lessons, questions, labs, private test definitions kept out of Git) and applied to the dev database | 4 lectures exist in total (9 to 12). **Not** 104. The new labs were verified in the database only (counts), not walked through in a browser, because they unlock after Lecture 9. |
| Practice runtime | Real Chromium against the live site: Monaco editor loads, Pyodide runs learner code and shows output, an infinite loop is stopped after 5 s and the page stays usable (`e2e/practice.spec.ts`) | Passed |
| Smoke and security headers | Live site: sign-in routing, not-found, no overflow at 360 px, `/privacy` and `/terms` reachable, HSTS, nosniff, frame deny present | Passed (one first-attempt navigation timeout through the proxy, passed on re-run) |
| Accessibility | axe WCAG 2.1 A/AA scans now include privacy and terms | Automated only; no screen-reader or by-hand audit |
| Backup and restore | `scripts/backup_db.py`, `scripts/dr_rehearsal.sh`, runbook | Migrations 0001 to 0006 applied from an empty PostgreSQL; 19 of 19 tables restored with identical row counts. Auth users and RLS behaviour on the copy were **not** proved. |
| Test suites | backend 112 passed + ruff clean; grader worker tests passed (Docker tests ran earlier on the host); frontend lint, tsc, vitest 37, `test:ui` 38 of 38 | CI workflow still has **never run on GitHub** (no `main` branch exists; it triggers on pull requests and pushes to `main`) |

### Conditions that keep this from a full GO
1. **Credentials (Gate 0):** the owner chose not to rotate the Supabase key or dev passwords. The old default password is in public Git history and the synthetic dev accounts still accept it. Real learners must use new accounts, and the dev/synthetic accounts should be deleted before launch. The service-role key was shared in chat and remains unrotated.
2. **Single environment:** there is no separate staging project; development, drills and the pilot share one Supabase project. Decide whether to create a second project.
3. **Capacity:** tested to 40 concurrent synthetic learners for 60 s on a free-tier stack with one worker host; no 100-user capacity claim.
4. **Content:** 4 of 104 lectures; no recorded videos; teacher authoring and admin screens do not exist.
5. **Policies:** privacy and terms pages are drafts without legal review; retention periods in `DATA_RETENTION_AND_POLICIES.md` are proposals.
6. **Alerting:** confirm the SNS e-mail subscription; one worker host is still a single point of failure (submissions wait, then fail safe as a system issue).
7. **Release process:** CI has never run on GitHub; production aliases currently serve builds of the working branch, not `main`.

---
## Update 2026-10-14: credentials, CI, policies, accessibility, staging
- **Accounts:** all 44 synthetic accounts deleted after a backup; old password verified to fail; no real users or admin exist yet (owner creates the admin with `scripts/create_admin.py`). Service-role key still unrotated by owner decision, so Gate 0 stays a condition. See `ENVIRONMENTS_AND_TEST_ACCOUNTS.md`.
- **CI:** `main` created (at the first commit) and PR 1 opened. First real CI run: secrets, grader (incl. Docker tests) and frontend (lint, typecheck, unit, build, UI + axe) passed; backend failed because one test relied on local `SUPABASE_*` variables. Fixed so the suite passes with an empty environment (112 passed).
- **Accessibility audit (structure, not a real screen reader):** new `ui-tests/screenreader.spec.ts` found two real defects: every screen had the same document title, and keyboard focus stayed on the clicked link after in-app navigation. Fixed with `RouteA11y` (title from the page heading, focus moved to the new content). Also now checked on all learner screens: one main landmark, one h1, no skipped heading levels, distinct nav labels, labelled fields, grouped radio options, status live region for answers. **No test with NVDA, JAWS, VoiceOver or TalkBack was done** and none can be run from this environment; a manual pass by a person using one is still recommended before an open launch.
- **Policies:** privacy notice expanded (storage regions, browser storage, backups, age, request handling). Still a draft needing the owner's operator/contact details and legal review.
- **Staging:** **not created.** Supabase refused (free plan, 2 active projects limit reached). Needs an owner decision (see `ENVIRONMENTS_AND_TEST_ACCOUNTS.md`).
