# NeuroMind Practical Labs — complete blueprint

Status: 2026-10-17. Describes what is built and deployed on branch `claude/determined-bardeen-ip8pup`.
Related documents: product rules `docs/01-product/PRACTICAL_LABS_SPEC.md`, authoring rules `docs/06-operations/LAB_AUTHORING_GUIDE.md`,
pack format `docs/06-operations/CONTENT_PACK_GUIDE.md`, routes `API_SPEC.md`, tables `DATA_MODEL_AND_DATABASE_SCHEMA.md`,
course-document differences `docs/01-product/COURSE_DOCUMENT_CHANGE_NOTES.md`.

---

## 1. What the Practical Labs are

Every lecture from 9 to 104 of the 1-year *AI Creator Program* has one practical lab. A learner opens **Practical labs** in the
website, sees the course split into 13 months, opens the lab of a lecture they have reached, writes Python in the browser and presses
**Save & check**. The work is checked instantly in the browser, then officially on the server. On failure a popup explains what is
wrong; the bulb gives up to 3 hints; after 3 hints the learner can **Redo** the lab. Teachers see every result and mark the written
and upload labs. The administrator sees every check, hidden ones included.

Four kinds of lab exist:

| Kind | Used for | How it is judged | Result |
|---|---|---|---|
| `code` | most lectures (Python, data, ML, AI APIs) | automatic checks on the server | pass / fail |
| `quiz` | exam lectures 87–98 | the server marks the answers | pass / fail |
| `written` | design and reflection tasks (e.g. lecture 27) | the teacher marks it from a rubric | pass / fail, set by the teacher |
| `upload` | deployment and presentation lectures 84, 103, 104 | the teacher marks a link plus a checklist | pass / fail, set by the teacher |

## 2. Architecture at a glance

```
                         ┌──────────────────────────────────────────────────────────────┐
  Learner / Teacher /    │  Browser (React 19 + TypeScript, Vite build, Vercel CDN)    │
  Administrator  ───────▶│  • Practical labs pages, lab page, Save & check popup       │
                         │  • Monaco code editor                                        │
                         │  • Web Worker running Pyodide 0.27.4 (Python in WebAssembly) │
                         │      numpy, pandas, matplotlib, scikit-learn, pillow, requests│
                         │      + nm_evaluate.py (same checker as the server)           │
                         │      + labmock.py (simulated practice API, no internet)      │
                         └───────────────┬───────────────────────────┬──────────────────┘
                     sign-in (JWT)       │                           │  HTTPS + Bearer JWT
                                         ▼                           ▼
                ┌────────────────────────────┐      ┌──────────────────────────────────────┐
                │  Supabase Auth             │      │  NeuroMind API (FastAPI, Python)      │
                │  (email + password, MFA)   │◀────▶│  Vercel serverless, region hnd1       │
                └────────────────────────────┘ token│  • verifies the token, reads the role │
                                                    │  • lab rules: reach, hints, redo,    │
                                                    │    quiz marking, reviews, results    │
                                                    │  • grading queue (claim/lease/retry) │
                                                    └──────┬───────────────────────┬────────┘
                                         service-role key  │                       │  X-Worker-Token
                                         (server only)     ▼                       ▲  (HTTPS, worker polls)
                                     ┌──────────────────────────────┐   ┌──────────────────────────────────┐
                                     │ Supabase PostgreSQL (Tokyo)  │   │ Grader worker (AWS EC2 t4g.micro, │
                                     │ lectures, labs, checks,      │   │ Sydney, no inbound ports)        │
                                     │ submissions, hints, reviews, │   │ • claims a job, runs the code in  │
                                     │ progress, audit (RLS on)     │   │   a locked Docker container       │
                                     └──────────────────────────────┘   │ • evaluates ALL checks (hidden    │
                                                                        │   ones too) outside the container │
                                                                        │ • posts the result back           │
                                                                        └──────────────────────────────────┘
```

Three places run Python, each with a different job:

