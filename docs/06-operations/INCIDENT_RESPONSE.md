# Incident response

For a small supervised pilot. The goal is simple: protect learners and their data, restore service, tell the right people, and learn from it. Fill in the contact details in the first table before the pilot starts.

## Who does what
| Role | Person | Contact |
|---|---|---|
| Incident lead (decides, communicates) | Owner (Hussain) | Hussainsingapuri24@gmail.com |
| Technical responder | Owner (Hussain), until a second person is named | Hussainsingapuri24@gmail.com |
| Owner / data controller (legal and learner notices) | Owner (Hussain) | Hussainsingapuri24@gmail.com |

Automatic alerts (worker down, queue backlog, API unreachable from the worker, EC2 status check, and the $15 budget) are delivered to the same address through the AWS notification topic `neuromind-alerts`; delivery was tested on 2026-10-14. One person holds every role for now, so add a second named responder before real learners join. Replace "Owner (Hussain)" with your full name and organisation when you give the policy details.

## Severity
| Level | Meaning | Respond within |
|---|---|---|
| 1 Critical | Suspected data exposure, a credential leak, learners can see others' data, scores can be forged | immediately, stop and contain |
| 2 Major | Sign-in or grading down for everyone; data loss risk | 1 hour |
| 3 Minor | One feature broken, slow grading, one learner affected | next working day |

## First 15 minutes (any level)
1. **Write down** the time, who reported it and what they saw. Create an issue report (Help → Report a problem) or a note.
2. **Look**, do not change: Administration → Overview (health, queue, dead letters), Audit log (what happened and who did it), CloudWatch alarms (`neuromind-*`), Vercel deployments (is the latest deployment healthy?).
3. **Decide the level** using the table. When unsure, treat it as one level higher.

## Containment by incident type
- **Suspected leaked credential** (a key or password appeared somewhere it should not): follow `KEY_ROTATION_RUNBOOK.md`; deactivate affected accounts in Administration → Users; review the Audit log for the period. A leaked Supabase service-role key means: create a new secret key, set it in Vercel, redeploy, then disable the old key. Treat all data as possibly read until proven otherwise.
- **Account compromised:** Deactivate the account (Administration → Users), then reactivate only after the owner has reset the password through the recovery email. Check the Audit log for what it did.
- **Grading integrity** (a learner found a way to pass without the right code, or forged a result): stop grading (`sudo systemctl stop neuromind-worker`; submissions wait and then fail safe), keep the attempts as evidence, fix, rerun the adversarial tests (`grader/tests`), then restart. Do not edit scores.
- **Grading or site down:** follow `DEAD_LETTER_RUNBOOK.md` for stuck attempts; for a bad release, roll back by pointing the production aliases at the previous Vercel deployment (no data change); for the worker host, restart the service or the instance.
- **Data loss or corruption:** stop writes if needed (maintenance notice as an announcement), then follow `BACKUP_RESTORE_RUNBOOK.md`. Take a fresh backup first.

## Telling people
- **Learners and teachers:** use an announcement for service problems (what is affected, what to do, when the next update comes). Plain language, no blame, no technical detail that helps an attacker.
- **Personal data affected:** the owner decides whether the law in the learners' country requires telling a regulator or the people involved, and by when (some laws set 72 hours). Get qualified advice; this document is not legal advice.
- **Never** put secrets, learner code or personal data into a public issue, chat or screenshot while handling an incident.

## Afterwards (within a week)
Write a short note: what happened, impact (who, how long), cause, what fixed it, what will prevent it. Add tests or alarms for the gap. Record decisions in `docs/09-audit/`.

## Escalation and credentials
Credential rotation steps: `KEY_ROTATION_RUNBOOK.md`. Restore: `BACKUP_RESTORE_RUNBOOK.md`. Stuck grading: `DEAD_LETTER_RUNBOOK.md`. Cost surprises: the AWS budget alert and `AWS_COST_AND_RESOURCE_PLAN.md`.
