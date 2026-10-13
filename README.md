# NeuroMind AI Learning Lab — Pre-Vibe-Coding Pack
Status: planning baseline, 2026-10-13. Audience: solo developer using AI coding tools.

## Read in order
1. PRD; 2. User stories and acceptance criteria; 3. Architecture/stack; 4. Data model; 5. API spec; 6. CLAUDE.md / AGENTS.md; 7. User flows; 8. Design system; 9. Wireframes; 10. Security; 11. Test plan; 12. NFRs; 13. Error handling; 14. Environment; 15. Deployment; 16. Implementation plan; 17. PROGRESS; 18. ADRs; 19. Glossary; 20. Reference patterns; 21. Prompt library.

## Scope baseline
Build one data-driven sample lecture first (recommended Lecture 9: Python setup, notebooks and the first program). It must sequence separate video segments, two MCQ checkpoints, results/explanations, a practical video, automatic exercise opening, Pyodide browser practice, official local Docker grading, retry/remediation, progress persistence, and a basic teacher result view. The full course has 104 lectures, but do not build 104 bespoke pages or record all videos before the sample flow works.

## Constraints and cautions
- Solo developer; use free plans/local tools and existing AI subscription. No paid service/API without approval.
- Frontend: React/TypeScript; Cloudflare Pages Free. API: FastAPI local or Render Free. Auth/database: Supabase Free. Browser practice: Pyodide. Official grading: separate local Docker worker.
- Google Drive can store master recordings and may be tested for playback. Use HTML5-compatible media events for reliable automatic transitions; test Cloudflare R2 for sample playback.
- Never expose Docker, Docker socket, or local grader to public internet.
- Free prototype is not a production-secure code runner or proof of 100 concurrent grading jobs.
- Version pins are a proposed baseline and must be verified together before install.
- Keep `.env`, secrets, answer keys and hidden tests out of Git/client responses.

## Prototype acceptance gate
Learner can sign in; play segments; answer two MCQs and see server-calculated results; see practical video; have exercise open automatically; run supported Python in browser; submit to a local isolated grader; receive result/retry; refresh and resume; and have results visible to authorised teacher.

## Change control
For any scope/schema/API/security/cost decision: update the relevant spec, tests, ADR if needed, and PROGRESS.md before or with implementation. Do not silently infer major requirements.