1. **The browser (Pyodide)** — instant feedback. Runs **Run** and the quick check of the *visible* checks. Never official.
2. **The grader sandbox (Docker on EC2)** — the official result. Runs the learner's program with no network and strict limits.
3. **The grader host process** — evaluates every check, including hidden ones, *outside* the sandbox, so the learner's code never
   sees an expected answer.

## 3. Technology stack

| Layer | Technology | Where it runs | Cost |
|---|---|---|---|
| Frontend | React 19, TypeScript 5.7 (strict), Vite 6, React Router 7, TanStack Query 5, Monaco editor 4.7 | Vercel (project `neuromind-lab`) | free tier |
| Browser Python | Pyodide 0.27.4 in a Web Worker, loaded from the jsDelivr CDN; packages loaded on demand | learner's browser | free |
| API | FastAPI 0.115, Pydantic 2, httpx | Vercel serverless (project `neuromind-lab-api`, Tokyo region) | free tier |
| Identity | Supabase Auth (email/password, optional two-step verification) | Supabase | free tier |
| Database | Supabase PostgreSQL with row-level security, numbered SQL migrations 0001–0009 | Supabase project `ddiwlgbllhwcdykqjfne` (Tokyo) | free tier |
| Grader | Python worker + Docker sandbox image `python:3.12-slim` with numpy, pandas, matplotlib, scikit-learn, pillow, requests | AWS EC2 `i-018d91b05eae11535`, t4g.micro, ap-southeast-2 | about $12.6/month, budget alarm at $15 |
| Practice API | `labmock.py`, an in-process simulator of `https://api.neuromind.lab/v1` | inside the browser worker and inside the sandbox | free |
| Tests | pytest (backend, grader), Vitest + Testing Library (frontend units), Playwright + axe (mocked UI suite and live suite) | developer machine and GitHub Actions | free |
| Monitoring | structured JSON logs, CloudWatch alarms for queue backlog and worker down, SNS e-mail to the owner | AWS | inside the budget |

## 4. Repository map (lab-related parts)

```
content/
  course.json                     13 month-modules, 104 lecture titles and each lecture's practical project (from the course document)
  lectures/NNN-title.json         one pack per lecture: intro, lab, visible checks, hints, data files, reference solution
private/ (git-ignored)            hidden check definitions per block, database backups
database/migrations/0009_practical_labs.sql
backend/app/
  routers/labs.py                 GET /labs (catalogue)
  routers/exercises.py            lab view, hints, redo, submissions (all four kinds)
  routers/teacher.py              review queue, rubric decision, submission detail
  routers/admin_ops.py            every check of a lab for the administrator
  routers/admin_content.py        validate / import packs from the browser
  routers/worker.py               the grading queue the worker talks to
  services/labs.py                lab state, quiz marking, upload validation, limits, visible checks, data files
  content_pack.py                 pack schema v2 and the rows it becomes
grader/
  worker.py                       claim → run → evaluate → result loop, with heartbeat and release
  grader_service/runner.py        the exact `docker run` command and the subprocess runner (tests only)
  grader_service/evaluate.py      every check kind, run on the host
  sandbox/harness.py              runs inside the container: parent/child processes, data files, probes, practice API switch
  sandbox/labmock.py              the practice API simulator and helpers
  Dockerfile                      the sandbox image
frontend/
  public/pyodide-worker.js        the browser Python worker
  public/py/nm_evaluate.py        byte-identical copy of grader evaluate.py (a test enforces it)
  public/py/labmock.py            byte-identical copy of the practice API (a test enforces it)
  public/py/nm_quickcheck.py      runs a program plus the visible checks in the browser
  src/pages/Labs.tsx              Practical labs catalogue
  src/pages/LabPage.tsx           one lab; code, quiz, written and upload experiences
  src/features/lab/ExerciseLab.tsx  editor, Run, Save & check, bulb hints, Redo, results, history
  src/features/lab/CheckDialog.tsx  the Save & check popup
  src/features/lab/usePyodide.ts  owns the worker, time limits, quick check
  src/pages/TeacherReviews.tsx, TeacherSubmission.tsx   teacher marking
  src/pages/admin/AdminContent.tsx  admin content table with "Show checks"
scripts/
  content_pack.py                 validate / import / export packs; create course records
  verify_labs.py                  proves each solution passes and each starter fails
  backup_db.py, create_dev_users.py
```

