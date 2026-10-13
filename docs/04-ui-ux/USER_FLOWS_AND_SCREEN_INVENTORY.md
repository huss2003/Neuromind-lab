# User Flows and Screen Inventory

## Learner flow
Sign in -> dashboard -> course/module -> lecture overview -> start -> video segment -> MCQ -> result/explanation -> next theory -> MCQ -> result -> practical video -> auto-open exercise -> Pyodide practice -> official submission -> queued/running -> pass OR remediation/retry -> exit check -> completion/progress.

## Resume flow
Sign in -> resume lecture -> API loads saved state -> validate checkpoint requirements -> restore current segment/position. If content changed or segment is invalid, show recovery rather than bypassing required work.

## Teacher flow
Sign in -> teacher dashboard -> content list -> edit draft -> configure ordered segments -> attach questions/exercise/tests -> preview -> validate -> publish -> view scoped results.

## Screen inventory with states
1. **Sign in:** default, submitting, invalid credentials, provider error, signed in, expired session.
2. **Learner dashboard:** loading, populated, no course, API error, expired session.
3. **Course/module:** loading, populated, empty, unavailable, network error.
4. **Lecture overview:** loading, ready, completed, draft/unavailable, media not configured.
5. **Lecture player:** loading, playing, paused, checkpoint, saving, media error, offline, transition, complete.
6. **MCQ checkpoint:** unanswered, selected, submitting, correct, incorrect, failed submission, attempt limit.
7. **Practical video:** loading, playing, ended, playback error, exercise missing.
8. **Coding lab:** loading, ready, runtime loading, running, output, timeout, queued, grading, passed, failed, grader unavailable.
9. **Submission result:** queued, running, passed, failed, timeout, infrastructure error.
10. **Progress:** loading, no activity, results, partial failure.
11. **Teacher dashboard:** loading, empty, populated, error.
12. **Lecture editor:** draft, saving, saved, validation error, publish-ready, publish failure.
13. **MCQ editor:** draft, invalid options, saved, published/versioned.
14. **Exercise editor:** draft, saving, invalid tests, ready, published.
15. **Teacher results:** loading, empty, populated, forbidden, error.
16. **Global error:** not found, unauthorised, forbidden, unavailable, unexpected error.

## Navigation rules
- Learner nav never shows teacher links, but API checks are still mandatory.
- Required checkpoints block forward navigation until server confirms.
- Leaving is not completion.
- Grader infrastructure failure is not learner failure.
- Draft content is invisible to learners.
- Every async action has loading, success, error and recovery states.
