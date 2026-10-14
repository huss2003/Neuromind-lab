-- 0004: "Complete Flow & Working v1.0" — enrolment, attempt statuses, section types, exercise orientation fields,
-- remediation mapping, snapshot hash. Additive except two CHECK constraints that are widened (no data is rewritten).

-- §9.2 status vocabulary: add RUNTIME_ERROR and CANCELLED/EXPIRED (SYSTEM_ERROR stays 'error')
alter table public.lab_submissions drop constraint lab_submissions_status_check;
alter table public.lab_submissions add constraint lab_submissions_status_check
  check (status in ('queued','running','passed','failed','timeout','error','runtime_error','expired','cancelled'));
-- §9 attempt creation: snapshot hash of the submitted code
alter table public.lab_submissions add column snapshot_sha256 text;

-- §14 section types beyond video/checkpoint/exercise/exit_check
alter table public.lecture_segments drop constraint lecture_segments_segment_type_check;
alter table public.lecture_segments add constraint lecture_segments_segment_type_check
  check (segment_type in ('intro','video','reading','example','checkpoint','exercise','reflection','exit_check'));

-- §8.1 exercise panel contents
alter table public.lecture_exercises
  add column objective text not null default '',
  add column constraints text not null default '',
  add column visible_examples jsonb not null default '[]',
  add column success_criteria jsonb not null default '[]';

-- §10 remediation mapped to a learning objective and a replayable section
alter table public.exercise_tests
  add column objective text,
  add column remediation_segment_id uuid references public.lecture_segments(id) on delete set null;

-- §8.1 drafts are tied to the content version
alter table public.lab_drafts add column content_version int;

-- §5/§17 enrolment: which learners may open which course
create table public.enrollments (
  id uuid primary key default gen_random_uuid(),
  learner_id uuid not null references public.profiles(id) on delete cascade,
  course_id uuid not null references public.courses(id) on delete cascade,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (learner_id, course_id)
);
create index enrollments_learner_idx on public.enrollments(learner_id) where revoked_at is null;
alter table public.enrollments enable row level security;
create policy enrollments_select_own on public.enrollments for select to authenticated using (learner_id = (select auth.uid()));