## 5. How everything is connected

### 5.1 Identity and roles
1. The browser signs in with Supabase Auth and receives a short-lived access token (JWT).
2. Every API call carries `Authorization: Bearer <token>`.
3. The API verifies the token with Supabase, then reads the user's **role** (learner, teacher, admin) from the `profiles` table using
   the server-only service-role key. The browser never sends its role, score or result; the server decides them.
4. Verified users are cached for 30 seconds; a deactivated account is refused within that window.

### 5.2 Content
1. Authors write one JSON pack per lecture (`content/lectures/`). Visible checks carry their definition in the pack; hidden checks
   live only in a git-ignored private file.
2. `scripts/content_pack.py validate` checks the schema; `scripts/verify_labs.py` runs the reference solution (must pass every check)
   and the starter code (must fail at least one) through the real checker.
3. `scripts/content_pack.py import … --publish --yes` (or Administration › Content › Import) writes deterministic rows: lecture,
   sections, lab (`lecture_exercises`), checks (`exercise_tests`), quiz questions (`lab_questions`). Re-importing updates the same rows.
4. A database backup is taken before any production import.

### 5.3 The grading queue (official results)
1. **Save & check** posts the code to `POST /exercises/{id}/submissions`. The API stores the attempt as `queued` and answers 202.
2. The worker on EC2 polls `POST /internal/grader/claim` every few seconds with its `X-Worker-Token`. It has no open ports; it only
   calls out.
3. The API hands out the oldest queued attempt with a 60-second lease: code, all checks (hidden included), the lab's data files,
   packages and limits.
4. The worker starts a fresh container (section 7), runs the program, collects stdout, the exception if any, the named variables and
   the probe values, then evaluates every check **on the host**.
5. It posts the result to `/jobs/{id}/result`. The API stores it once (a late or duplicate result is ignored), and the learner's
   page, which polls `GET /submissions/{id}`, shows it.
6. A heartbeat keeps the lease alive. If the worker dies, the lease expires and another claim retries the job; after 3 claims the
   attempt becomes a dead letter that the administrator can requeue.

### 5.4 Data flow of secrets
- The service-role key and the worker token exist only in the API's environment and in AWS Parameter Store. They are never in the
  frontend bundle, never in the sandbox, never in Git.
