# Phase 4A — Admin Recruiter Management

Admin-only endpoints list, invite/provision, and deactivate recruiters. Native Supabase Auth invitation is the single password-setup email source; no outbox invitation event is created. After invite success, a service-role-only RPC creates the recruiter profile and audit record. If provisioning fails, the backend deletes the newly created Auth user as compensation. Deactivation is idempotent and retains historical assignments while Phase 2E/3B denies inactive recruiter access.
