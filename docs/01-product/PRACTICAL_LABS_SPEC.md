# Practical Labs — specification (v1, 2026-10-16)

Source of truth for the Practical Labs feature. Decisions below were taken by the owner on 2026-10-16; anything marked *assumption* was not explicitly answered and follows the recommendation the owner was shown.

## 1. Goal
Every lecture from 9 to 104 of the *AI Foundations, AI Application & AI Creator Program* (104 hours) names a Practical Project. The site gets a **Practical Labs** section (course → month → lecture → lab). A learner opens a lab, the browser loads Python and the lab's libraries, the learner works, presses **Save & check**, and an auto-checker says pass or fail. On failure a popup explains the error with two choices: **Dismiss** or **Show hint** (the fix for that error, free). A **bulb** button gives general hints, **3 per lab**; after 3 hints the learner can **Redo** (start the lab again). Results are pass/fail; attempts and hints are recorded. The server is the authority for every official result.

## 2. Decisions (owner, 2026-10-16)
| # | Decision |
|---|---|
| Kinds | Code labs auto-checked. Labs needing an outside service use a **predefined practice API** (mock LLM, sentiment, embeddings, OCR, vision, public-data endpoints) with fixed, deterministic answers; **the course document will be changed to name this API**. Written/design labs: learner submits text, **teacher marks from a rubric**. Exam lectures 87–98: **auto-marked question sets**. Deployment/presentation lectures (84, 103, 104): **checklist + link upload for the teacher**. All kinds are built now. |
| Content | AI-written instructions, starter code, datasets (small fictional CSV/image/document files), tests, 3 hints and error guidance for every lab; owner reviews. **Test definitions are always visible to the administrator.** |
| Save | Checks run **instantly in the browser** (visible checks) and the popup shows at once; the **official result comes from the server grader** a few seconds later and replaces it. |
| Hints | Error guidance in the popup is free. Bulb hints: **max 3 per lab per learner**, then **Redo** (*assumption*: redo restores the starter code, resets the 3 hints, keeps the attempt history, counts a redo). |
| Scoring | **Pass/fail**; attempt count and hint count recorded. A lab passes when every check passes. No score penalties. |
| Gating | A lab opens only for lectures the learner has **reached** (previous lecture completed). Passing the lab counts toward lecture completion and the certificate (*assumption*). |
| Lecture labs | The labs in Lectures 9–12 are **replaced** by the document's practical projects. |
| Teachers | See practical-lab results in the existing teacher views, plus a review queue for written/upload labs. |
| Course records | Existing course renamed to the document's course (*assumption*); 13 month-modules; **lecture records for all 104 lectures** created now (1–8 draft; 9–104 published with a minimal "lab-only" body until the lecture content is uploaded — a draft lecture cannot be opened by learners, so lab-only lectures must be published). |
| Order | Built and deployed in blocks: 9–24, 25–40, 41–56, 57–72, 73–88, 89–104. |
| Videos / R2 | Cost approved but **out of scope now**. |
| Grader host | Stays t4g.micro for now. |
| Network | Student code never reaches the internet. The practice API is an **in-process simulator** (`labmock`) installed in both runtimes; same code, same answers in the browser and on the server. |
| Git | Keep working on the current branch, deploy to production from it, PR at the end. |

## 3. Acceptance criteria
- AC1 A learner sees Practical Labs: course title, months, each lecture's lab with kind and state (locked, not started, in progress, awaiting review, passed, try again). Locked labs cannot be opened (API 400/404, UI disabled).
- AC2 Opening a code lab loads Python with the lab's packages and files in the browser; **Run** executes code and shows output; code autosaves.
- AC3 **Save & check** runs the visible checks in the browser and opens a popup within 2 s: pass ("Looks right — confirming officially…") or fail with the error (exception type + line, or the failed checks) and the buttons Dismiss / Show hint. The server result replaces it when it arrives; a server pass is the only pass recorded.
- AC4 Bulb hints: counter "Hint n of 3"; the 4th request is refused (409 `HINTS_EXHAUSTED`); when exhausted and the last result failed, the popup offers **Redo**; Redo resets code and hints, keeps history, increments redo count.
- AC5 Quiz labs: questions shown without answers; one submission marks all questions server-side; pass when every question is correct (per-question explanation shown afterwards); retry allowed.
- AC6 Written labs: text (≤ 8 000 chars) is submitted; status "awaiting review"; teacher sees it in **Reviews**, scores each rubric criterion, marks pass/fail with feedback; the learner sees the outcome.
- AC7 Upload labs: checklist ticks, a link (https) and notes; same review flow as AC6.
- AC8 Admin → Content shows every lab's kind and, on request, its full test definitions.
- AC9 Teacher views show practical-lab attempts, hints used, redo count and review outcomes.
- AC10 Every official result is produced server-side; the browser quick check never changes a stored result. Student code has no network in either runtime; the practice API is simulated in-process.
- AC11 Each lab ships with a reference solution that passes and a starter that fails (verified in CI for every pack).

