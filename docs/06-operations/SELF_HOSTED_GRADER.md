# Self-hosted grader (replaces the AWS grading host)

Status: designed and implemented on branch `claude/determined-bardeen-ip8pup`, 2026-10-17. Not yet installed on the owner's machine.
Scope: only the machine that runs learner code changes. The website (Vercel), the API (Vercel), the database and sign-in
(Supabase), the grading queue, the progress rules and the browser labs stay exactly as they are.

## 1. Decision

| Question | Decision |
|---|---|
| Where | A dedicated Linux virtual machine on the owner's PC "Hussain-PC" (i7-12700F, 16 GB, Windows, Wi-Fi, UPS). The same installer works on any Ubuntu/Debian server, so the grader can move later without code changes. |
| Isolation | Docker with **gVisor** (`runsc`) as the container runtime, plus the existing locked-down container settings. Inside a VM, so the Windows system and personal files are a second boundary away. |
| Why not plain Docker | A container shares the host kernel; one kernel bug is enough to escape. gVisor answers learner system calls in its own user-space kernel, so learner code never talks to the real kernel directly. |
| Why not Firecracker | Strongest option, but needs KVM, a custom image pipeline and much more upkeep for 5 concurrent learners. Revisit if the platform grows or handles sensitive data. |
| Why not WSL directly | WSL mounts the Windows drives and can start Windows programs by default. Supported only with `infra/selfhost/wsl.conf` applied; the installer refuses otherwise. A separate VM is the recommended set-up. |
| Cost | No hosting fee. Electricity only (section 9). AWS (about $12.60/month) is switched off after the cut-over. |

## 2. Architecture

