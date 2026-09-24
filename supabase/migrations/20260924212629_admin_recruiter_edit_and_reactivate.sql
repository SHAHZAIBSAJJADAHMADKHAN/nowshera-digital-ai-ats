-- Admin-only recruiter lifecycle operations. They preserve the existing Auth
-- identity and all recruiter relationships; no recruiter is provisioned here.

create or replace function public.reactivate_recruiter(
  p_admin_id uuid,
  p_recruiter_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_active boolean;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'insufficient_privilege';
  end if;

  select is_active into v_active
  from public.profiles
  where id = p_recruiter_id and role = 'recruiter'
  for update;
  if not found then
    raise exception 'Recruiter not found' using errcode = 'foreign_key_violation';
  end if;

  if v_active then
    return false;
  end if;

  update public.profiles
  set is_active = true
  where id = p_recruiter_id;

  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id)
  values (p_admin_id, 'admin', 'recruiter_reactivated', 'profile', p_recruiter_id);

  return true;
end;
$$;

create or replace function public.update_recruiter_profile(
  p_admin_id uuid,
  p_recruiter_id uuid,
  p_full_name text,
  p_phone text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_current_name text;
  v_current_phone text;
  v_full_name text;
  v_phone text;
begin
  perform 1
  from public.profiles
  where id = p_admin_id and role = 'admin' and is_active;
  if not found then
    raise exception 'Active admin profile not found' using errcode = 'insufficient_privilege';
  end if;

  v_full_name := nullif(btrim(p_full_name), '');
  if v_full_name is null then
    raise exception 'Recruiter full name is required' using errcode = 'check_violation';
  end if;
  v_phone := nullif(btrim(p_phone), '');

  select full_name, phone into v_current_name, v_current_phone
  from public.profiles
  where id = p_recruiter_id and role = 'recruiter'
  for update;
  if not found then
    raise exception 'Recruiter not found' using errcode = 'foreign_key_violation';
  end if;

  if v_current_name is not distinct from v_full_name
     and v_current_phone is not distinct from v_phone then
    return;
  end if;

  update public.profiles
  set full_name = v_full_name,
      phone = v_phone
  where id = p_recruiter_id;

  insert into public.audit_logs (actor_id, actor_role, action, entity_type, entity_id, metadata)
  values (
    p_admin_id,
    'admin',
    'recruiter_profile_updated',
    'profile',
    p_recruiter_id,
    jsonb_build_object(
      'full_name_changed', v_current_name is distinct from v_full_name,
      'phone_changed', v_current_phone is distinct from v_phone
    )
  );
end;
$$;

revoke all on function public.reactivate_recruiter(uuid, uuid) from public, anon, authenticated;
revoke all on function public.update_recruiter_profile(uuid, uuid, text, text) from public, anon, authenticated;
grant execute on function public.reactivate_recruiter(uuid, uuid) to service_role;
grant execute on function public.update_recruiter_profile(uuid, uuid, text, text) to service_role;
