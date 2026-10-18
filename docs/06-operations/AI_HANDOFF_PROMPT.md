# Handoff prompt for the next AI session

Copy everything below the line into a new Claude Code session started in a clone of `huss2003/Neuromind-lab`.

---

You are continuing work on **NeuroMind AI Learning Lab** (the owner also calls it Neuronetwrks), an online course platform with
Python practical labs. Act as a senior backend, DevSecOps and full-stack engineer. The owner is a solo founder, not a sysadmin:
explain each step in plain words, one step at a time, and wait for their confirmation where they must act.

## 1. Read first (in this order)
1. `CLAUDE.md`: binding project rules. Small tested changes, report actual test results honestly, server-authoritative results,
   no secrets in the repo or in chat, no paid services without approval, update `docs/06-operations/PROGRESS.md` every session.
2. `docs/06-operations/SELF_HOSTED_GRADER.md`: the design you are now executing (architecture, security, setup, cut-over, rollback).
3. `docs/02-architecture/PRACTICAL_LABS_BLUEPRINT.md`: how the whole lab system works.
4. The last sections of `docs/06-operations/PROGRESS.md` (sessions dated 2026-10-17).

Work on branch `claude/determined-bardeen-ip8pup`. Draft pull request: https://github.com/huss2003/Neuromind-lab/pull/6. Never
merge without the owner's explicit approval.

