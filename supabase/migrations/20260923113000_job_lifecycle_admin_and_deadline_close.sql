-- Phase 2D-5: admin-controlled draft/open/closed lifecycle and deadline closure.

create function public.open_job(p_admin_id uuid, p_job_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job public.jobs%rowtype;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'foreign_key_violation';
  end if;

  select * into v_job
  from public.jobs
  where id = p_job_id
  for update;
  if not found then
    raise exception 'Job not found' using errcode = 'foreign_key_violation';
  end if;
  if v_job.status <> 'draft' then
    raise exception 'Only draft jobs can be opened' using errcode = 'check_violation';
  end if;
  if char_length(btrim(v_job.title)) = 0
     or char_length(btrim(v_job.department)) = 0
     or char_length(btrim(v_job.location)) = 0
     or char_length(btrim(v_job.description)) = 0
     or char_length(btrim(v_job.requirements)) = 0
     or v_job.openings <= 0 then
    raise exception 'Job is missing required publication data' using errcode = 'check_violation';
  end if;
  if v_job.application_deadline <= now() then
    raise exception 'Job deadline must be in the future to open' using errcode = 'check_violation';
  end if;

  update public.jobs
  set status = 'open', closed_at = null
  where id = p_job_id;

  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, old_values, new_values)
  values (
    p_admin_id, 'admin', 'job_opened', 'job', p_job_id,
    jsonb_build_object('status', 'draft'),
    jsonb_build_object('status', 'open', 'closed_at', null)
  );
end;
$$;

create function public.close_job(p_admin_id uuid, p_job_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job public.jobs%rowtype;
  v_closed_at timestamptz;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'foreign_key_violation';
  end if;

  select * into v_job
  from public.jobs
  where id = p_job_id
  for update;
  if not found then
    raise exception 'Job not found' using errcode = 'foreign_key_violation';
  end if;
  if v_job.status = 'closed' then
    return false;
  end if;

  v_closed_at := now();
  update public.jobs
  set status = 'closed', closed_at = v_closed_at
  where id = p_job_id;

  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, old_values, new_values)
  values (
    p_admin_id, 'admin', 'job_manually_closed', 'job', p_job_id,
    jsonb_build_object('status', v_job.status, 'closed_at', v_job.closed_at),
    jsonb_build_object('status', 'closed', 'closed_at', v_closed_at)
  );
  return true;
end;
$$;

create function public.close_expired_jobs()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_job_id uuid;
  v_closed_count integer := 0;
  v_closed_at timestamptz := now();
begin
  for v_job_id in
    select id
    from public.jobs
    where status = 'open' and application_deadline <= v_closed_at
    for update
  loop
    update public.jobs
    set status = 'closed', closed_at = v_closed_at
    where id = v_job_id and status = 'open' and application_deadline <= v_closed_at;

    if found then
      insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, old_values, new_values, metadata)
      values (
        null, null, 'job_deadline_closed', 'job', v_job_id,
        jsonb_build_object('status', 'open'),
        jsonb_build_object('status', 'closed', 'closed_at', v_closed_at),
        jsonb_build_object('reason', 'application_deadline_expired')
      );
      v_closed_count := v_closed_count + 1;
    end if;
  end loop;
  return v_closed_count;
end;
$$;

revoke all on function public.open_job(uuid, uuid) from public, anon, authenticated;
revoke all on function public.close_job(uuid, uuid) from public, anon, authenticated;
revoke all on function public.close_expired_jobs() from public, anon, authenticated;
grant execute on function public.open_job(uuid, uuid) to service_role;
grant execute on function public.close_job(uuid, uuid) to service_role;
grant execute on function public.close_expired_jobs() to service_role;
