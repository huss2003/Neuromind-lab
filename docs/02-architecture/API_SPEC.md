# API Specification
Prefix `/api/v1`; JSON over HTTPS; protected routes require `Authorization: Bearer <Supabase access token>`. FastAPI OpenAPI schema is the executable contract.

## Error shape
```json
{"error":{"code":"VALIDATION_ERROR","message":"Request could not be processed","details":[{"field":"option_id","issue":"Unknown option"}],"request_id":"opaque-id"}}
```
Status codes: 200 success, 201 created, 202 queued, 204 no body, 400 invalid state, 401 unauthenticated, 403 forbidden, 404 not found/not visible, 409 conflict, 422 validation, 429 rate limit, 500 unexpected, 503 dependency unavailable.

## Routes
| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public minimal | Liveness only |
| GET | `/me` | Auth | Current profile/role |
| GET | `/courses` | Auth | Available courses |
| GET | `/courses/{course_id}` | Auth | Published course/modules |
| GET | `/lectures/{lecture_id}` | Auth | Learner-safe lecture manifest |
| GET | `/lectures/{lecture_id}/session` | Auth | Load/create session |
| PATCH | `/lectures/{lecture_id}/session` | Auth | Save allowed state |
| POST | `/checkpoints/{checkpoint_id}/attempts` | Auth | Submit answer |
| GET | `/checkpoints/{checkpoint_id}/attempts` | Owner/teacher scope | View attempts |
| GET | `/exercises/{exercise_id}` | Auth | Learner-safe exercise config |
| POST | `/exercises/{exercise_id}/submissions` | Auth | Create official submission |
| GET | `/submissions/{submission_id}` | Owner/teacher scope | Poll result |
| POST | `/lectures/{lecture_id}/complete` | Auth | Request completion; server verifies requirements |
| GET | `/teacher/lectures` | Teacher/admin | List content |
| POST | `/teacher/lectures` | Teacher/admin | Create draft |
| PATCH | `/teacher/lectures/{id}` | Teacher/admin | Update draft |
| PUT | `/teacher/lectures/{id}/segments` | Teacher/admin | Replace validated manifest |
| POST | `/teacher/questions` | Teacher/admin | Create question version |
| PATCH | `/teacher/questions/{id}` | Teacher/admin | Edit draft/version |
| POST | `/teacher/exercises` | Teacher/admin | Create exercise/tests |
| POST | `/teacher/lectures/{id}/publish` | Teacher/admin | Validate/publish |
| GET | `/teacher/learners/{learner_id}/results` | Scoped teacher/admin | View results |

## Key request/response shapes

### `GET /lectures/{id}`
```json
{"id":"uuid","lecture_number":9,"title":"Python setup, notebooks and the first program","duration_seconds":3600,"content_version":1,"segments":[{"id":"uuid","order":1,"type":"video","title":"Introduction","media":{"provider":"r2","url":"approved-media-url"},"next_action":{"type":"next_segment"}},{"id":"uuid","order":2,"type":"checkpoint","title":"Knowledge check 1","checkpoint":{"id":"uuid","type":"mcq","question":{"id":"uuid","prompt":"Which statement prints text?","options":[{"id":"a","text":"echo('Hi')"},{"id":"b","text":"print('Hi')"}]}}}]}
```
Never return correct answer or hidden test definitions.

### `GET /lectures/{id}/session`
```json
{"lecture_id":"uuid","current_segment_id":"uuid","playback_position_seconds":0,"status":"in_progress","completed_checkpoint_ids":[],"completed_exercise_ids":[],"state_version":1}
```

### `PATCH /lectures/{id}/session`
Request: `{"current_segment_id":"uuid","playback_position_seconds":125,"state_version":1}`. Server validates segment ownership and checkpoint prerequisites; use optimistic concurrency.

### `POST /checkpoints/{id}/attempts`
Header `Idempotency-Key: UUID`; request `{"question_id":"uuid","selected_option_id":"b"}`.
Response: `{"attempt_id":"uuid","is_correct":true,"score":1,"explanation":"print writes output.","checkpoint_completed":true,"next_action":{"type":"next_segment"}}`.
Never accept score/correctness from client.

### `GET /exercises/{id}`
```json
{"id":"uuid","title":"Print a variable","instructions":"Create student_name and print it.","language":"python","starter_code":"student_name = \"\"\nprint(student_name)\n","practice_mode":"both","pass_threshold":80,"max_attempts":5}
```
No hidden tests in response.

