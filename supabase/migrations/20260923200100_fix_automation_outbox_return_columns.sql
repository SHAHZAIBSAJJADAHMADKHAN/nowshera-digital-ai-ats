-- Correct Phase 8A routine return-column qualification for PL/pgSQL output variables.

create or replace function public.complete_automation_event(p_event_id uuid)
returns table(
  event_id uuid,
  status public.processing_status,
  attempt_count integer,
  processed_at timestamptz,
  available_at timestamptz
)
language plpgsql security definer set search_path = '' as $$
declare v_event public.automation_events%rowtype;
begin
  select * into v_event from public.automation_events where id = p_event_id for update;
  if not found then raise exception 'Automation event not found' using errcode = 'foreign_key_violation'; end if;
  if v_event.status = 'completed' then
    return query select v_event.id, v_event.status, v_event.attempt_count, v_event.processed_at, v_event.available_at;
    return;
  end if;
  if v_event.status <> 'processing' then raise exception 'Only processing automation events can complete' using errcode = 'check_violation'; end if;
  update public.automation_events set status = 'completed', processed_at = now(), last_error = null
  where id = p_event_id
  returning id, public.automation_events.status, public.automation_events.attempt_count,
    public.automation_events.processed_at, public.automation_events.available_at
  into event_id, status, attempt_count, processed_at, available_at;
  return next;
end;
$$;

create or replace function public.fail_automation_event(p_event_id uuid, p_error text)
returns table(
  event_id uuid,
  status public.processing_status,
  attempt_count integer,
  processed_at timestamptz,
  available_at timestamptz
)
language plpgsql security definer set search_path = '' as $$
declare
  v_event public.automation_events%rowtype;
  v_error text := left(nullif(btrim(p_error), ''), 500);
begin
  if v_error is null then raise exception 'A safe failure message is required' using errcode = 'check_violation'; end if;
  select * into v_event from public.automation_events where id = p_event_id for update;
  if not found then raise exception 'Automation event not found' using errcode = 'foreign_key_violation'; end if;
  if v_event.status <> 'processing' then raise exception 'Only processing automation events can fail' using errcode = 'check_violation'; end if;
  update public.automation_events
  set status = case when public.automation_events.attempt_count >= 3 then 'failed'::public.processing_status else 'pending'::public.processing_status end,
      last_error = v_error,
      available_at = case when public.automation_events.attempt_count >= 3 then public.automation_events.available_at else now() + interval '5 minutes' end
  where id = p_event_id
  returning id, public.automation_events.status, public.automation_events.attempt_count,
    public.automation_events.processed_at, public.automation_events.available_at
  into event_id, status, attempt_count, processed_at, available_at;
  return next;
end;
$$;
