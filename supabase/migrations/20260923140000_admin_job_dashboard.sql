-- Phase 4D Step 1: trusted, read-only per-job admin dashboard aggregates.
create function public.get_admin_job_dashboard(p_admin_id uuid)
returns table (
  job_id uuid,
  title text,
  department text,
  status public.job_status,
  application_deadline timestamptz,
  openings integer,
  total_applied bigint,
  applied_count bigint,
  shortlisted_count bigint,
  interview_count bigint,
  offer_count bigint,
  hired_count bigint,
  rejected_count bigint,
  withdrawn_count bigint
)
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform 1
  from public.profiles
  where id = p_admin_id
    and role = 'admin'
    and is_active;

  if not found then
    raise exception 'Active admin profile not found'
      using errcode = 'insufficient_privilege';
  end if;

  return query
  select
    j.id,
    j.title,
    j.department,
    j.status,
    j.application_deadline,
    j.openings,
    count(a.id)::bigint,
    count(a.id) filter (where a.stage = 'applied'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'shortlisted'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'interview'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'offer'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'hired'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'rejected'::public.application_stage)::bigint,
    count(a.id) filter (where a.stage = 'withdrawn'::public.application_stage)::bigint
  from public.jobs j
  left join public.applications a on a.job_id = j.id
  group by j.id, j.title, j.department, j.status, j.application_deadline, j.openings
  order by j.created_at desc, j.id desc;
end;
$$;

revoke all on function public.get_admin_job_dashboard(uuid) from public, anon, authenticated;
grant execute on function public.get_admin_job_dashboard(uuid) to service_role;
