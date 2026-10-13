# User Stories and Acceptance Criteria
Each criterion is testable. Convert these into automated tests where practical.

## Authentication/roles
**US-01 Learner sign-in:** As a learner, I want to sign in so my progress is tied to my account.
- Valid credentials route to learner dashboard.
- Invalid credentials show safe error and create no session.
- Protected API without valid token returns 401.
- Learner cannot read another learner's records by changing IDs.

**US-02 Teacher access:** As a teacher, I want to manage course content.
- Teacher can open teacher routes.
- Learner cannot create/edit/publish content.
- Changing role in request/browser storage grants no permission.
- Denied action returns 403 and safe audit event.

## Lecture flow
**US-03 Open lecture:** As a learner, I want to open a published lecture.
- Dashboard lists published content only.
- Selecting lecture loads metadata/segments.
- Missing/unpublished lecture shows safe not-found state.

**US-04 Ordered segments:** As a learner, I want segments to play in order.
- End of segment 1 advances to segment 2 once.
- Order comes from data, not hard-coded page logic.
- Media error shows retry/fallback and does not mark completion.

**US-05 Checkpoint:** As a learner, I want video to pause for MCQs.
- Required checkpoint pauses the flow and shows its question.
- Next segment remains locked until server confirms completion.
- Refresh cannot bypass checkpoint.
- Duplicate events do not duplicate completion.

**US-06 Resume:** As a learner, I want progress saved.
- Segment/position is saved at transitions and reasonable intervals.
- Refresh restores latest server state.
- Client local storage cannot mark a lecture complete.
- Failed save is visible and retryable.

**US-07 Practical to exercise:** As a learner, I want the exercise to open after the practical video.
- Media `ended` opens configured exercise.
- Accessible fallback button exists.
- Missing exercise shows error and does not mark completion.

## MCQs
**US-08 Answer MCQ:** As a learner, I want server-checked answers.
- Prompt/options render.
- Correct answer is not returned before submission.
- Server validates option and checkpoint association.
- Correct/incorrect answer returns score/explanation.
- Unknown option returns 422.
- Idempotent retry creates no duplicate attempt.

**US-09 Teacher reviews attempts:** As a teacher, I want to inspect results.
- Attempt stores learner, checkpoint, option, correctness, score and timestamp.
- Learner sees only own attempts.
- Teacher access is course-scoped.

## Coding lab
**US-10 Edit/run practice:** As a learner, I want a browser editor.
- Monaco loads starter code.
- Pyodide runs supported exercise.
- Output and errors are displayed as text.
- Infinite loop can be terminated.
- Browser result is labelled practice, not official grade.

**US-11 Official grading:** As a learner, I want submitted code graded consistently.
- Submission requires auth and published exercise.
- API does not execute code in request process.
- Worker has time, memory, process and output limits.
- No secrets, Docker socket, host home mount or network are exposed.
- Hidden tests remain server-side.

**US-12 Feedback/retry:** As a learner, I want actionable feedback.
- Result shows status, score and passed/total tests.
- Infrastructure failure is not labelled student failure.
- Failed task can be retried when allowed.
- Previous attempts remain recorded.
- Pass updates completion exactly once.

## Teacher and operations
**US-13 Content editor:** Teacher can configure ordered segments, questions, practical video and exercise.
- Invalid references/order block publishing.
- Draft content is not learner-visible.
- Published question edits preserve historical attempt meaning.

**US-14 Setup:** As solo developer, I want reproducible setup.
- README lists verified commands.
- `.env.example` contains names only, no secrets.
- Fresh checkout setup succeeds.
- Lint/typecheck/tests are documented and run.

**US-15 Logs:** As developer, I want useful safe logs.
- API errors include request ID.
- Secrets, tokens and hidden test answers are not logged.
- Grader distinguishes timeout, code failure and infrastructure failure.

## Global acceptance rules
- Server validates auth, ownership, role, inputs and completion.
- Async UI has loading/error/success/empty states.
- No green success before server confirmation.
- Retry operations are idempotent.
- No test uses production credentials.
