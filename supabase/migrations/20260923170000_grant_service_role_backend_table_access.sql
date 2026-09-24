-- Trusted FastAPI integration uses the Supabase service_role key for its
-- server-side reads and service-role-only RPC calls. Browser roles remain
-- restricted by the Phase 2E grants and RLS policies.

grant usage on schema public to service_role;

grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;
