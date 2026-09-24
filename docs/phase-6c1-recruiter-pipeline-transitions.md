# Phase 6C Step 1 — Recruiter Pipeline Transitions

`PATCH /api/v1/recruiter/applications/{application_id}/stage` exposes the existing authoritative `public.transition_recruiter_application(recruiter_id, application_id, target_stage)` RPC. The request schema is strict and permits only `shortlisted`, `offer`, and `rejected`; it never accepts a recruiter identifier.

The API uses `require_recruiter` and binds the RPC actor to `CurrentUser.user_id`. It first resolves the exact application and current job assignment with the existing privacy-safe recruiter service pattern, producing `404` for unknown or unassigned resources. The RPC remains the sole owner of locking, assignment revalidation, stage changes, history, audit rows, and rejection outbox events.

Step 1 deliberately does not expose `interview` or `hired`. Interview scheduling remains exclusively owned by `schedule_interview(...)` in Phase 7; hiring remains owned by `hire_application(...)` for Phase 6C Step 2. Database rules retain Applied→Shortlisted, Interview→Offer, active→Rejected, terminal-state protection, and the closed-job rule that permits only rejection of active applications.

The rollback-only SQL Editor verification passed. It confirmed standard progression, rejection/outbox behavior, closed-job rejection, terminal protection, assignment denial, direct-mutation/RPC privilege protection, and generic Interview/Hired denial. No fixture data remained after rollback. Focused endpoint tests: 12 passed. Complete backend suite: 217 passed. Frontend production build: passed.