### `POST /exercises/{id}/submissions`
Header `Idempotency-Key: UUID`; request `{"source_code":"student_name='Aarav'\nprint(student_name)"}`.
Response `202`: `{"submission_id":"uuid","status":"queued","status_url":"/api/v1/submissions/uuid"}`.

### `GET /submissions/{id}`
```json
{"submission_id":"uuid","status":"passed","score":100,"passed_tests":3,"total_tests":3,"execution_ms":42,"feedback":[{"kind":"success","message":"All required tests passed."}],"finished_at":"2026-01-01T00:00:02Z"}
```
Do not reveal hidden inputs, expected output or container internals.

### Completion
`POST /lectures/{id}/complete` request `{"exit_check_completed":true}`. Server independently checks all required segments/checkpoints/exercises. Client flags alone are never authoritative.

## Idempotency and versioning
MCQ and code submissions accept idempotency keys. Same key/same payload returns original result; same key/different payload returns 409. Prefix API with `/v1`; update OpenAPI and contract tests with changes.

## Additive endpoints and conventions (implementation notes, 2026-10-13 — need owner approval)
- `GET /me/progress` (Auth): learner's own lecture session statuses for the dashboard.
- `GET /exercises/{id}/submissions` (Auth): learner's own attempt history for an exercise.
- `GET /teacher/learners` (Teacher/admin): learner list so the teacher results screen can choose a learner.
- Session responses additionally include `checkpoint_results` (so explanations survive refresh) and `max_reachable_order`.
- Segment `settings.on_end = {"type":"open_exercise","exercise_id":"<uuid>"}` links a practical video to its exercise explicitly; the manifest exposes it as `next_action`.
- Checkpoint completion: no `pass_threshold` => any submitted attempt completes it (formative MCQ); with a threshold (exit check = 100) a sufficient score is required and retries are allowed. Exercise completion = a `passed` submission. Infrastructure errors never count toward `max_attempts`.
- Unknown, malformed or not-owned resource ids return 404 (never 403) to avoid id probing. Teacher/admin access is currently NOT course-scoped because the schema has no teacher-course assignment table (open decision).

## v1.0 requirements update (2026-10-13, aligned to NeuroMind Lab Requirements v1.0)
Policy decisions taken from the requirements document (which supersedes the earlier pack):
- **Unlimited practice attempts** (§6.2). `lecture_exercises.max_attempts = null`; a cap is still honoured if a teacher sets one. Abuse protection is separate: max 6 submissions/minute and 2 in flight per learner (`429 RATE_LIMITED`).
- **Best valid score** = highest `score` among `passed`/`failed` attempts (timeouts and infrastructure errors never count).
- **Hints** (default formula, open decision §25): each hint revealed during an attempt lowers *that attempt's* score by `hint_penalty_percent` points (floor 0); pass/fail uses the adjusted score; earlier best scores are never lowered.
- **Appeals are NOT enabled** (eligibility/window/reviewer are undecided, §21).
- **Teacher scope**: teachers see only learners with an active (`revoked_at is null`) row in `teacher_assignments`; admins see all. Out-of-scope or unknown learners/submissions return 404. No endpoint can change an official score.

