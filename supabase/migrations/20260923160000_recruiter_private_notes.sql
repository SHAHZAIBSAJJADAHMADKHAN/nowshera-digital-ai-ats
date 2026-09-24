-- Phase 6B Step 1: atomic, service-role-only recruiter note creation.

create function public.add_recruiter_note(
  p_recruiter_id uuid,
  p_application_id uuid,
  p_note text
)
returns table (id uuid, note text, created_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_note public.recruiter_notes%rowtype;
begin
  perform 1
  from public.profiles p
  where p.id = p_recruiter_id and p.role = 'recruiter' and p.is_active
  for key share;
  if not found then
    raise exception 'Active recruiter profile not found' using errcode = 'foreign_key_violation';
  end if;

  perform 1
  from public.applications a
  where a.id = p_application_id
  for key share;
  if not found then
    raise exception 'Application not found' using errcode = 'foreign_key_violation';
  end if;

  perform 1
  from public.job_recruiters jr
  join public.applications a on a.job_id = jr.job_id
  where jr.recruiter_id = p_recruiter_id and a.id = p_application_id
  for key share of jr;
  if not found then
    raise exception 'Application not found' using errcode = 'foreign_key_violation';
  end if;

  insert into public.recruiter_notes (application_id, recruiter_id, note)
  values (p_application_id, p_recruiter_id, p_note)
  returning * into v_note;

  return query select v_note.id, v_note.note, v_note.created_at;
end;
$$;

revoke all on function public.add_recruiter_note(uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.add_recruiter_note(uuid, uuid, text) to service_role;
