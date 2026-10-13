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

## Results (2026-10-13). Objectives above were not changed after seeing numbers.

Generator: one cloud container, outbound through a proxy (adds roughly 200 ms to every request and occasionally fails a TLS handshake). The columns marked "server" come from the API's own `Server-Timing` header, so they exclude that path.

### Run 0: baseline before any performance work (10 users)
Client p50 3.2 to 5.5 s on every endpoint (p95 up to 10.4 s). Cause: API in `iad1` talking to a Tokyo database, 6 to 15 sequential upstream calls per request, a new TLS connection per call.

### Changes made because of run 0
Pooled upstream HTTP client (keep-alive); 30 s token-verification cache; API pinned to `hnd1` (next to Supabase); independent reads run concurrently (lecture context, dashboard, submission pre-checks); the submission audit write moved off the request path; 15 s in-process cache for published, learner-independent content only (learner state is never cached; a republish appears within 15 s).

### Run 5 (final, same code as production)
| Stage | Errors | Slowest endpoint, client p95 | Same endpoint, server p95 |
|---|---|---|---|
| 10 learners | 0 / 945 | dashboard 809 ms | 188 ms |
| 25 learners | 0 / 2394 | dashboard 831 ms | 190 ms |
| 40 learners | 2 / 3465 (0.06%, both generator connect timeouts) | dashboard 1036 ms | 294 ms |

At 40 learners the other endpoints were: lecture 473, session 595, checkpoint write 750, draft 570, session write 676 ms (client p95); server p95 at most 473 ms (checkpoint write).
Burst of 12 simultaneous submissions: acknowledgement p50 1089 ms / p95 1130 ms; every attempt finished and passed (no lost or duplicated attempt); grading end to end p50 13.7 s, p95 17.2 s, max 19.1 s.

### Verdict against the objectives
- Met: error rate (under 1% at every stage), write p95 (under 1000 ms), grading end to end p95 (17.2 s under 30 s), burst correctness.
- **Missed, by a small margin:** dashboard read p95 (809 / 831 / 1036 ms against 800 ms) and burst acknowledgement p95 (1130 ms against 1000 ms), measured at the client.
- The server-side figures (dashboard p95 at most 294 ms) show the API is not the limit; the remaining time is the generator's network path. This was not proved by measuring from a second location, so it is a likely explanation, not a result.
- Earlier runs on the same code varied (one 40-learner run had p95 above 2.5 s on session reads). Treat results as noisy; the tail at 40 learners is not stable.

### What may be claimed
Tested and working: 10, 25 and 40 concurrent synthetic learners for 60 s each, and 12 simultaneous submissions, against the free-tier stack with one grading worker. **Not tested:** 100 users, sustained load beyond 60 s, several workers, real network conditions. No 100-user capacity claim is made.
