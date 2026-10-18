# Data Model and Database Schema
PostgreSQL via Supabase. Versioned SQL migrations in `database/migrations/` are the schema source of truth.

## Rules
UUID primary keys; `timestamptz` UTC; FK/unique constraints; indexes for query patterns; no video binaries in DB; no answer keys/hidden tests in learner responses; server owns score/completion; RLS for browser-accessible tables; published content versions must preserve historical results.

## Entities and fields

### `profiles`
`id uuid PK FK auth.users`; `display_name text`; `role text CHECK learner|teacher|admin`; `created_at`, `updated_at timestamptz`. Role changes restricted to trusted admin/server path.

### `courses`
`id uuid PK`; `slug text UNIQUE`; `title text`; `description text`; `status text CHECK draft|published|archived`; `created_by uuid FK profiles`; timestamps. Index `(status, created_at)`.

### `modules`
`id uuid PK`; `course_id uuid FK courses`; `module_number int`; `title text`; `description text`; `sort_order int`; `status`; timestamps. Unique `(course_id,module_number)` and `(course_id,sort_order)`.

### `lectures`
`id uuid PK`; `course_id uuid FK courses` (denormalised for course-wide number constraint); `module_id uuid FK modules`; `lecture_number int`; `title text`; `summary text`; `learning_objectives jsonb`; `duration_seconds int`; `status`; `content_version int`; timestamps; `published_at timestamptz`. Unique `(course_id,lecture_number)`, index `(module_id,status)`.

### `lecture_segments`
`id uuid PK`; `lecture_id uuid FK`; `segment_order int`; `segment_type CHECK video|checkpoint|exercise|exit_check`; `title text`; `media_provider text nullable`; `media_asset_key text nullable`; `media_url text nullable`; `duration_seconds int nullable`; `checkpoint_id uuid nullable`; `exercise_id uuid nullable`; `is_required bool`; `settings jsonb`; timestamps. Unique `(lecture_id,segment_order)`. Validate fields according to segment type; use a later migration to add cyclic FKs safely.

### `mcq_questions`
Prefer immutable versioned records: `id uuid PK`; `question_key uuid`; `question_version int`; `prompt text`; `options jsonb` array of `{id,text}`; `correct_option_id text` server-only; `explanation_correct text`; `explanation_incorrect text nullable`; `points numeric(6,2)`; `status`; `created_by uuid`; timestamps. Unique `(question_key,question_version)`. Never return `correct_option_id` to learner before submission.

### `lecture_checkpoints`
`id uuid PK`; `lecture_id uuid FK`; `checkpoint_order int`; `checkpoint_type CHECK mcq|exit_check`; `question_id uuid FK`; `required bool`; `pass_threshold numeric nullable`; `settings jsonb`; `created_at`. Unique `(lecture_id,checkpoint_order)`.

### `lecture_exercises`
`id uuid PK`; `lecture_id uuid FK`; `title text`; `instructions text`; `language CHECK python`; `starter_code text`; `practice_mode CHECK pyodide|server|both`; `pass_threshold numeric`; `max_attempts int nullable`; `status`; timestamps. Index `(lecture_id,status)`.

### `exercise_tests`
`id uuid PK`; `exercise_id uuid FK`; `test_order int`; `test_type CHECK stdout|function|unit`; `definition jsonb`; `points numeric`; `is_hidden bool`; `created_at`. Unique `(exercise_id,test_order)`. Learner queries must never read this table.

### `lecture_sessions`
`id uuid PK`; `learner_id uuid FK profiles`; `lecture_id uuid FK`; `current_segment_id uuid nullable`; `playback_position_seconds int`; `status CHECK not_started|in_progress|completed`; `state_version int`; `last_seen_at`; `completed_at nullable`; timestamps. Unique `(learner_id,lecture_id)`, index `(learner_id,status)`.

### `checkpoint_attempts`
`id uuid PK`; `learner_id uuid FK`; `checkpoint_id uuid FK`; `question_id uuid FK`; `selected_option_id text`; `is_correct bool server-generated`; `score numeric`; `idempotency_key uuid`; `submitted_at`. Unique `(learner_id,idempotency_key)`; index `(learner_id,checkpoint_id,submitted_at desc)`.

