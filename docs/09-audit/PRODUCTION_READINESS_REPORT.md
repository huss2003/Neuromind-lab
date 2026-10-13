# Production readiness report

Date: 2026-10-13 · Branch `claude/determined-bardeen-ip8pup`

## Decision: **NO-GO**
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
