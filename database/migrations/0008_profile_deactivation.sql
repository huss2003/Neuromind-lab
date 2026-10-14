-- 0008: administrators can deactivate an account. The API refuses a deactivated profile on every request (see app/auth.py),
-- and the Auth user is also banned so no new sign-in or token refresh succeeds.
alter table public.profiles add column deactivated_at timestamptz;
