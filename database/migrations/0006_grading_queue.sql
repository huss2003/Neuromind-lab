-- 0006: durable, database-backed grading queue (see docs/06-operations/ADR_HOSTED_GRADING.md).
-- lab_submissions IS the queue: status 'queued' = waiting, 'running' = claimed under a lease. No second source of truth.
alter table public.lab_submissions
  add column claimed_by text,
  add column lease_expires_at timestamptz,
  add column claim_count int not null default 0;

create index lab_submissions_claim_idx on public.lab_submissions (created_at)
  where status in ('queued', 'running');

-- Atomically claim the oldest eligible job. Safe under concurrency (FOR UPDATE SKIP LOCKED).
-- Also dead-letters jobs whose claims are exhausted, so a job that keeps killing workers cannot loop forever.
create or replace function public.claim_next_submission(p_worker text, p_lease_seconds int, p_max_claims int)
returns setof public.lab_submissions
language plpgsql
security definer
set search_path = public
as $$
declare
  v public.lab_submissions;
begin
  update public.lab_submissions
     set status = 'error', claimed_by = null, lease_expires_at = null, finished_at = now(),
         safe_feedback = '[{"kind":"infrastructure","message":"We could not finish grading because of a system issue. This was not marked incorrect. Please submit again."}]'::jsonb
   where claim_count >= p_max_claims
     and (status = 'queued' or (status = 'running' and lease_expires_at < now()));

  select * into v
    from public.lab_submissions
   where claim_count < p_max_claims
     and (status = 'queued' or (status = 'running' and lease_expires_at < now()))
   order by created_at
   for update skip locked
   limit 1;
  if not found then
    return;
  end if;

  update public.lab_submissions
     set status = 'running', claimed_by = p_worker, claim_count = claim_count + 1,
         lease_expires_at = now() + make_interval(secs => p_lease_seconds),
         started_at = coalesce(started_at, now())
   where id = v.id
   returning * into v;
  return next v;
end;
$$;

-- Only the API's service role may call it; learners and anon must never be able to claim jobs.
revoke all on function public.claim_next_submission(text, int, int) from public, anon, authenticated;
grant execute on function public.claim_next_submission(text, int, int) to service_role;