### `lab_submissions`
`id uuid PK`; `learner_id uuid FK`; `exercise_id uuid FK`; `submission_number int`; `source_code text size-limited`; `status CHECK queued|running|passed|failed|timeout|error`; `score numeric nullable`; `passed_tests int`; `total_tests int`; `safe_feedback jsonb`; `execution_ms int nullable`; timestamps. Unique `(learner_id,exercise_id,submission_number)`; indexes `(status,created_at)` and `(learner_id,exercise_id,created_at desc)`.

### `student_progress`
`id uuid PK`; `learner_id uuid FK`; `course_id uuid FK`; `completed_lectures int`; `total_lectures int`; `progress_percent numeric`; `updated_at`. Unique `(learner_id,course_id)`. Summary is recomputable from source records.

### `audit_logs`
`id uuid PK`; `actor_id uuid nullable`; `event_type text`; `resource_type text`; `resource_id uuid nullable`; `request_id text`; `metadata jsonb allow-listed`; `created_at`. Index by event/time and actor/time as needed. Never log secrets.

## Relations
Courses 1:N modules; modules 1:N lectures; lectures 1:N segments/checkpoints/exercises; exercises 1:N tests; learners 1:N sessions/attempts/submissions; courses 1:N progress summaries.

## RLS/permissions
- Enable RLS on tables reachable from browser.
- Learners read published course content and only their own progress/attempts/submissions.
- Learners cannot directly write score, role, correctness, completion or hidden test fields.
- Teacher access is course-scoped and server-verified.
- Service-role key stays server-only.
- Test with two learners and one teacher.

## Migration strategy
Numbered SQL migrations; commit all changes; separate idempotent seed data; test from empty database; use staging first; no undocumented dashboard-only schema edits; no destructive migration without backup and explicit approval; regenerate types after schema changes.

## Migration 0009 — practical labs (applied to production 2026-10-16, additive)
- `lecture_exercises` gains `lab_kind CHECK code|quiz|written|upload` (default `code`), `scoring CHECK score|pass_fail` (default `score`; new labs are imported as `pass_fail`), `packages jsonb` (allowed: numpy, pandas, matplotlib, scikit-learn, pillow, requests), `assets jsonb` (lab data files written into the learner's working directory; text or base64, 2 MB in total per lab), `limits jsonb` (`memory_mb`, `timeout_seconds`; defaults 128 MB / 5 s, 384 MB / 20 s when a scientific package is used), `rubric jsonb` (written/upload: `{criterion, description, max_points}`), `checklist jsonb` (upload), `hints_max int` (0 to 10, default 3).
- `exercise_hint_reveals` gains `cycle int` (default 1); the unique key becomes `(learner_id, exercise_id, cycle, attempt_number, hint_index)`.
- New `lab_hint_state (learner_id, exercise_id) PK; cycle int; redo_count int; updated_at` — the learner's current hint cycle for a pass/fail lab; `Redo` increments both.
- New `lab_questions`: `id uuid PK; exercise_id FK; question_order int; prompt text; options jsonb; correct_option_id text; explanation text; points numeric`. Unique `(exercise_id, question_order)`. `correct_option_id` is server-only, like `mcq_questions`.
- `lab_submissions` gains `answers jsonb` (quiz responses or upload link/notes/checklist) and the status `submitted` (written/upload attempt waiting for a teacher).
- New `lab_reviews`: `id uuid PK; submission_id FK unique; reviewer_id FK nullable; scores jsonb; passed bool; feedback text (≤ 4000); created_at; updated_at`. One review per attempt; re-reviewing updates the row. Indexes: `lab_reviews(reviewer_id, created_at desc)`, partial `lab_submissions(status, created_at) where status = 'submitted'`.
- RLS is enabled on the three new tables; the API uses the service role, learners never query them directly. Learner-facing views are built in the API and never include hidden check definitions or correct option ids.
- `exercise_tests.definition` may now describe probes (`expr`), `stdout_contains`, `stdout_regex`, `stdout_min_lines`, `expected_stdout_lines`, `variable_type` and the earlier kinds (see docs/06-operations/LAB_AUTHORING_GUIDE.md). The `GET /admin/exercises/{id}/tests` route is the only place definitions leave the server, for administrators.