```
 Learner browser ──HTTPS──► API (FastAPI on Vercel) ──service role──► Supabase PostgreSQL
   (Pyodide practice,          │  auth, ownership, lab unlock rules,      lab_submissions = durable queue
    instant browser check)     │  decides and records official results    (queued → running → final)
                               ▲
                               │ HTTPS, outbound from the PC only, X-Worker-Token (no database credentials)
                               │ claim / heartbeat / result / release
 ┌─ Hussain-PC (Windows) ───────┼──────────────────────────────────────────────────────────────┐
 │ ┌─ Linux VM (Ubuntu 24.04) ──┼────────────────────────────────────────────────────────────┐ │
 │ │  neuromind-worker (systemd, user nmworker)                                              │ │
 │ │   • probes the sandbox at start-up and announces what it can run                       │ │
 │ │   • runs each job in a fresh container, evaluates ALL checks (hidden ones too) here    │ │
 │ │            │ docker run --runtime=runsc --network none --read-only --cap-drop=ALL ...    │ │
 │ │            ▼                                                                            │ │
 │ │   ┌ gVisor sandbox (one per job, removed afterwards) ───────────────────────────────┐   │ │
 │ │   │ learner program as user nobody; only its lab's data files in a 48 MB /tmp;      │   │ │
 │ │   │ no network interface except loopback; practice API simulated in-process         │   │ │
 │ │   └─────────────────────────────────────────────────────────────────────────────────┘   │ │
 │ └────────────────────────────────────────────────────────────────────────────────────────┘ │
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

Nothing connects **into** the PC. The worker only calls the API, so no router port-forwarding, no public IP and no tunnel
are needed, and the home network is never exposed.

## 3. Components and responsibilities

| Component | Trusted? | Does | Never does |
|---|---|---|---|
| API (`backend/app/routers/exercises.py`, `worker.py`) | yes | authenticates the learner, checks the lab is unlocked, stores the attempt, hands jobs to capable workers, validates and records the result once, updates progress | run learner code |
| Database (`lab_submissions`, migration 0006 `claim_next_submission`) | yes | durable queue with leases and a claim limit | — |
| Worker (`grader/worker.py`) | yes, holds one secret: the worker token | claims, starts the sandbox, evaluates checks, posts results, hands jobs back on infrastructure trouble | hold database or Supabase credentials |
| Evaluator (`grader/grader_service/evaluate.py`) | yes | compares the run's evidence with the expected answers | send expected answers into the sandbox |
| Sandbox image (`grader/Dockerfile`, `requirements-sandbox.lock`) | **no** (runs learner code) | Python 3.13, pinned numpy, pandas, matplotlib, scikit-learn, pillow, requests, the harness and the practice-API simulator | contain secrets, tests or app code |
| Harness (`grader/sandbox/harness.py`) | parent trusted, child untrusted | runs the learner program in a child process, writes the lab files, evaluates probe expressions, reports with a per-run secret nonce | let the learner forge the report |

## 4. Job lifecycle (existing states, unchanged)

`queued` → `running` (claimed, 60 s lease, renewed by heartbeat) → one final state:

| State | Meaning | Counts against the learner? |
|---|---|---|
| `passed` / `failed` | the program ran and the checks decided | yes, a legitimate result |
| `runtime_error` | the learner's program raised an exception | yes (score 0) |
| `timeout` | the learner's program exceeded the lab's time limit | yes |
| `error` | infrastructure problem (sandbox unavailable, unreadable result, 3 failed claims) | **no**: shown as "not judged, please submit again" |
| `expired` | waited too long in the queue (15 min, e.g. the PC was off) | **no** |

Rules that already hold and are kept: a result is accepted only from the worker holding the lease; a duplicate or late result
after a final state changes nothing; every attempt is its own row, so an old result can never complete a newer attempt;
progress is recomputed only from these rows.

**New:** before a job is handed out, the API checks the worker's announced capabilities (section 5). An outdated worker gets
no job at all, so it can no longer turn missing libraries into `runtime_error` for a learner (the failure seen on 2026-10-17).

## 5. API contract (worker ↔ API)

All under `/api/v1/internal/grader`, header `X-Worker-Token`, HTTPS.

| Call | Request | Response |
|---|---|---|
| `POST /claim` | `{worker_id, harness_version, packages: {name: version}, runtime, python}` | `200` job: `{submission_id, claim_count, lease_seconds, source_code, pass_threshold, timeout_seconds, limits, packages, files, tests}`; `204` no job; `204` + `X-Claim-Refused: worker-too-old \| missing-packages:<names>` when the worker cannot grade the labs (the job stays queued) |
| `POST /jobs/{id}/heartbeat` | `{worker_id}` | `200` lease extended, `409 LEASE_LOST` |
| `POST /jobs/{id}/result` | `{worker_id, result}` | `200 {accepted}`; idempotent |
| `POST /jobs/{id}/release` | `{worker_id}` | `200`; job back to the queue (bounded by 3 claims) |
| `GET /health` | — | queue depth, oldest wait, p95 wait/execution for the last hour |

Capabilities are measured, not declared: at start-up the worker runs a locked-down container from the sandbox image and reads the
installed package versions (`grader_service/runner.py: probe_image`). If that fails, the worker exits and systemd retries; it never
claims jobs with a broken sandbox. Required today: harness version ≥ 2 and all six lab packages.

## 6. Security configuration

Every learner run (`grader_service/runner.py: docker_command`):

| Threat | Control (enforced outside the learner process) |
|---|---|
| Internet, cloud metadata, home network, the API, Supabase | `--network none`: the container has only a loopback interface. Practice API answered in-process by `labmock`. |
| Host kernel exploits | gVisor `--runtime=runsc` (user-space kernel); VM boundary to Windows |
| Host files, other learners' files, docker socket, SSH keys | no mounts; read-only root filesystem; fresh container and fresh `/tmp` per job, removed afterwards |
| Secrets | empty environment except harmless runtime variables; the worker token never enters the container |
| Hidden tests | stay in the worker; only probe expressions enter; expected values never do |
| Forged results | the trusted parent reports with a random per-run nonce the learner process cannot read |
| Privilege escalation | user 65534 (nobody), `--cap-drop=ALL`, `no-new-privileges` |
| Infinite loops | per-lab timeout in the worker plus a `timeout -s KILL` inside the container |
| Memory bombs | `--memory` = `--memory-swap` (128 MB, 384 MB for scientific labs, max 1024) |
| Fork bombs | `--pids-limit=48` |
| Output and disk floods | output capped at 20 KB, max file size 5 MB, `/tmp` 48 MB and `noexec` |
| Too many runs at once | `WORKER_CONCURRENCY` (default 2) |

Machine level (`infra/selfhost/install.sh`): dedicated `nmworker` account without login shell, systemd hardening
(`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, kernel protections), firewall denying all inbound
traffic, automatic security updates, token in a root-only file entered without echo.

