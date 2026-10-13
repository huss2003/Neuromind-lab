# Product Requirements Document — NeuroMind AI Learning Lab
Version 0.1.0 | Status: prototype baseline

## 1. Summary
A web learning environment for NeuroMind's 104-lecture AI course. It combines segmented video lessons, embedded MCQs, practical demonstrations, browser Python practice, official grading, remediation/retry and persisted progress. The learner experiences one coordinated flow rather than jumping between tools.

## 2. Problem
Separate videos, quizzes, editors and feedback create navigation friction and make progress hard to track. NeuroMind needs a repeatable lesson engine and consistent assessment results, while a solo developer proves the concept before requesting paid infrastructure.

## 3. Target users
**Learner:** beginner who needs plain-language instructions, browser coding, immediate feedback and resumable progress.
**Teacher/content author:** configures segments, questions, exercises and grading rules without editing code for routine content.
**Administrator:** manages roles, access and operational issues.

## 4. Goals
- G1: one complete end-to-end lecture works.
- G2: the same data-driven player supports all lectures.
- G3: both Pyodide practice and official server-side grading are supported.
- G4: scores, attempts and progress are server-authoritative and persistent.
- G5: prototype uses free plans/local execution wherever practical.
- G6: components can be upgraded without rebuilding the entire application.

## 5. Non-goals — do not build without approval
- All 104 lectures as bespoke pages or all recordings before prototype validation.
- Payments, fees, attendance, admissions, certificates, marketing site or full LMS.
- Languages other than Python in MVP.
- Arbitrary packages, unrestricted filesystem/network, uploaded executables, or public arbitrary-code execution.
- Production promise of 100 simultaneous official grading jobs.
- Linux terminal, SQL, APIs, Git, RAG, agents, cybersecurity labs, cloud labs, multi-file persistent workspaces, GPU labs, native mobile app, complex analytics.
- Paid AI tutor, Redis, paid video service, paid hosting or GPU purchase before approval.
- AI deciding official grades where deterministic tests can decide.
- Automatically publishing AI-generated course content without teacher review.

## 6. Product principles
Data-driven content; one vertical slice first; server owns official scores; code execution is isolated; beginner-friendly language; resumable progress; accessible UI; cost visibility; replaceable media/grading adapters.

## 7. MVP scope
- Supabase Auth, learner/teacher roles.
- Course dashboard and lecture manifest.
- Segmented player with checkpoints and progress restoration.
- Server-scored MCQs and explanations.
- Practical video auto-transition to exercise.
- Monaco editor and Pyodide browser practice.
- Official grading through local Docker worker, separate from API.
- Hidden tests, time/memory/output limits, safe feedback and retry.
- Teacher content/results view.
- Basic logs/tests and free-tier preview deployment.

Deferred: hosted grading, Redis queue, paid AI tutor, all 104 content records, advanced lab types, production scale/load certification.

## 8. Functional requirements
FR1 Auth; FR2 server-enforced roles; FR3 published course navigation; FR4 ordered segments; FR5 required checkpoints cannot be bypassed; FR6 server-scored MCQs; FR7 practical-video end opens linked exercise; FR8 Pyodide supported practice; FR9 isolated official grading; FR10 feedback/retry; FR11 server-persisted progress; FR12 teacher content management; FR13 safe operational logs.

## 9. Success criteria
- Sign-in works.
- Segment sequence and checkpoint pauses are correct.
- MCQ results survive refresh and do not expose answer keys.
- Practical video opens correct exercise.
- Browser practice works for supported Python.
- Official grading runs outside API process with limits.
- Failure/retry and pass/completion work.
- Refresh restores valid state and cannot bypass required work.
- Teacher can inspect results.
- Security/permission tests pass.
- Fresh-checkout setup is documented and tested.

## 10. Assumptions and risks
Lecture 9 is the recommended sample; videos can be placeholders. Drive player control must be tested; do not rely on undocumented iframe events. Render Free may sleep, Supabase Free has quotas, R2 has quotas. 100 simultaneous learners is a future target, not an MVP guarantee. Docker alone is not a complete hostile-code sandbox.
