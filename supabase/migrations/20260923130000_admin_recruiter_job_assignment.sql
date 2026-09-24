create function public.assign_recruiter_to_job(
  p_admin_id uuid,
  p_job_id uuid,
  p_recruiter_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job_status public.job_status;
  v_recruiter_role public.app_role;
  v_recruiter_active boolean;
  v_inserted_count integer;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active
  for key share;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'insufficient_privilege';
  end if;

  select status into v_job_status
  from public.jobs
  where id = p_job_id
  for update;
  if not found then
    raise exception 'Job not found' using errcode = 'foreign_key_violation';
  end if;
  if v_job_status = 'closed' then
    raise exception 'Closed jobs cannot receive recruiter assignments' using errcode = 'check_violation';
  end if;

  select role, is_active into v_recruiter_role, v_recruiter_active
  from public.profiles
  where id = p_recruiter_id
  for key share;
  if not found or v_recruiter_role <> 'recruiter' or not v_recruiter_active then
    raise exception 'Active recruiter profile not found' using errcode = 'foreign_key_violation';
  end if;

  insert into public.job_recruiters (job_id, recruiter_id, assigned_by)
  values (p_job_id, p_recruiter_id, p_admin_id)
  on conflict (job_id, recruiter_id) do nothing;
  get diagnostics v_inserted_count = row_count;

  if v_inserted_count > 0 then
    insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, metadata)
    values (
      p_admin_id,
      'admin',
      'recruiter_assigned_to_job',
      'job',
      p_job_id,
      jsonb_build_object('recruiter_id', p_recruiter_id)
    );
  end if;

  return v_inserted_count > 0;
end;
$$;

create function public.unassign_recruiter_from_job(
  p_admin_id uuid,
  p_job_id uuid,
  p_recruiter_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_recruiter_role public.app_role;
  v_removed_count integer;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active
  for key share;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'insufficient_privilege';
  end if;

  perform 1
  from public.jobs
  where id = p_job_id
  for key share;
  if not found then
    raise exception 'Job not found' using errcode = 'foreign_key_violation';
  end if;

  select role into v_recruiter_role
  from public.profiles
  where id = p_recruiter_id
  for key share;
  if not found or v_recruiter_role <> 'recruiter' then
    raise exception 'Recruiter profile not found' using errcode = 'foreign_key_violation';
  end if;

  delete from public.job_recruiters
  where job_id = p_job_id and recruiter_id = p_recruiter_id;
  get diagnostics v_removed_count = row_count;

  if v_removed_count > 0 then
    insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, metadata)
    values (
      p_admin_id,
      'admin',
      'recruiter_unassigned_from_job',
      'job',
      p_job_id,
      jsonb_build_object('recruiter_id', p_recruiter_id)
    );
  end if;

  return v_removed_count > 0;
end;
$$;

revoke all on function public.assign_recruiter_to_job(uuid, uuid, uuid) from public, anon, authenticated;
revoke all on function public.unassign_recruiter_from_job(uuid, uuid, uuid) from public, anon, authenticated;
grant execute on function public.assign_recruiter_to_job(uuid, uuid, uuid) to service_role;
grant execute on function public.unassign_recruiter_from_job(uuid, uuid, uuid) to service_role;
