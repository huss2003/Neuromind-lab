-- 0005: lecture prerequisites (§5 course map locking) and question presentation policy (§11.1).
alter table public.lectures add column prerequisites jsonb not null default '[]';  -- array of lecture ids that must be completed first
alter table public.mcq_questions
  add column shuffle_options boolean not null default false,
  add column reveal_policy text not null default 'always' check (reveal_policy in ('always','after_correct'));
