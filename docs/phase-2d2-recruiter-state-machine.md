# Phase 2D-2 — Recruiter State Machine

`transition_recruiter_application` is a locked, service-role-only operation. It validates an active recruiter profile and an assignment in `job_recruiters` before locking and re-reading the application stage.

Allowed ordinary transitions are only `applied → shortlisted` and `interview → offer`. Rejection is allowed from `applied`, `shortlisted`, `interview`, or `offer`; it is terminal. Hired, rejected, and withdrawn applications cannot change. For closed jobs, rejection is the only permitted action.

`shortlisted → interview` is reserved for Phase 2D-3 interview scheduling, and `offer → hired` is reserved for Phase 2D-4 capacity-safe hiring. Successful actions atomically update the application, append history, and append an audit log. Rejection additionally queues a deterministic `application-rejected:<application-id>` event.

The application row is locked with `FOR UPDATE`, which serializes concurrent recruiter actions and checks the current post-lock stage. The function is `SECURITY DEFINER` with an empty search path, revoked from browser roles, and granted only to `service_role`. Future FastAPI code must verify its JWT subject matches the supplied recruiter ID.