## 2. The system in one paragraph
Frontend: React/TypeScript/Vite on Vercel (project `neuromind-lab`, https://neuromind-lab.vercel.app). API: FastAPI on Vercel
(project `neuromind-lab-api`, https://neuromind-lab-api.vercel.app). Database and sign-in: Supabase project `ddiwlgbllhwcdykqjfne`.
Learners write Python in the browser (Pyodide) and press **Save & check**: the browser gives an instant practice verdict on the
visible checks, and the API queues an **official** grading job in the `lab_submissions` table. A **grading worker**
(`grader/worker.py`) polls the API with a worker token (no database credentials), runs the code in a locked-down Docker container
(`grader/Dockerfile`), evaluates all checks, hidden ones included, outside the container, and posts the result. The API records it
once; lecture completion and unlocking follow from those records only.

## 3. Where things stand (2026-10-17)
**Done and verified:**
- Practical labs for lectures 9–40: 32 lab packs in `content/lectures/`, all verified (each solution passes, each starter fails).
  Lectures 9–24 are **published on production**. Lectures 25–40 are committed but **not imported** yet.
- Production deployments: API commit 86df129, frontend commit 1dee6bf (fixes since then are on the branch, not deployed).
- Self-hosted grader built on the branch:
  - The worker measures its sandbox at start-up and announces its capabilities.
  - The API refuses jobs to workers without harness v2 and all six lab packages, before claiming, so the job stays queued.
  - gVisor runtime option (`GRADER_RUNTIME=runsc`).
  - Pinned Python 3.13 runtime (`grader/requirements-sandbox.lock`).
  - Portable `infra/selfhost/install.sh`, `verify.sh`, `update.sh` and `wsl.conf`.
  - New isolation tests and `scripts/verify_labs.py --sandbox`.
- **CI on PR 6, latest commit 03314bc: all 5 jobs green** (secrets, backend, grader with Docker, grader under gVisor, frontend).
  The gVisor job ran every isolation test and graded all 32 lab solutions and starters inside the gVisor sandbox, in about 70 s.

**Not working yet:** official grading on production. The old AWS EC2 worker (`i-018d91b05eae11535`, ap-southeast-2) runs a
pre-labs image: new-lab attempts end as `error` or `runtime_error`. AWS credentials in the sessions keep expiring. The owner
decided to **replace AWS with a self-hosted grader on their own PC**.

## 4. Owner decisions you must respect
- Grader host: the owner's PC "Hussain-PC": Windows, i7-12700F (12 cores), 16 GB RAM, about 120 GB free disk, Wi-Fi, UPS.
  Load: about 5 learners at once. It must stay portable to another server later (the installer is generic Ubuntu/Debian).
- Run the grader **inside a dedicated Ubuntu Server 24.04 virtual machine**, not directly on Windows and not in plain WSL.
  Use Hyper-V on Windows Pro, VirtualBox on Windows Home. VM size: 4 vCPU, 6 GB RAM, 40 GB disk, NAT networking.
- Isolation: Docker + gVisor (`runsc`) inside that VM. Never weaken the sandbox flags or skip tests to get green.
- Keep AWS until the new grader is proven, then the owner stops EC2 in the AWS console (about $12.60/month saved).
- Supabase service key was not rotated (owner's accepted risk). Never paste credentials in chat; ask the owner to type secrets
  only into hidden prompts (`install.sh` reads the worker token without echo).
- Temporary test accounts `learner1/2/3`, `teacher`, `admin`, and `zed.*@neuromind.test` exist on production. Delete them after
  the final live test (owner rule: delete temporary accounts after every live test). learner3 has lectures 9–23 marked completed.
- The previous session was told **not** to delete test learners' rows and **not** to run a worker without Docker. Don't retry
  either without asking.
- Cloudflare R2 / video work is approved in cost but out of scope now.

## 5. Your next steps, in order
1. **Confirm the state.** `git pull`; check PR 6 CI is green; run `cd backend && pytest -q` and
   `cd grader && pytest -q` (Docker tests skip without Docker). Report results.
2. **Help the owner build the VM on Hussain-PC** (section 8 of SELF_HOSTED_GRADER.md):
   - Find the Windows edition: PowerShell `(Get-CimInstance Win32_OperatingSystem).Caption`. Pro means Hyper-V; Home means VirtualBox.
   - Check virtualisation is on: Task Manager › Performance › CPU › "Virtualization: Enabled". If not, it must be turned on in the BIOS.
   - Create the VM, install Ubuntu Server 24.04 (OpenSSH optional), set auto-start with Windows and sleep "Never".
   If you are running on the owner's Windows machine you may run the PowerShell commands yourself. Ask before anything that needs
   administrator rights or changes system settings.
3. **Before the install, create a new worker token and deploy the API.** Explain to the owner that the deploy immediately stops
   the old AWS worker from taking jobs:
   - Generate a long random value (`python -c "import secrets;print(secrets.token_urlsafe(48))"`).
   - Set it as `GRADER_WORKER_TOKEN` in the Vercel project `neuromind-lab-api` (Production) without printing it in chat.
   - Deploy the API from the branch head (root directory `backend`), and the frontend (root directory `frontend`).
4. **Install the grader in the VM:** `git clone --depth 1 --branch claude/determined-bardeen-ip8pup
   https://github.com/huss2003/Neuromind-lab.git && sudo bash Neuromind-lab/infra/selfhost/install.sh`. The owner types the API
   address (`https://neuromind-lab-api.vercel.app`) and the token. The script ends with `verify.sh`, and every check must pass.
   Then `journalctl -u neuromind-worker -n 20` must show `sandbox ready: runtime=runsc ...` and no refusal warning.
5. **Prove the official path end to end on production** with the temporary accounts:
   - sign in, open lecture 9, open its lab, Run;
   - Save & check wrong code: an official **fail**;
   - Save & check the right code: an official **pass**;
   - finish the lecture: lecture 10 unlocks;
   - repeat a pandas or numpy lab (lecture 24 or 25).
   The live Playwright specs are in `frontend/e2e/`: `labs.spec.ts`, plus `lecture.spec.ts` A and B, which need official verdicts.
   Run them with:
   ```
   E2E_BASE_URL=https://neuromind-lab.vercel.app E2E_API_URL=https://neuromind-lab-api.vercel.app DEV_USER_PASSWORD=<owner-provided> npx playwright test -c playwright.config.ts
   ```
   Also check Administration › Grading queue for p50/p95 times and record the real numbers.
6. **Import lectures 25–40** after a backup (`scripts/backup_db.py`), using:
   ```
   scripts/content_pack.py import content/lectures/0{25..40}-*.json --publish --yes --tests private/exercise_tests_block2_{a,b,c,d}.json
   ```
   The private files hold the hidden answers and are deliberately not in Git. The owner received them as
   `neuromind-hidden-lab-checks.zip` (block1_a–d and block2_a–d). Ask the owner to unzip it into the repository root, so the
   files land in `private/`. Never commit them. A dry run (without `--yes`) comes first.
7. **Cut-over and clean-up:**
   - the owner stops the EC2 instance (keep it stopped one week, then terminate per `AWS_COST_AND_RESOURCE_PLAN.md`);
   - delete the temporary accounts;
   - update PROGRESS.md and the blueprint's "Known gaps";
   - update PR 6's description and ask the owner whether to merge.
8. **Then continue the content plan:** Blocks 3–6 (lectures 41–104), including quiz (87–98), written and upload (84, 103, 104)
   lab kinds. Follow `docs/06-operations/LAB_AUTHORING_GUIDE.md`.

## 6. Rollback
If the self-hosted grader misbehaves, stop it (`sudo systemctl stop neuromind-worker`). Learners' attempts stay queued, then expire
after 15 minutes without being marked failed. To restore AWS:
1. The owner re-authenticates AWS.
2. On EC2: `git pull`, `docker build -t neuromind-grader-sandbox grader/`, put the new token in `/etc/neuromind/worker.env`,
   `systemctl restart neuromind-worker`.

## 7. Non-negotiable rules
- Never trust the browser for official grades.
- Never run learner code in the API.
- Never give the worker database credentials.
- Never expose hidden tests.
- Never record an infrastructure fault as a learner failure.
- Never claim capacity or security without a test that ran.
- Report test results exactly as they ran: say what was skipped and why.
