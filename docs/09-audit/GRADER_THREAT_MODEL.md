# Grader threat model

## Assets
Official scores and completion; hidden test definitions; service credentials (Supabase service role, worker token); other learners' code; the grading host.

## Trust boundaries
Browser (untrusted) → API (trusted, enforces identity/ownership) → Postgres (system of record) ← worker (trusted process, holds only a worker token) → Docker container → **harness parent (trusted)** → **child process running learner code (untrusted)**.

## Attacker
An enrolled learner who controls their submitted source code, the content of their stdout/stderr, and the timing of requests. They can read every public file in this repository.

## Attack paths and controls
| # | Attack | Control | Evidence |
|---|---|---|---|
| 1 | Print a fake `NMRESULT:` line to forge a result | Parent starts the learner code as a child and reads the child's stdout through its own pipe; the nonce exists only in the parent. Printed text is ordinary output. | `test_printing_a_fake_result_line…`, `test_guessing_or_hunting_the_nonce…` (local subprocess, PASS) |
| 2 | Find the nonce through frames, env, argv, `/proc` | Nonce is not in the child's argv/env/stdin; parent sets non-dumpable | `test_parent_memory_and_environment…` (PASS locally; **inside Docker NOT RUN**) |
| 3 | Write a forged report on the report pipe | Strict schema, declared variables only, size cap; malformed/missing = "crashed", never a pass | `test_forged_report…`, `test_report_for_undeclared_variable…`, `test_abrupt_exit…` (PASS) |
| 4 | Exit early / `sys.exit(0)` to hide an error | Missing report fails safe; `SystemExit` is a runtime error | PASS |
| 5 | Infinite loop, output flood | Host timeout kills the container; output capped at 20 kB and drained | `test_infinite_loop…`, `test_output_flood…`, `test_endless_output_flood…` (PASS locally) |
| 6 | Memory/CPU/fork bomb | Docker `--memory`, `--cpus`, `--pids-limit`, ulimits | Flags unit-tested as strings only. **NOT RUN against real Docker.** |
| 7 | Network, cloud metadata, host files, secrets | `--network none`, no mounts, empty env, read-only root, `--cap-drop=ALL`, non-root | **NOT RUN against real Docker.** |
| 8 | Read hidden tests | Hidden definitions never enter the sandbox; evaluated host-side; not in user API responses; not in the repo (seed holds a placeholder, real definition is loaded privately) | backend test `…never_expose…`, secret scan |
| 9 | Claim a pass through the API | Score/completion computed server-side; worker result validated; only the lease holder can post | `test_worker_queue.py` (PASS, in-memory) |
| 10 | Steal another learner's grade / submit outside enrolment | Ownership and enrolment checks, 404 for out-of-scope | existing backend tests (PASS, in-memory) |
| 11 | Abuse the queue | 6/min and 2 in flight per learner, 50 kB source cap, 3-claim dead-letter | tests PASS; global capacity not load-tested |
| 12 | Abuse the worker endpoint | Dedicated token, constant-time compare, disabled (503) when unset | PASS |

## Residual risks (unresolved)
* **Real container isolation has not been executed.** Until the Docker adversarial run passes, treat the sandbox as unverified.
* The parent/child split protects result integrity inside the container; a learner can still *claim* a variable's value in the report. The checks look at behaviour a program could legitimately produce, so this gives no advantage over writing the right program, but exercises with value-only checks should be designed with that in mind.
* A kernel or Docker escape would reach the worker host. Mitigation is a dedicated host with no credentials besides the worker token. gVisor/Firecracker are not in place.
* The worker token is a shared secret; rotate it as part of the rotation procedure.
