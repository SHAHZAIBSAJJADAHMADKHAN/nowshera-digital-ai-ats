-- Phase 8A: atomic, service-only automation outbox delivery lifecycle.

create function public.claim_automation_events(
  p_event_types text[],
  p_limit integer default 10
)
returns table(
  event_id uuid,
  event_type text,
  aggregate_type text,
  aggregate_id uuid,
  payload jsonb,
  attempt_count integer,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
begin
  if coalesce(cardinality(p_event_types), 0) = 0
     or cardinality(p_event_types) > 4
     or exists (
       select 1 from unnest(p_event_types) as requested(event_type)
       where requested.event_type not in (
         'application_received',
         'interview_invitation',
         'application_hired',
         'application_rejected'
       )
     ) then
    raise exception 'Only supported email event types can be claimed'
      using errcode = 'check_violation';
  end if;

  if p_limit < 1 or p_limit > 25 then
    raise exception 'Claim limit must be between 1 and 25'
      using errcode = 'check_violation';
  end if;

  return query
  with eligible as (
    select e.id
    from public.automation_events as e
    where e.status = 'pending'
      and e.available_at <= now()
      and e.event_type = any(p_event_types)
    order by e.available_at, e.created_at, e.id
    for update skip locked
    limit p_limit
  ), claimed as (
    update public.automation_events as e
    set status = 'processing',
        attempt_count = e.attempt_count + 1
    from eligible
    where e.id = eligible.id
    returning e.id, e.event_type, e.aggregate_type, e.aggregate_id,
              e.payload, e.attempt_count, e.created_at
  )
  select claimed.id, claimed.event_type, claimed.aggregate_type,
         claimed.aggregate_id, claimed.payload, claimed.attempt_count,
         claimed.created_at
  from claimed
  order by claimed.created_at, claimed.id;
end;
$$;

create function public.complete_automation_event(p_event_id uuid)
returns table(
  event_id uuid,
  status public.processing_status,
  attempt_count integer,
  processed_at timestamptz,
  available_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event public.automation_events%rowtype;
begin
  select * into v_event
  from public.automation_events
  where id = p_event_id
  for update;
  if not found then
    raise exception 'Automation event not found' using errcode = 'foreign_key_violation';
  end if;
  if v_event.status = 'completed' then
    return query select v_event.id, v_event.status, v_event.attempt_count,
      v_event.processed_at, v_event.available_at;
    return;
  end if;
  if v_event.status <> 'processing' then
    raise exception 'Only processing automation events can complete'
      using errcode = 'check_violation';
  end if;

  update public.automation_events
  set status = 'completed', processed_at = now(), last_error = null
  where id = p_event_id
  returning id, public.automation_events.status, public.automation_events.attempt_count,
    public.automation_events.processed_at, public.automation_events.available_at
  into event_id, status, attempt_count, processed_at, available_at;
  return next;
end;
$$;

create function public.fail_automation_event(p_event_id uuid, p_error text)
returns table(
  event_id uuid,
  status public.processing_status,
  attempt_count integer,
  processed_at timestamptz,
  available_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event public.automation_events%rowtype;
  v_error text := left(nullif(btrim(p_error), ''), 500);
begin
  if v_error is null then
    raise exception 'A safe failure message is required' using errcode = 'check_violation';
  end if;
  select * into v_event
  from public.automation_events
  where id = p_event_id
  for update;
  if not found then
    raise exception 'Automation event not found' using errcode = 'foreign_key_violation';
  end if;
  if v_event.status <> 'processing' then
    raise exception 'Only processing automation events can fail'
      using errcode = 'check_violation';
  end if;

  update public.automation_events
  set status = case when public.automation_events.attempt_count >= 3 then 'failed'::public.processing_status else 'pending'::public.processing_status end,
      last_error = v_error,
      available_at = case
        when public.automation_events.attempt_count >= 3 then public.automation_events.available_at
        else now() + interval '5 minutes'
      end
  where id = p_event_id
  returning id, public.automation_events.status, public.automation_events.attempt_count,
    public.automation_events.processed_at, public.automation_events.available_at
  into event_id, status, attempt_count, processed_at, available_at;
  return next;
end;
$$;

revoke all on function public.claim_automation_events(text[], integer) from public, anon, authenticated;
revoke all on function public.complete_automation_event(uuid) from public, anon, authenticated;
revoke all on function public.fail_automation_event(uuid, text) from public, anon, authenticated;
grant execute on function public.claim_automation_events(text[], integer) to service_role;
grant execute on function public.complete_automation_event(uuid) to service_role;
grant execute on function public.fail_automation_event(uuid, text) to service_role;
