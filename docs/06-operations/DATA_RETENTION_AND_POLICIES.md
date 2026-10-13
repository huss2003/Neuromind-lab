# Data retention and policy status

**Status: draft proposals for the owner to confirm. Nothing here has had legal review.** The in-app Privacy and Terms pages (`/privacy`, `/terms`) are marked as drafts and carry the same values.

| Data | Proposed retention | Notes |
|---|---|---|
| Account profile (name, role) | while the account is active; deleted on request | Auth email is held by Supabase Auth |
| Progress, checkpoint attempts, submissions, drafts | length of the course plus 12 months | Needed for grades and teacher review |
| Submitted source code | same as submissions | Learners are told not to paste secrets (Help page) |
| Audit log | 12 months | Allow-listed metadata only: no tokens, code, answers or tests |
| Server logs (Vercel) | platform default (hobby tier: short) | Logs carry request id, route, status, timings; no tokens or code |
| Backups | latest 4 weekly copies | `private/backups`, owner-held, mode 600 |

Open decisions for the owner: confirm the periods above; name a data controller and contact address for the legal pages; deletion/export request process (currently manual by the admin); jurisdictional wording (e.g. GDPR / local law). Until confirmed, the production decision keeps this as a condition.
