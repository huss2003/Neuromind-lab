# ADR: Hosted official grading (pull-model queue in Postgres)

Status: accepted for implementation, **not yet deployed**. Date: 2026-10-13.

## Context
Learner code is hostile input. Today the API grades through `GRADER_BASE_URL` (default `http://127.0.0.1:8010`) from a FastAPI `BackgroundTask`. That works on a developer machine only: a hosted API cannot reach a laptop, and an in-memory background task is lost when the API instance stops. The AWS account provided has a $100 Free-plan credit and a Service Control Policy that **denies EC2, ECS, ECR, SQS, SNS, Lambda, CloudWatch, SSM and Secrets Manager** (see the AWS plan), so an AWS-compute worker cannot be created from it today.

## Decision
1. **The existing table is the queue.** `lab_submissions.status` (`queued` → `running` → final) plus three columns (`claimed_by`, `lease_expires_at`, `claim_count`, migration `0006`). No second store, so no queue/database disagreement and no transactional-outbox problem: the attempt row is written *before* the API answers `202`, and that row *is* the job.
2. **Pull, not push.** A worker polls the API over HTTPS (`POST /api/v1/internal/grader/claim`). The worker opens no port, so there is nothing to attack from the internet, and it holds **no database credentials**, only a worker token that can claim a job, extend its lease and post a result for the job it holds.
3. **Atomic claim** with `claim_next_submission` (`FOR UPDATE SKIP LOCKED`). Two workers can never get the same job.
4. **Lease + heartbeat.** 60 s lease, heartbeat every 20 s. A dead worker's job is re-claimed after the lease expires. A late result from the old worker is fenced out (`409 LEASE_LOST`).
5. **Bounded retries.** At most 3 claims. After that the attempt becomes `error` ("system issue, not marked incorrect", score unchanged) — this is the dead-letter state, visible to support by `status='error' and claim_count>=3`. Deterministic learner failures (wrong answer, crash, timeout) are results, never retried.
6. **Idempotent finalisation.** `finalize_submission` does nothing if the attempt is already `passed/failed/runtime_error/timeout/cancelled`. Duplicate or late results cannot change a score.
7. **Strict result validation** (`validate_payload`); anything malformed becomes a system error, never a pass. The score is recomputed server-side (hint penalty, pass mark).
8. **Isolation** is two layers: the Docker flags (no network, read-only root, all caps dropped, non-root, memory/CPU/pid/file limits, hard kill) and the parent/child harness split (`GRADER_THREAT_MODEL.md`).
9. **Fairness/back-pressure:** existing per-user limits (6/min, 2 in flight). Global capacity = worker count × concurrency (default 1, max 2). Excess work waits in `queued`; the UI shows "waiting" and polls 1 s backing off to 4 s.
10. **Modes:** `GRADER_MODE=inline` (default, local development) or `queue` (hosted). Hosted official grading must never silently fall back to a mock.

## Where the worker runs (open, needs the owner)
| Option | Cost | Status |
|---|---|---|
| A. EC2 `t4g.micro` in the AWS account | about $11/month (see plan) | **Blocked**: the SCP denies EC2. Needs an AWS organisation admin to lift it, and a Free-plan account may need upgrading to a paid plan, which removes the automatic spending stop. |
| B. Any Docker host you control (an always-on computer or a small VPS) | $0–$6/month | Works with the code as written. A home machine is a weaker availability story. |
| C. Managed container service (Fargate/Cloud Run) | higher, plus a NAT or public IP | Rejected: more cost and moving parts than the workload needs. |

## Rejected alternatives
* **SQS + outbox:** correct but adds a second source of truth, IAM, and a publisher; SQS is also denied here. Postgres `SKIP LOCKED` is the standard small-scale alternative.
* **Keep `BackgroundTasks`:** not durable; jobs vanish on restart.
* **Grader as a public HTTP service:** would expose a code-execution endpoint to the internet.
* **Lambda/Fargate per submission:** cold starts and cost, and Lambda is denied.

## Consequences and limits
* Polling load: adaptive (1 s for 60 s after work, 10 s idle) is about 8,600 idle API calls/day per worker; the API runs on Vercel, so watch the serverless invocation allowance.
* Throughput is bounded by one worker (about 1–2 gradings in parallel). A 100-user class submitting at once would queue. **Not measured.**
* `claim_next_submission` was verified on the live database in a rolled-back transaction (exclusive claim, lease re-claim, dead-letter after 3 claims, no rights for `anon`/`authenticated`). The Python API and worker were verified only against an in-memory fake and a mocked API.
