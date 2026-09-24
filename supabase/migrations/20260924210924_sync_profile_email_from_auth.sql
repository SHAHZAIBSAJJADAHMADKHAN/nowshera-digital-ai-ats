-- Keep the ATS profile email aligned only after Supabase Auth has committed
-- an authenticated email change. This deliberately does not provision profiles.

create or replace function public.sync_profile_email_from_auth()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.email is not distinct from old.email or new.email is null then
    return new;
  end if;

  update public.profiles
  set email = lower(btrim(new.email))
  where id = new.id
    and email is distinct from lower(btrim(new.email));

  return new;
end;
$$;

revoke all on function public.sync_profile_email_from_auth() from public, anon, authenticated;

drop trigger if exists sync_profile_email_from_auth_after_email_update on auth.users;
create trigger sync_profile_email_from_auth_after_email_update
after update of email on auth.users
for each row
when (old.email is distinct from new.email)
execute function public.sync_profile_email_from_auth();