- Hidden check definitions leave the database only towards the worker (and to the administrator's "Show checks" view).

## 6. How a lab works, step by step

### 6.1 Finding a lab
- **Practical labs** (`/labs`) calls `GET /labs`. The API groups published labs by month-module and gives each a state computed from
  server records only: `locked`, `not_started`, `in_progress`, `awaiting_review`, `needs_retry`, `passed`.
- A lab is open only when its lecture is reached: earlier prerequisite lectures completed, and, for lectures with knowledge checks
  (9–12 today), those checks answered. Locked labs show a disabled **Locked** button.

### 6.2 Inside a code lab
The page shows the task, constraints, "you will pass when…", the files provided, worked examples, and the editor.
- **Run** executes the program in the browser and shows the output. It never counts. Programs that run too long are stopped
  (5 s, or 30 s for labs using scientific packages) and the worker is replaced.
- **Save & check**:
  1. The draft is saved on the server.
  2. In parallel: the browser runs the program plus the *visible* checks with the same checker code as the server (quick check), and
     the code is sent for the official check.
  3. The popup first says "Looks right in the browser — confirming officially…" or lists what failed. When the official verdict
     arrives it replaces the quick one.
  4. **Pass**: "Lab passed" and the result is recorded. **Fail**: the failed checks and the exception line; **Dismiss** closes,
     **Show hint** shows how to fix each failed check (free). If the official checker itself has a problem, the popup says so and keeps
     the browser's findings visible.
- **Bulb (Hint n/3)**: reveals the lab's general hints in order. The server allows at most 3 per cycle (a fourth answers 409).
- **Redo**: available once the 3 hints are used and the lab is not passed. Starts a new cycle with fresh hints and the starter code;
  the attempt history is kept.
- Results are pass/fail. Each attempt records the number of checks passed and the hints used.

### 6.3 Quiz labs (exam lectures)
Questions come from `lab_questions`; the correct answer never leaves the server. The server marks the answers on submission and returns
per-question right/wrong with explanations, never the right option. Today a quiz passes when every answer is correct; a configurable
pass mark for the exam lectures will be set when Block 6 is authored.

### 6.4 Written and upload labs
The learner sends text (written) or an https link with every checklist item ticked (upload). The attempt waits as
`awaiting_review`. The teacher opens **Reviews**, sees the answer and the rubric, gives points per criterion (capped by the
rubric), pass or fail and feedback. That decision becomes the official result; re-marking replaces it.

### 6.5 Teachers and the administrator
- Teachers see their assigned learners' lab results and attempt details, and the review queue.
- The administrator sees everything, can import and publish packs, and can open **Show checks** to see every check of a lab with its
  definition, hidden ones included (owner decision).

## 7. Safety of learner code

| Control | Browser (Pyodide) | Server sandbox (Docker) |
|---|---|---|
| Network | `requests` only reaches the simulated practice API; any other host raises "Internet access is disabled in the lab" | `--network none`; the practice API is in-process |
| Time | 5 s / 30 s, worker terminated | per-lab limit (5 s default, 20 s with scientific packages) plus a hard `timeout -s KILL` inside the container |
| Memory | browser tab limits | 128 MB default, 384 MB with scientific packages, no swap |
| Processes / files | n/a | `--pids-limit=48`, 128 open files, 5 MB max file size, read-only root, 48 MB `/tmp` tmpfs with `noexec` |
| Privileges | n/a | user 65534 (nobody), all capabilities dropped, `no-new-privileges` |
| Secrets | none in the browser | no environment from the host, no mounts, a per-run nonce the learner's process cannot read |
| Hidden answers | never sent to the browser | evaluated on the host; only the probe *expressions* enter the container, never expected values |
| Output | shown as text, never HTML | truncated at 20 KB, shown as text |

## 8. The practice API (no real internet, no cost)

`https://api.neuromind.lab/v1`, test key `nm-test-key-123`. Simulated by `labmock.py` in the browser and in the sandbox, identical in
both (a test checks the copies are byte-identical). Deterministic: the same request always gives the same answer.

Endpoints: `GET /weather`, `GET /books`, `GET /news/headlines`, `GET /secure/profile` (needs the key in the header), `GET /flaky`
(fails twice, then works), `GET /search`, `POST /chat`, `POST /generate`, `POST /sentiment`, `POST /entities`, `POST /embeddings`,
`POST /ocr`, `POST /vision/classify`, `POST /vision/detect`, `POST /vision/ask`. Helpers: `tokenize`, `embed`, `cosine`,
`VectorIndex`, `chunk_text`. It replaces every real weather, news and AI service named in the course document.

## 9. Data model (lab part)

| Table | Holds |
|---|---|
| `courses`, `modules`, `lectures` | the course, 13 month-modules, 104 lectures (status draft/published) |
| `lecture_segments` | the lecture's sections; a lab-only lecture has an intro and the exercise section |
| `lecture_exercises` | the lab: kind, scoring, instructions, starter code, hints, packages, data files, limits, rubric, checklist, hint cap |
| `exercise_tests` | each check: definition, hidden flag, label, remediation |
| `lab_questions` | quiz questions and the server-only correct option |
| `lab_submissions` | every attempt: code or answers, status, checks passed, hints used, feedback |
| `exercise_hint_reveals`, `lab_hint_state` | hints shown per cycle, current cycle and Redo count |
| `lab_reviews` | the teacher's rubric decision for written/upload attempts |
| `lecture_sessions`, `student_progress` | lecture progress and completion, which unlock the next lectures |
| `audit_logs` | hint reveals, Redo, imports, teacher decisions (never check definitions) |

Row-level security is on for every table; the API uses the service role and enforces ownership in code.

## 10. Feature list

**Learner**: Practical labs catalogue by month with states and progress; lab page with task, files provided, examples, success
criteria; Monaco editor with a simple-editor fallback; Run in the browser; Save & check with instant and official verdicts; error popup
with Dismiss and free Show hint; bulb hints capped at 3; Redo with history kept; attempt history; quiz, written and upload labs;
teacher decisions and feedback visible; numpy/pandas/matplotlib/scikit-learn/pillow/requests in the browser; the practice API;
keyboard and screen-reader friendly (axe checks in the test suite).

**Teacher**: dashboard; learner results per lab; attempt detail with code, checks and hints used; review queue; rubric marking
with feedback.

**Administrator**: content table with publish/unpublish; pack validation and import from the browser; **Show checks** for every lab;
grading queue health and dead-letter requeue; audit log.

**Content pipeline**: one pack per lecture; schema validation; solution/starter verification; deterministic idempotent import;
export from the database; course records from the course document.

## 11. Deployment and operations

| Part | How it is deployed | Current version |
|---|---|---|
| Frontend | Vercel production deployment from the branch | commit 2c8fd5e |
| API | Vercel production deployment from the branch | commit 86df129 |
| Database | SQL migrations applied by hand after a backup | 0009 applied 2026-10-16 |
| Content | `scripts/content_pack.py import --publish --yes` after a backup | lectures 9–24 published 2026-10-17 |
| Grader host | `git pull`, `docker build -t neuromind-grader-sandbox grader/`, `systemctl restart neuromind-worker` through AWS Systems Manager | **still the pre-labs version** (see section 13) |

CI (GitHub Actions) on every push: secret scan, ruff, pack validation, backend tests, grader tests including the real Docker sandbox,
frontend lint, typecheck, unit tests, build and the mocked UI suite with accessibility checks.

## 12. Testing

| Suite | What it covers | Last result |
|---|---|---|
| Backend pytest | lab rules, hints and Redo, quiz marking, reviews, admin checks view, queue, pack import | 182 passed |
| Grader pytest | harness, probes, data files, practice API, check kinds, worker loop; Docker-backed tests run in CI | 56 passed, 11 skipped locally |
| Pack verification | every solution passes, every starter fails, no hidden check inline | lectures 9–28 and 37–40: 0 problems |
| Frontend unit (Vitest) | components incl. the Save & check popup | 40 passed |
| Mocked UI (Playwright + axe) | catalogue, popup, hints and Redo, quiz, written review, upload, admin checks, accessibility | 68 passed |
| Live (Playwright against production) | catalogue, browser quick check, hints/Redo, requests and numpy labs, teacher and admin views | partly run; see section 13 |

## 13. Known gaps (2026-10-17)

- **Official grading is not working yet for the new labs.** The EC2 worker still runs the image and harness from before the labs
  work, so it answers every lab attempt with "test configuration problem". The fix is the host update in section 11; it needs the AWS
  connection to be re-authenticated. The browser quick check works now.
- Because of that, the full end-to-end journey (official pass → lecture complete → next lecture unlocked) has not been run on
  production for the new labs.
- Blocks 2–6 content: lectures 25–28 and 37–40 are authored and verified (not yet imported); 29–36 are being authored; 41–104 are
  not started.
- Quiz pass mark is "all correct" today; the exam lectures will need a configurable mark.
- Video storage (Cloudflare R2) is approved in cost but out of scope now.