**Residual risks (stated honestly):** passing tests do not prove a sandbox unbreakable. The `nmworker` account can start containers,
which equals control of the VM; that is why the VM must hold nothing else. A gVisor escape would land inside the VM, not on Windows.
A shared home connection and a single PC mean downtime delays official results (they are not lost and nobody is failed).

## 7. Runtime manifest

`grader/requirements-sandbox.lock` (Python 3.13): numpy 2.5.4, pandas 2.3.3, matplotlib 3.11.2, scikit-learn 1.9.1, pillow 11.3.0,
requests 2.34.2 and their exact dependencies. These are the versions all 32 lab packs (lectures 9–40) were verified with. The image
is built from this lock with `--no-deps` and `pip check`; nothing is downloaded while learner code runs. Changing a version means
re-running `scripts/verify_labs.py` for every lab. The browser runtime (Pyodide 0.27.4) ships its own versions; the browser check is
practice only, the official result always comes from this image.

## 8. Setting it up on Hussain-PC

1. **Virtual machine** (one of):
   - Windows Pro: enable Hyper-V (Settings › Optional features › More Windows features › Hyper-V), create a Generation 2 VM.
   - Windows Home: install VirtualBox (free).
   Give it 4 virtual CPUs, 6 GB memory, a 40 GB disk, NAT networking (the default). Install **Ubuntu Server 24.04 LTS**.
2. **Keep it running**: Windows power plan › sleep: Never. Hyper-V: VM › Settings › Automatic start action: Always start.
   VirtualBox: a Task Scheduler task at start-up running `VBoxManage startvm "neuromind-grader" --type headless`.
   Set Windows Update active hours so restarts happen at night.
3. **Install** inside the VM:
   ```
   sudo apt-get install -y git
   git clone --depth 1 --branch claude/determined-bardeen-ip8pup https://github.com/huss2003/Neuromind-lab.git
   sudo bash Neuromind-lab/infra/selfhost/install.sh
   ```
   It asks for the API address and the worker token (the new token is created during the cut-over, step 10.2).
4. The installer ends by running `infra/selfhost/verify.sh` (section 11). Every check must pass.

## 9. Capacity and cost

| Item | Estimate (to be confirmed by measurement on the machine) |
|---|---|
| Today's load | about 5 learners at once, i.e. a few submissions per minute at peak |
| Time per grading | about 1–3 s for plain Python, 3–6 s for pandas or scikit-learn labs, plus gVisor overhead |
| Memory per run | up to 128 MB, or 384 MB for scientific labs |
| Concurrency | 2 at once by default; the VM can take 4 |
| Disk | sandbox image about 600 MB; 40 GB VM disk is plenty |
| Electricity | if the PC is on anyway: close to nothing extra. If it would otherwise be off: a desktop like this idles at roughly 40–60 W, about 30–45 kWh a month; multiply by the local tariff. |

These figures are estimates. Real queue wait and execution times appear in Administration › Grading queue (p50/p95) once the worker runs.

## 10. Cut-over and rollback

1. Deploy the API with the capability check (this branch). From then on the old AWS worker is refused jobs (it sends no
   capabilities), so it can no longer fail learners. New attempts wait in the queue until a capable worker runs.
2. Create a new worker token: a long random value, stored only as `GRADER_WORKER_TOKEN` in the Vercel API project and entered into
   the installer. The old AWS worker then cannot even authenticate.
3. Install the VM (section 8); `verify.sh` must pass.
4. End-to-end on production with temporary accounts: sign in, open lecture 9, open its lab, run, Save & check a wrong answer
   (official fail), then the right one (official pass), finish the lecture, see lecture 10 unlock. Repeat for a pandas lab.
5. Stop the EC2 instance in the AWS console (owner). Keep it stopped one week, then terminate it and its parameter, role and alarms
   (AWS_COST_AND_RESOURCE_PLAN.md lists them).

**Rollback:** start the EC2 instance, update it (`git pull`, `docker build`, `systemctl restart neuromind-worker`) and give it the new
token. Queued work is picked up by whichever capable worker runs; nothing in the database changes.

## 11. Tests

