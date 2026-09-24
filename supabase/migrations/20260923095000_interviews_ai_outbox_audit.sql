-- Phase 2C: interview scheduling, AI summary state, automation outbox, and audit logs.

create extension if not exists btree_gist with schema extensions;

create type public.processing_status as enum ('pending', 'processing', 'completed', 'failed');

create function public.prevent_audit_log_mutations()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  raise exception 'Audit logs are append-only.' using errcode = 'integrity_constraint_violation';
end;
$$;

create table public.interviews (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null unique references public.applications(id) on delete restrict,
  recruiter_id uuid not null references public.profiles(id) on delete restrict,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  location text,
  meeting_link text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint interviews_exactly_one_hour check (ends_at = starts_at + interval '1 hour'),
  constraint interviews_location_or_meeting_link check (
    nullif(btrim(location), '') is not null
    or nullif(btrim(meeting_link), '') is not null
  ),
  constraint interviews_recruiter_no_overlap exclude using gist (
    recruiter_id with =,
    tstzrange(starts_at, ends_at, '[)') with &&
  )
);

create table public.ai_summaries (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null unique references public.applications(id) on delete restrict,
  status public.processing_status not null default 'pending',
  profile_summary jsonb,
  requirements_found jsonb,
  requirements_not_found jsonb,
  interview_questions jsonb,
  error_message text,
  attempt_count integer not null default 0 check (attempt_count >= 0),
  generated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ai_summaries_completed_output_shape check (
    status <> 'completed'
    or (
      jsonb_typeof(profile_summary) = 'array'
      and jsonb_array_length(profile_summary) between 3 and 5
      and jsonb_typeof(requirements_found) = 'array'
      and jsonb_typeof(requirements_not_found) = 'array'
      and jsonb_typeof(interview_questions) = 'array'
      and jsonb_array_length(interview_questions) = 3
      and generated_at is not null
    )
  )
);

create table public.automation_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null check (char_length(btrim(event_type)) > 0),
  aggregate_type text not null check (char_length(btrim(aggregate_type)) > 0),
  aggregate_id uuid not null,
  payload jsonb not null default '{}'::jsonb,
  status public.processing_status not null default 'pending',
  attempt_count integer not null default 0 check (attempt_count >= 0),
  idempotency_key text not null unique check (char_length(btrim(idempotency_key)) > 0),
  last_error text,
  available_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  processed_at timestamptz,
  updated_at timestamptz not null default now()
);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.profiles(id) on delete set null,
  actor_role public.app_role,
  action text not null check (char_length(btrim(action)) > 0),
  entity_type text not null check (char_length(btrim(entity_type)) > 0),
  entity_id uuid not null,
  old_values jsonb,
  new_values jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

comment on table public.interviews is
  'One current official interview per application; recruiter overlap is prevented with a half-open one-hour range exclusion constraint.';
comment on table public.ai_summaries is
  'Current structured AI summary state per application. Semantic AI safety validation is enforced outside the database.';
comment on table public.automation_events is
  'Transactional outbox foundation; idempotency_key prevents duplicate logical event delivery.';
comment on table public.audit_logs is
  'Append-only traceability log. Null actor fields represent system or automation initiated events.';

create trigger set_interviews_updated_at
before update on public.interviews
for each row execute function public.set_updated_at();
create trigger set_ai_summaries_updated_at
before update on public.ai_summaries
for each row execute function public.set_updated_at();
create trigger set_automation_events_updated_at
before update on public.automation_events
for each row execute function public.set_updated_at();
create trigger prevent_audit_log_updates
before update on public.audit_logs
for each row execute function public.prevent_audit_log_mutations();
create trigger prevent_audit_log_deletes
before delete on public.audit_logs
for each row execute function public.prevent_audit_log_mutations();

create index interviews_recruiter_starts_at_idx on public.interviews (recruiter_id, starts_at);
create index ai_summaries_status_idx on public.ai_summaries (status);
create index automation_events_status_available_at_idx on public.automation_events (status, available_at);
create index automation_events_aggregate_idx on public.automation_events (aggregate_type, aggregate_id);
create index audit_logs_actor_id_idx on public.audit_logs (actor_id) where actor_id is not null;
create index audit_logs_entity_idx on public.audit_logs (entity_type, entity_id);
create index audit_logs_created_at_idx on public.audit_logs (created_at desc);

alter table public.interviews enable row level security;
alter table public.ai_summaries enable row level security;
alter table public.automation_events enable row level security;
alter table public.audit_logs enable row level security;

revoke all on function public.prevent_audit_log_mutations() from public;
