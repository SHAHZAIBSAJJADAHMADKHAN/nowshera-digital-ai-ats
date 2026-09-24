-- Phase 2B: immutable CV versions, applications, stage history, and recruiter notes.

create type public.application_stage as enum (
  'applied',
  'shortlisted',
  'interview',
  'offer',
  'hired',
  'rejected',
  'withdrawn'
);

create function public.prevent_candidate_cv_updates()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  raise exception 'Candidate CV versions are immutable; upload a new version instead.'
    using errcode = 'integrity_constraint_violation';
end;
$$;

create function public.prevent_application_identity_updates()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if new.candidate_id is distinct from old.candidate_id
     or new.job_id is distinct from old.job_id
     or new.cv_id is distinct from old.cv_id
     or new.applied_at is distinct from old.applied_at then
    raise exception 'An application cannot change its candidate, job, CV snapshot, or submission time.'
      using errcode = 'integrity_constraint_violation';
  end if;
  return new;
end;
$$;

create table public.candidate_cvs (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.profiles(id) on delete restrict,
  storage_path text not null unique check (char_length(btrim(storage_path)) > 0),
  original_filename text not null check (char_length(btrim(original_filename)) > 0),
  mime_type text not null check (mime_type = 'application/pdf'),
  file_size_bytes integer not null check (file_size_bytes > 0 and file_size_bytes <= 2097152),
  uploaded_at timestamptz not null default now(),
  unique (id, candidate_id)
);

comment on table public.candidate_cvs is
  'Immutable metadata for a versioned candidate PDF CV. Files remain in future private Supabase Storage.';

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null references public.profiles(id) on delete restrict,
  job_id uuid not null references public.jobs(id) on delete restrict,
  cv_id uuid not null,
  stage public.application_stage not null default 'applied',
  applied_at timestamptz not null default now(),
  withdrawn_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint applications_cv_belongs_to_candidate_fkey
    foreign key (cv_id, candidate_id)
    references public.candidate_cvs (id, candidate_id)
    on delete restrict,
  constraint applications_withdrawn_at_matches_stage
    check (
      (stage = 'withdrawn' and withdrawn_at is not null)
      or (stage <> 'withdrawn' and withdrawn_at is null)
    )
);

comment on table public.applications is
  'Candidate job application with an immutable foreign-key reference to the exact submitted CV version.';

create table public.application_stage_history (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references public.applications(id) on delete restrict,
  from_stage public.application_stage,
  to_stage public.application_stage not null,
  changed_by uuid not null references public.profiles(id) on delete restrict,
  changed_at timestamptz not null default now()
);

create table public.recruiter_notes (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references public.applications(id) on delete restrict,
  recruiter_id uuid not null references public.profiles(id) on delete restrict,
  note text not null check (char_length(btrim(note)) > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.recruiter_notes is
  'Private internal notes. Future RLS permits only assigned recruiters and authorized admins.';

create trigger prevent_candidate_cv_updates
before update on public.candidate_cvs
for each row execute function public.prevent_candidate_cv_updates();

create trigger prevent_application_identity_updates
before update on public.applications
for each row execute function public.prevent_application_identity_updates();

create trigger set_applications_updated_at
before update on public.applications
for each row execute function public.set_updated_at();

create trigger set_recruiter_notes_updated_at
before update on public.recruiter_notes
for each row execute function public.set_updated_at();

-- Active stages occupy the candidate/job slot; terminal history does not.
create unique index applications_one_active_per_candidate_job_idx
  on public.applications (candidate_id, job_id)
  where stage in ('applied', 'shortlisted', 'interview', 'offer');
create index candidate_cvs_candidate_uploaded_at_idx
  on public.candidate_cvs (candidate_id, uploaded_at desc);
create index applications_candidate_id_idx on public.applications (candidate_id);
create index applications_job_id_idx on public.applications (job_id);
create index applications_stage_idx on public.applications (stage);
create index application_stage_history_application_changed_at_idx
  on public.application_stage_history (application_id, changed_at desc);
create index application_stage_history_changed_by_idx
  on public.application_stage_history (changed_by);
create index recruiter_notes_application_created_at_idx
  on public.recruiter_notes (application_id, created_at desc);
create index recruiter_notes_recruiter_id_idx on public.recruiter_notes (recruiter_id);

alter table public.candidate_cvs enable row level security;
alter table public.applications enable row level security;
alter table public.application_stage_history enable row level security;
alter table public.recruiter_notes enable row level security;

revoke all on function public.prevent_candidate_cv_updates() from public;
revoke all on function public.prevent_application_identity_updates() from public;