| Where | What | How |
|---|---|---|
| Every push (CI `grader`) | harness, evaluator, worker loop, runtime settings, Docker isolation tests with plain Docker | `cd grader && pytest` |
| Every push (CI `grader-gvisor`) | the same isolation tests **under gVisor**, and every lab's reference solution graded inside the gVisor sandbox (hidden checks are private, so PARTIAL) | `GRADER_RUNTIME=runsc` |
| Every push (CI `backend`) | capability refusal keeps jobs queued, idempotent results, leases, dead letters, progress | `cd backend && pytest` |
| On the machine | everything above against the real VM, plus service health | `sudo bash /opt/neuromind/infra/selfhost/verify.sh` |
| Production | the journey in 10.4 with temporary accounts, deleted afterwards | live Playwright specs in `frontend/e2e` |

Isolation tests (grader/tests/test_docker_sandbox.py) try, and must be denied: the internet, cloud metadata, the home router and
private ranges, the Docker host, the API and Supabase; any network interface but loopback; reading host paths or the Docker socket;
writing the image; root; executing files in `/tmp`; filling the disk; seeing another job's files; finding the hidden expected
answer; memory and fork bombs; endless output; outliving the time limit even when the worker is killed. Also checked: numpy, pandas,
matplotlib and scikit-learn work, and the practice API answers while real hosts stay blocked. Attack tests in
`test_adversarial.py` cover forged results.

## 12. Moving to another server later

The grader has no state: the queue is in the database. On any Ubuntu 22.04/24.04 or Debian 12 machine (a rented server, a
second PC, ARM or x86): run `install.sh` with the same token, run `verify.sh`, then stop the old one (`systemctl disable --now
neuromind-worker`). Two capable workers can also run at the same time: leases prevent double grading.

## 13. Operations

- Update: `sudo REF=<branch> bash /opt/neuromind/infra/selfhost/update.sh` (stops cleanly, rebuilds, re-verifies).
- Logs: `journalctl -u neuromind-worker -f`. The start-up line `sandbox ready: runtime=runsc ...` confirms the runtime.
- A refused worker logs `WARNING: the API refuses to give this worker jobs (...)`: rebuild the image with `update.sh`.
- Alerts: Administration › Overview shows queue depth and dead letters; DEAD_LETTER_RUNBOOK.md applies unchanged.
- Token rotation: new value in Vercel and in `/etc/neuromind/worker.env`, then `systemctl restart neuromind-worker`.

## 14. Interim host: GitHub Actions (owner decision 2026-10-17)

The VM on Hussain-PC is postponed: Hyper-V could not be enabled (Windows component store corruption) and the disk was nearly full.
Until a PC or VPS grader exists, `.github/workflows/grader-worker.yml` runs the same worker on a GitHub-hosted runner.

- **Same sandbox:** Docker with gVisor (`GRADER_RUNTIME=runsc`) and the pinned image, exactly as the CI `grader-gvisor` job tests.
  Two jobs at a time (`WORKER_CONCURRENCY=2`; the runner has 4 vCPU and 16 GB).
- **Always on:** each run serves about 5 h 40 min, then stops gracefully. A schedule every 5 h and the `grader-worker`
  concurrency group keep the next run queued behind the active one. Hand-over gap: the ~3 min set-up; attempts wait in the queue.
- **Settings:** repository variable `GRADER_API_BASE_URL` (`https://neuromind-lab-api.vercel.app`) and secret
  `GRADER_WORKER_TOKEN` (same value as in the Vercel API project). Start or restart: Actions › grader-worker › Run workflow.
- **Cost:** free (public repository, standard runner).
- **Public logs:** the worker prints only start-up, refusal and stray-container lines: no learner code, no hidden checks, and the
  token is masked. Hidden checks still reach the worker only through the authenticated claim response.
- **Risks, accepted by the owner:** GitHub's terms intend Actions for building, testing and deploying the project; running a
  production service may get Actions disabled for the repository without notice. GitHub also pauses scheduled workflows after 60
  days without repository activity. If either happens, grading stops (attempts stay queued, then expire, never marked failed):
  start a run by hand, or move to a VM/VPS with `install.sh` (section 12).
- **Check it:** the run log shows `sandbox ready: runtime=runsc ...` and no `WARNING: the API refuses ...` line.