New / changed endpoints:
| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/ready` | Public minimal | Readiness: `{status, checks:{config,database}}`, 503 when degraded; discloses no values |
| GET | `/me` | Auth | now also `email`, `display_name` |
| GET | `/courses/{id}` | Auth | now includes `modules[]` each with its `lectures[]` |
| GET | `/me/progress` | Auth | own lecture statuses |
| GET | `/me/feedback` | Auth | own **published** teacher feedback |
| GET | `/exercises/{id}` | Auth | + `hints_total`, `hints_revealed`, `hint_penalty_percent`, `best_score`, `attempts_used`, `draft`, `unlocked` |
| POST | `/exercises/{id}/hints` | Auth | reveal hint `hint_index` (ordered, idempotent) |
| PUT | `/exercises/{id}/draft` | Auth | autosave work in progress (204) |
| GET | `/exercises/{id}/submissions` | Auth | own attempts + `best_score` |
| GET | `/submissions/{id}` | Owner / scoped teacher | + `raw_score`, `hints_used`, `hint_penalty`, `criteria[]` (hidden checks labelled generically), `remediation[]` |
| GET | `/lectures/{id}/session` | Auth | + `progress{media,checkpoints,labs,mastery}` |
| GET | `/teacher/summary` | Teacher/admin | tiles for assigned learners |
| GET | `/teacher/learners?q&limit&offset` | Teacher/admin | scoped, searchable, paginated (limit 1-100) |
| GET | `/teacher/learners/{id}/results` | Scoped teacher/admin | titles, best scores, attempts, submissions, feedback |
| GET | `/teacher/submissions/{id}` | Scoped teacher/admin | full evidence: code, criteria, grader/test-suite/content versions, correlation id, timings |
| POST | `/teacher/learners/{id}/feedback` | Scoped teacher/admin | feedback note; never alters scores |

Evidence persisted per official attempt (§6.3, GRD-008): content version, test-suite version, grader version, max score, pass threshold, raw and adjusted score, hint use and penalty, per-criterion results, correlation id, started/finished timestamps. Checkpoint attempts store question and content versions.
Audit events written (allow-listed metadata only): `auth.denied`, `checkpoint.attempt`, `submission.created`, `submission.finished`, `submission.rate_limited`, `hint.revealed`, `lecture.completed`, `teacher.view_learner`, `teacher.view_submission`, `feedback.created`.


## 2026-10-14 additions (admin workspace, certificates, portfolio, announcements, cohorts, issue reports)
All routes are under `/api/v1`. Errors use the standard shape. Admin routes need role `admin`; teacher-tool routes need `teacher` or `admin`; `/me/*` needs any signed-in user; `GET /certificates/verify/{serial}` is public.

| Method | Route | Notes |
|---|---|---|
| GET | `/admin/users?q&role&status&limit&offset` | merges profiles with Supabase Auth data (email, last sign-in); searched in memory over at most 1,000 accounts |
| POST | `/admin/users` | `{email, display_name, role, password (12+), course_id?}`; 409 `USER_NOT_CREATED` with one generic message if the address exists or the password is refused |
| POST | `/admin/users/{id}/deactivate` · `/reactivate` | sets `profiles.deactivated_at` and bans the Auth user; 400 for your own account; the API answers 403 `ACCOUNT_DEACTIVATED` within the 30 s token cache |
| GET | `/admin/overview` · `/admin/queue` | counts, health, queue depth, queue-wait / execution / end-to-end percentiles for 24 h, dead letters |
| POST | `/admin/submissions/{id}/requeue` | only `status=error` with `claim_count>=3`; 404 otherwise |
| GET | `/admin/audit?event_type&actor_id&limit(<=200)&offset` | newest first |
| GET | `/admin/courses` · PATCH `/admin/lectures/{id}/status` | `{status: draft|published|archived}`; publishing a lecture with no sections is refused (422); the lecture's questions and lab take the same status |
| POST | `/admin/content/packs/validate` | `{pack, tests}` → `{valid, problems[], missing_tests[], summary}`; writes nothing; max about 400 KB (413) |
| POST | `/admin/content/packs/import` | `{pack, tests, publish=false, replace_published=false, course_id?}`; idempotent upsert of the lecture, questions, checkpoints, lab, sections and hidden tests; draft unless `publish`; 422 if invalid or a hidden test definition is missing; 409 if it would turn a published lecture into a draft without `replace_published`; audited as `admin.content_pack_imported` (counts only, never test definitions) |
| GET/POST | `/admin/cohorts` · DELETE `/admin/cohorts/{id}` | archive, not delete |
| PUT/DELETE | `/admin/cohorts/{id}/members/{learner}` · `/teachers/{teacher}` | membership drives enrolment and teacher assignment |
| GET/PATCH | `/admin/issues` | `{status, admin_note}` |
| GET | `/admin/settings` | read-only, no secrets |
| GET | `/me/certificates` · `GET /certificates/verify/{serial}` | issued only by `POST /lectures/{id}/complete` when every published lecture of the course is complete |
| GET/POST/DELETE | `/me/portfolio` | only own passed submissions; the same submission is added once |
| GET | `/me/announcements` | course-wide from administrators, plus the learner's own teachers' |
| POST | `/me/issues` | `{category: content|grading|account|accessibility|other, message, page?}`; 5 per hour per person |
| GET/POST/DELETE | `/teacher/announcements` | teachers: scope `assigned` only |
| GET | `/teacher/cohorts` · `/teacher/reports/progress?format=json|csv&cohort_id=` | CSV cells starting with `= + - @` are prefixed with `'` |

Submission views now also return `content_version`, `test_suite_version`, `started_at`, `finished_at`. The worker `GET /internal/grader/health` also returns `queue_wait_p95_seconds`, `execution_p95_seconds`, `sample_last_hour`. The API returns 403 `MFA_REQUIRED` for an account with a verified second factor when the access token did not complete it (assurance level 1).

## 2026-10-16 additions (practical labs; see docs/01-product/PRACTICAL_LABS_SPEC.md)
All routes are under `/api/v1`. Labs exist only for published lectures; a learner only reaches the lab of a lecture they have reached (a lab behind an uncompleted checkpoint answers 400 `CHECKPOINT_REQUIRED` and a locked lecture is not opened at all, as before).

| Method | Route | Notes |
|---|---|---|
| GET | `/labs` | course → month-module → lab rows: `{lecture_id, lecture_number, lecture_title, exercise_id, title, lab_kind, packages, state, lecture_state, attempts, last_status}`; `state` is `locked`, `not_started`, `in_progress`, `awaiting_review`, `needs_retry` or `passed`, computed from server records only; learners see enrolled courses, teachers and admins all published courses |
| GET | `/exercises/{id}` | now also `lab_kind` (`code`, `quiz`, `written`, `upload`), `scoring` (`score`, `pass_fail`), `packages`, `assets` (name, description; data files for the browser runtime), `limits`, `visible_checks` (the non-hidden checks with their definitions so the browser can run the quick check; hidden checks never leave the server), `hints_max`, `hints_used`, `cycle`, `redo_count`, `redo_available`, `questions` (quiz: prompt and options, never `correct_option_id`), `rubric`, `checklist`, `review` (teacher decision when one exists) |
| POST | `/exercises/{id}/hints` | pass/fail labs: at most `hints_max` (3) per cycle; the fourth answers 409 `HINTS_EXHAUSTED`; score-mode labs keep the per-attempt behaviour |
| POST | `/exercises/{id}/redo` | only when the hints of the current cycle are used up, else 409 `REDO_NOT_AVAILABLE`; starts cycle `n+1` with fresh hints and the starter code, drops the draft, keeps the attempt history; audited `lab.redo` |
| POST | `/exercises/{id}/submissions` | body now `{source_code?, content_version?, answers?}`; `code`: graded as before (official result on the server); `quiz`: `answers = {question_id: option_id}` marked at insert, result `passed`/`failed` with `quiz_results` (per question correct/incorrect and explanation, never the correct option); `written`: `source_code` is the learner's text, status `submitted`; `upload`: `answers = {link (https), notes?, checklist: [true…]}` validated (422) then `submitted` |
| GET | `/submissions/{id}` | also `awaiting_review`, `quiz_results`, `answers` (own submissions only) and `review` (`passed`, `feedback`, `scores`, `reviewed_at`) |
| GET | `/teacher/reviews` | written/upload attempts in status `submitted` for the teacher's assigned learners (admins: all) |
| POST | `/teacher/submissions/{id}/review` | `{passed, feedback, scores: [{criterion, points}]}`; points are capped by the rubric's `max_points` (422 if above); the decision becomes the official result (`passed`/`failed`, score from the rubric); re-reviewing replaces it; audited `teacher.reviewed`; 409 `NOT_REVIEWABLE` for code and quiz labs |
| GET | `/teacher/submissions/{id}` | also `lab_kind`, `rubric`, `checklist`, `answers`, `review` |
| GET | `/admin/exercises/{id}/tests` | every check of a lab, hidden ones included, with definitions and quiz answers — administrators only (owner decision 2026-10-16: test definitions always visible to the admin) |
| POST | `/admin/content/packs/validate` · `/import` | pack schema v2 (`lab_only`, lab `kind`, `scoring`, `packages`, `assets`, `limits`, `questions`, `rubric`, `checklist`, `hints_max`); visible checks may carry their `definition` inline and are then never reported as missing; hidden checks must not (422) |
| GET | `/internal/grader/claim` | the claimed job also carries `files` (lab data files), `packages`, `limits` (`memory_mb`, `timeout_seconds`) and `probes` (expressions evaluated in the learner namespace after the run; expected values stay on the server) |

Official results stay server-authoritative: the browser quick check (Pyodide, same `evaluate.py` as the grader, visible checks only) is guidance; `Save` sends the code to the server and the recorded attempt, hint and redo counts come from server rows. The sandbox never reaches the internet: the predefined practice API (`https://api.neuromind.lab/v1`, in-process simulator `labmock`) is the only "network" a lab can use, in the browser and in the grader alike.
