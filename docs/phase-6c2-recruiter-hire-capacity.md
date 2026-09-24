# Phase 6C Step 2 — Recruiter Hire API and Capacity

`POST /api/v1/recruiter/applications/{application_id}/hire` exposes only the existing service-role-only `public.hire_application(recruiter_id, application_id)` RPC. The route requires `require_recruiter` and binds the actor to `CurrentUser.user_id`; it accepts no recruiter identifier or request body.

The database RPC remains authoritative for Offer→Hired only, current assignment, job/application row locks, hired-count capacity enforcement, automatic closure when hired count reaches `openings`, application history, `application_hired` outbox events, audit records, and terminal state protection. The generic stage endpoint still rejects `hired`, while generic Interview remains unavailable.

The RPC locks the job before counting hired applications, preventing concurrent successful hires from exceeding capacity. It leaves a multi-opening job open until the final available opening is filled, then closes it. A closed job cannot hire another offer; Step 1's rejection path remains available for active applications.

The rollback-only SQL Editor verification passed: one-opening auto-close, second-hire capacity denial, rejection after closure, two-opening closure timing, invalid-stage and unassigned-recruiter denial, terminal protection, generic Hire denial, outbox/history behavior, and privilege checks all passed. No fixture data remained after rollback. Focused hire-route tests: 4 passed. Complete backend suite: 217 passed. Frontend production build: passed.
