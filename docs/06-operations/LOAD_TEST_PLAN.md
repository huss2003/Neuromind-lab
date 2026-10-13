# Load test plan (objectives fixed before the first run)

Written 2026-10-13, before any load run. Tool: `scripts/load_test.py`. Target: the live dev stack (Vercel API in iad1, Supabase free tier, one AWS grading worker in Sydney). Users: synthetic `loadtestNN@neuromind.test`.

## Workload
Each virtual learner repeats: dashboard, course list, lecture manifest, session read, session save, checkpoint answer, draft autosave, then thinks 1 to 3 seconds. Stages 10, 25 and 40 concurrent learners, 60 seconds each. Then a **submission burst**: N learners press "Submit for grading" at the same instant.

## Pass/fail objectives (taken from the UX spec section 10, relaxed for the measurement path)
| Measure | Objective |
|---|---|
| Read requests p95 | 800 ms |
| Write requests p95 | 1000 ms |
| Submission acknowledgement p95 | 1000 ms |
| Errors (5xx, 401, 403, network) | at most 1 % |
| Grading end to end under a burst, p95 | 30 s |
| Burst correctness | every submission finishes and passes (no lost or duplicated attempt) |

The UX spec targets are tighter (reads 500 ms, ack 500 ms, grading 10 s). The numbers above add allowance because the load generator is a cloud container reaching Vercel and Supabase through a proxy; they are an upper bound for users near the servers. Misses are reported, not hidden.

## Not covered
Video delivery, the browser Python runtime, Supabase auth sign-in limits (logins are staggered), 100-user claims (the largest stage is 40 because only 40 synthetic users exist), long soak runs.
