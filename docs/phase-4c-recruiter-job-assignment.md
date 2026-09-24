# Phase 4C: Recruiter-to-Job Assignment

## Step 1: Trusted database layer

Phase 4C Step 1 adds only the database operations for admin-controlled recruiter assignments. No Phase 4C API schema, service, router, dashboard, or frontend work is included.

## Relationship and lifecycle rule

The existing `public.job_recruiters` table remains unchanged. Its `(job_id, recruiter_id)` primary key prevents duplicate relationships, and its existing `assigned_by` and `assigned_at` columns preserve assignment history.

New assignments are allowed for Draft and Open jobs. New assignments to Closed jobs are denied. Unassignment is allowed for any existing job, including Closed jobs, as safe administrative cleanup. Deactivating a recruiter does not remove historical relationships.

## Trusted functions

Migration `20260923130000_admin_recruiter_job_assignment.sql` deploys:

- `public.assign_recruiter_to_job(p_admin_id uuid, p_job_id uuid, p_recruiter_id uuid) returns boolean`
- `public.unassign_recruiter_from_job(p_admin_id uuid, p_job_id uuid, p_recruiter_id uuid) returns boolean`

Both functions are `SECURITY DEFINER`, set `search_path = ''`, use schema-qualified objects, and are executable only by `service_role`. `PUBLIC`, `anon`, and `authenticated` do not have execute privileges.

Assignment validates an active admin actor, an existing non-Closed job, and an active recruiter target. It uses `INSERT ... ON CONFLICT DO NOTHING`, returning `true` only when a relationship is added. A duplicate returns `false` without a second audit event. Successful insertion records `recruiter_assigned_to_job` on the job with the recruiter ID in safe metadata.

Unassignment validates an active admin, existing job, and recruiter-role target. It returns `true` only when a relationship is removed. Repeated removal returns `false` and creates no duplicate audit. Successful removal records `recruiter_unassigned_from_job`.

## RLS access effect

No RLS policy was changed. Existing Phase 2E helpers use `job_recruiters` plus an active recruiter profile to decide access. Rollback-only live checks confirmed that a recruiter has no assigned-job access before assignment, gains it after assignment, loses it after unassignment, and remains denied after deactivation even when the historical assignment row is preserved.

## Live verification and cleanup

The migration was deployed to the connected healthy Supabase project. Rollback-only live checks passed for active admin assignment and removal; candidate, recruiter, and inactive-admin denial; candidate/admin/inactive-recruiter/missing target denial; missing-job denial; Closed-job assignment denial; duplicate no-op behavior; single-row and single-audit behavior; repeated-unassignment no-op behavior; and inactive-recruiter access denial.

Live catalog inspection confirmed both functions’ signatures, `SECURITY DEFINER`, empty search path, and service-role-only execute privileges. Temporary Auth users, profiles, jobs, assignments, and audit rows were confirmed absent after rollback.

The complete backend suite passed: 47 tests. The Supabase project status was `ACTIVE_HEALTHY`. The security advisor reports only two pre-existing informational findings for intentionally internal RLS-protected tables (`audit_logs` and `automation_events`) without browser policies.

## Step 2: FastAPI layer

Step 2 adds the trusted backend API layer without changing the database migration, RPCs, or RLS policies.

Created modules:

- `backend/app/schemas/admin_job_assignments.py`
- `backend/app/services/admin_job_assignments.py`
- `backend/app/api/v1/admin_job_assignments.py`

The existing service-role integration now lists assignment rows with safe recruiter profile fields and invokes the two trusted assignment RPCs. It does not directly insert or delete `job_recruiters` rows.

Admin-only routes are registered under the existing Admin Jobs resource:

- `GET /api/v1/admin/jobs/{job_id}/recruiters`
- `POST /api/v1/admin/jobs/{job_id}/recruiters/{recruiter_id}`
- `DELETE /api/v1/admin/jobs/{job_id}/recruiters/{recruiter_id}`

All three require `require_admin`. Assignment and unassignment pass only `CurrentUser.user_id` as the authoritative actor. The assignment list returns recruiter ID, full name, email, active state, and `assigned_at`; inactive historical assignments remain visible to admins.

The mutation response is `{"changed": true|false}`. A false value preserves the database idempotency semantics: already assigned for POST, or already absent for DELETE. Missing jobs or recruiters map to 404, target/lifecycle conflicts map to 409, trusted integration unavailability maps to 503, and FastAPI validates malformed UUID paths.

Router declaration and OpenAPI verification found all three routes exactly once with the admin dependency. Imports/app startup succeeded and the full backend suite remained at 47 passing tests. No secrets were added.

## Step 3: Final verification

Dedicated API coverage in `backend/tests/test_admin_job_assignments.py` verifies all three routes for 401 unauthenticated and 403 candidate/recruiter behavior; safe assignment-list responses including inactive historical assignments; empty and unknown-job lists; authenticated actor binding; duplicate assign and repeated-unassign responses; normalized 404, 409, and 503 failures; malformed UUID handling; ignored spoofing query parameters; and error-message non-leakage. The dedicated suite has 24 passing tests.

The complete backend suite has 71 passing tests. Existing Phase 3 auth/authorization, Phase 4A recruiter management, and Phase 4B job management tests remain green. The frontend production build also passed.

Live regression checks re-confirmed both assignment RPCs are `SECURITY DEFINER`, set an empty search path, deny execution to `PUBLIC`, `anon`, and `authenticated`, and grant execution only to `service_role`.

Rollback-only live checks reconfirmed Draft/Open assignment, Closed-job denial, inactive-recruiter and wrong-role target denial, candidate/recruiter/inactive-admin actor denial, duplicate no-op behavior with one relationship and one assignment audit, actual unassignment with one removal audit, and repeated-unassignment no-op behavior. A focused live RLS check confirmed access is denied before assignment, allowed while assigned, and denied again after unassignment. An inactive recruiter with a preserved historical assignment remains denied.

The unassignment regression included a controlled application and CV metadata row and verified both remained after relationship removal; the job also remained. No cascading deletion behavior was introduced.

All live test data was created inside rolled-back transactions. Follow-up checks confirmed no temporary Auth users, profiles, jobs, assignments, applications, CV metadata, or audit rows remained.

The project remains `ACTIVE_HEALTHY`. Security advisor findings are the two pre-existing informational notices for intentionally internal RLS-protected `audit_logs` and `automation_events` tables without browser policies. Performance advisor findings are informational unused-index notices on the currently unused workload; no unrelated changes were made.

Source secret scans found no token-pattern secrets. `.env` remains ignored and `.env.example` remains placeholder-only. No frontend backend secret was added.

Real Supabase access-token execution against the API remains deferred because no safe token-acquisition mechanism is available. No authentication bypass or unwanted Auth user was created.

## Deferred work

Phase 4D dashboards, assignment UI, candidate/recruiter workflow APIs, CV storage, n8n, Gemini, and email automation remain deferred.
