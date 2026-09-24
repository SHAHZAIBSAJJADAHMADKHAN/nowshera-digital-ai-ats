-- Create only a missing candidate profile during the authenticated bootstrap path.
-- Recruiter identities are explicitly provisioned by the existing recruiter invitation flow.

create function public.bootstrap_candidate_profile(
  p_candidate_id uuid,
  p_full_name text,
  p_email text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_existing_role public.app_role;
begin
  if nullif(btrim(p_full_name), '') is null or nullif(btrim(p_email), '') is null then
    raise exception 'Candidate profile requires a full name and email' using errcode = 'check_violation';
  end if;

  select role into v_existing_role
  from public.profiles
  where id = p_candidate_id
  for update;

  if found then
    if v_existing_role <> 'candidate' then
      raise exception 'Existing ATS profile is not a candidate' using errcode = 'insufficient_privilege';
    end if;
    return;
  end if;

  insert into public.profiles (id, full_name, email, role, is_active)
  values (p_candidate_id, btrim(p_full_name), lower(btrim(p_email)), 'candidate', true)
  on conflict (id) do nothing;

  select role into v_existing_role
  from public.profiles
  where id = p_candidate_id;

  if not found or v_existing_role <> 'candidate' then
    raise exception 'Candidate profile bootstrap conflict' using errcode = 'insufficient_privilege';
  end if;
end;
$$;

revoke all on function public.bootstrap_candidate_profile(uuid, text, text) from public, anon, authenticated;
grant execute on function public.bootstrap_candidate_profile(uuid, text, text) to service_role;
