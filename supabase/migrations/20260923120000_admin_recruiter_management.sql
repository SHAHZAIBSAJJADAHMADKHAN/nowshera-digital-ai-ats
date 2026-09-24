create function public.provision_recruiter_profile(p_admin_id uuid,p_recruiter_id uuid,p_full_name text,p_email text,p_phone text default null) returns void language plpgsql security definer set search_path='' as $$
begin
 perform 1 from public.profiles where id=p_admin_id and role='admin' and is_active;
 if not found then raise exception 'Active admin profile not found' using errcode='insufficient_privilege'; end if;
 insert into public.profiles(id,full_name,email,phone,role,is_active) values(p_recruiter_id,btrim(p_full_name),lower(btrim(p_email)),nullif(btrim(p_phone),''),'recruiter',true);
 insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id,metadata) values(p_admin_id,'admin','recruiter_provisioned','profile',p_recruiter_id,jsonb_build_object('email',lower(btrim(p_email))));
end;$$;
create function public.deactivate_recruiter(p_admin_id uuid,p_recruiter_id uuid) returns boolean language plpgsql security definer set search_path='' as $$
declare v_active boolean;
begin
 perform 1 from public.profiles where id=p_admin_id and role='admin' and is_active;
 if not found then raise exception 'Active admin profile not found' using errcode='insufficient_privilege'; end if;
 select is_active into v_active from public.profiles where id=p_recruiter_id and role='recruiter' for update;
 if not found then raise exception 'Recruiter not found' using errcode='foreign_key_violation'; end if;
 if not v_active then return false; end if;
 update public.profiles set is_active=false where id=p_recruiter_id;
 insert into public.audit_logs(actor_id,actor_role,action,entity_type,entity_id) values(p_admin_id,'admin','recruiter_deactivated','profile',p_recruiter_id);
 return true;
end;$$;
revoke all on function public.provision_recruiter_profile(uuid,uuid,text,text,text) from public,anon,authenticated;
revoke all on function public.deactivate_recruiter(uuid,uuid) from public,anon,authenticated;
grant execute on function public.provision_recruiter_profile(uuid,uuid,text,text,text) to service_role;
grant execute on function public.deactivate_recruiter(uuid,uuid) to service_role;
