# Phase 6C — Recruiter Pipeline Final Gate

## Result: PASS

The final mutation surface is deliberately small:

- `PATCH /api/v1/recruiter/applications/{application_id}/stage` accepts only `shortlisted`, `offer`, and `rejected`.
- `POST /api/v1/recruiter/applications/{application_id}/hire` is the sole recruiter API path to `hired`.

FastAPI requires a current recruiter and binds actor identity to `CurrentUser.user_id`; it never accepts a recruiter identifier. Both authoritative database RPCs revalidate the current assignment and own locking, stage/history/audit writes, and outbox creation.

`transition_recruiter_application(...)` owns Applied→Shortlisted, Interview→Offer, active→Rejected, terminal protection, and the closed-job rule: closed jobs permit only rejection of active applications. `schedule_interview(...)` exclusively owns Shortlisted→Interview and remains Phase 7 work. `hire_application(...)` exclusively owns Offer→Hired, capacity, auto-close, Hired history/outbox, and terminal protection. Its job-row lock prevents concurrent hires from exceeding openings.

Step 1 rollback-only SQL verification passed: progression, generic Interview/Hired blocking, rejection outbox, closed-job rejection, unassigned denial, terminal protection, direct mutation/RPC security, and cleanup. Step 2 rollback-only SQL verification passed: one- and two-opening capacity scenarios, auto-close timing, second-hire denial, post-close rejection, Hired outbox/history, unassigned denial, terminal protection, concurrency guard, and cleanup.

Combined focused regression: 16 passed. Complete backend suite: 217 passed. Frontend production build: passed. Browser roles have no direct application/job update privilege, and privileged mutation RPCs remain service-role-only. No direct email, n8n, Gemini, AI retry, or frontend pipeline UI was introduced.

Phase 6C contributes the recruiter portions of lifecycle Acceptance Test #2, capacity/closure/rejection Acceptance Test #4, and skip/terminal protections in Acceptance Test #5. Phase 7 retains interview scheduling; Phase 8 retains external delivery processing.
