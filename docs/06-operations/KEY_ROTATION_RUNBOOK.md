# Supabase key rotation runbook

Why: the service-role key (a long-lived JWT that bypasses all row-level security) was pasted into a chat early in the project, and the old default password sits in public Git history. The owner asked for rotation on 2026-10-14.

What the code supports now: `app/http.py:service_headers` sends the new opaque `sb_secret_...` key in the `apikey` header only, and still accepts the legacy JWT. All scripts do the same. So the swap needs no code change.

## Steps (dashboard only; the automation here has no Supabase management token and no Vercel environment access)
1. Supabase dashboard, project `ddiwlgbllhwcdykqjfne` → **Project Settings → API Keys**. Create a **secret key** (`sb_secret_...`). Copy it once.
2. Vercel → project `neuromind-lab-api` → Settings → Environment Variables → set `SUPABASE_SERVICE_ROLE_KEY` (Production) to the new secret key. Optionally set `SUPABASE_ANON_KEY` to the **publishable** key (`sb_publishable_6NTuV9vcfJDpc9ZsJsmFxA_SzigVAUF`). Redeploy.
3. Vercel → project `neuromind-lab` → set `VITE_SUPABASE_ANON_KEY` to the same publishable key. Redeploy (the value is baked in at build time).
4. Local `.env` (git-ignored): replace the key so scripts keep working.
5. Check: sign in on the live site, open a lecture, answer a check, submit a lab. If anything returns 5xx or 401 for everyone, put the old key back (step 2) while you investigate.
6. Only after step 5 passes: Supabase → API Keys → **disable the legacy `anon` and `service_role` keys**. This is what makes the leaked key useless. (Optionally rotate the legacy JWT secret afterwards, which also invalidates all sessions.)
7. Optional: Project Settings → Database → reset the database password. The application does not use a direct database password.

## What rotation does not fix
Git history still contains the old default password. It no longer matches any account. Nothing else in history is a live credential (`scripts/check_secrets.py` and gitleaks in CI guard against new ones).

## Record
- 2026-10-14: runbook written, code ready. Rotation itself: **pending the owner's dashboard steps** (see readiness report).
