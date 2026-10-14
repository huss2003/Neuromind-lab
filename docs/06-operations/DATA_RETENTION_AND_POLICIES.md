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

## Update 2026-10-14
The privacy notice (`frontend/src/content/legal.ts`) now also states where data is stored (Supabase Tokyo, Vercel Japan, grader in Sydney), what the browser keeps (sign-in session, unsent draft copy), backups (kept up to 4 weeks), the age note and the manual nature of access/deletion requests. **This is still not legal review.** I am not a substitute for a lawyer or data-protection adviser. Before real learners: (1) replace the generic operator and contact wording (`OPERATOR`, `CONTACT` in that file) with the real organisation name and a monitored address; (2) have the text reviewed for the learners' country (consent age, data-transfer wording, authority to complain to); (3) decide the retention periods; (4) keep the "Draft" banner until that is done. Deletion and export are handled by an administrator by hand (delete the auth user; learner rows cascade); there is no self-service tool.
