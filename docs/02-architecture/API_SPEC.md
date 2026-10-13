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