## 4. Data model (migration 0009, additive)
`lecture_exercises` + `lab_kind` (code|quiz|written|upload), `scoring` (score|pass_fail), `packages` jsonb, `assets` jsonb [{name, kind: text|base64, content, description}], `limits` jsonb {memory_mb, timeout_seconds}, `rubric` jsonb [{criterion, description, max_points}], `checklist` jsonb [text], `hints_max` int (3).
`exercise_hint_reveals` + `cycle` int. New `lab_hint_state` (learner_id, exercise_id, cycle, redo_count, updated_at). Hints are counted per cycle; Redo starts a new cycle.
`lab_questions` (quiz): exercise_id, question_order, prompt, options jsonb, correct_option_id (server-only), explanation, points.
`lab_submissions` + `answers` jsonb; status gains `submitted` (awaiting teacher review). New `lab_reviews` (submission_id unique, reviewer_id, scores jsonb, passed, feedback, created_at).
`exercise_tests.definition` gains check kinds: `expr`+`expected`/`truthy` (an expression evaluated in the learner's namespace after the run), `stdout_contains`, `stdout_regex`, `stdout_min_lines`, `variable_type`, in addition to the existing `non_empty`, `expected_stdout`, `variable_is_str`, `stdout_equals_variable`, `variable_equals`. Only probe *expressions* enter the sandbox; expected values stay host-side.
RLS: enabled with no policies on all new tables; grants revoked from anon/authenticated (API-only access).

## 5. API (additive; see API_SPEC.md)
- `GET /labs` — course, months, labs with state. Enrolled learners (teachers/admins see all states as "available").
- `GET /exercises/{id}` — adds lab_kind, scoring, packages, assets, visible_checks, hints_max, hints_used, cycle, redo_count, questions (quiz, no answers), rubric, checklist, lecture (id, number, title), review (if any).
- `POST /exercises/{id}/hints` — 409 `HINTS_EXHAUSTED` after hints_max in the current cycle.
- `POST /exercises/{id}/redo` — allowed only when hints are exhausted; new cycle; draft cleared.
- `POST /exercises/{id}/submissions` — body adds `answers`; code → queue as today; quiz → marked immediately; written/upload → `submitted`.
- `GET /submissions/{id}` — adds `quiz_results`, `review`.
- `GET /teacher/reviews` (pending written/upload for assigned learners); `POST /teacher/submissions/{id}/review` {scores, passed, feedback}.
- `GET /admin/exercises/{id}/tests` — full definitions.
- Worker claim payload adds `files`, `probes`, `limits`, `packages`.

## 6. The predefined practice API (`https://api.neuromind.lab/v1`)
Simulated in-process by `labmock` (one Python file used by the browser runtime and the sandbox image). Real `requests` calls to this host are answered without any network; any other host raises `ConnectionError("Internet access is disabled in the lab")`. Deterministic: the same input always gives the same output.

| Endpoint | Used by | Behaviour |
|---|---|---|
| `GET /weather?city=` | L23 | `{city, temperature_c, condition, humidity}`; unknown city → 404 `{error}` |
| `GET /books?author=`, `GET /books/{id}` | L23, L66 | fixed catalogue |
| `GET /news/headlines` | L70 | 5 fixed headlines |
| `GET /secure/profile` | L66, L69, L90 | needs `Authorization: Bearer nm-test-key-123`; key in the URL → 401 with an explanation |
| `GET /flaky` | L68 | 503 twice per process, then 200 |
| `POST /chat` | L50, L51–57, L67–74 | OpenAI-style request/response; deterministic content rules (summarise, flashcards, translate, tool calls when `tools` given) |
| `POST /generate` | L43 | n varied outputs for one prompt |
| `POST /sentiment` | L40 | lexicon-based label + score (misses sarcasm by design) |
| `POST /entities` | L40 | people/places/orgs from a fixed gazetteer |
| `POST /embeddings` | L47, L60–65 | 64-dim deterministic vectors; synonyms map so paraphrases score higher |
| `POST /ocr`, `POST /vision/classify`, `POST /vision/detect`, `POST /vision/ask` | L38, L41, L42 | lookup by provided image asset name |
| `GET /search?q=` | L72 | fixed results |
Python helpers in `labmock`: `tokenizer` (L39), `VectorIndex` (L61), `multimodal` (L41). The course document must be updated to name this API and key where it says "a public API" or "a provided tool".

## 7. Lab pack schema v2 (content/lectures/*.json)
Adds to v1: `lab.kind`, `lab.scoring` (default pass_fail), `lab.packages`, `lab.assets`, `lab.limits`, `lab.questions` (quiz), `lab.rubric`, `lab.checklist`, `lab.solution` (reference solution, validated in CI, never imported), test definitions with `expr`. `lab_only: true` allows a lecture with just an intro and the lab (no checkpoints/exit check) until content arrives. Hidden definitions still come from `private/` files.

## 8. Out of scope now
Videos/R2, file uploads (links only until storage is decided), AI-generated marking of written work, GitHub integration.
