# Dead-letter runbook (attempts that could not be graded)

**What a dead letter is.** A submission whose grading was claimed by a worker three times without a result (the worker crashed, lost its lease, or the host stopped). The database marks it `status = 'error'` with `claim_count >= 3`. The learner sees "System error, not your fault"; no score is recorded and their best score is unchanged. A learner's own wrong or crashing code is **never** a dead letter: it is a normal result.

**Where you see it.** Administration → Overview (a warning appears) and Administration → Grading queue (the list). A CloudWatch alarm `neuromind-queue-backlog` fires if work waits more than 120 s; `neuromind-worker-down` fires if the worker service stops.

## Steps
1. **Check the worker first.** Administration → Grading queue: are jobs waiting or running? On the host (Systems Manager session): `systemctl status neuromind-worker`, `journalctl -u neuromind-worker -n 100 --no-pager`. Look for: Docker not running, disk full, out of memory, the API unreachable, an expired worker token.
2. **Fix the cause before retrying.** Typical causes and fixes:
   - Worker stopped: `sudo systemctl restart neuromind-worker`.
   - Disk full: `docker system prune -f`, then restart.
   - API unreachable or wrong token: confirm `API_BASE_URL` and the SSM parameter `/neuromind/worker-token` match the API's `GRADER_WORKER_TOKEN`.
   - A job that kills the worker every time (for example a payload that exhausts memory beyond the container limit): do **not** retry it; go to step 4.
3. **Retry.** In Administration → Grading queue choose **Retry** on the attempt and confirm. The server resets it to `queued` with a fresh set of three claims, only if it really is a dead letter. The action is recorded in the audit log as `admin.submission_requeued`.
4. **If it fails again,** leave it. Tell the learner (their attempt history shows "System error"): they can submit again, which creates a new attempt. Open an issue report with the attempt id and the worker log lines. Do not edit scores or statuses by hand.
5. **Record it.** Note the cause and fix in the issue report (Administration → Issue reports) so repeated causes are visible.

## What not to do
- Do not change a status or score in the database by hand. There is no administrator endpoint that edits an official score, deliberately.
- Do not retry in a loop: three claims per attempt is the bound that keeps a poisonous job from stalling the queue.

## Measuring
Queue wait (submission until a worker first claims it) and execution time (claim until result) are measured from the submission timestamps and shown in Administration → Grading queue and Overview. The worker host publishes `QueueWaitP95Seconds` and `ExecutionP95Seconds` to CloudWatch every minute.
