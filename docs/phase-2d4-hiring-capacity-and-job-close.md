# Phase 2D-4 — Hiring Capacity and Auto-Close

`hire_application` is the only approved `offer → hired` operation. It validates an active assigned recruiter, discovers the job, locks the job row first, then locks and rechecks the application. Capacity is derived from committed `hired` applications for the locked job—there is no mutable remaining-openings counter.

If capacity remains, the transaction writes the hire, stage history, deterministic `application-hired:<application-id>` outbox event, and audit record. Filling the final opening closes the job and appends a separate auto-close audit entry in the same transaction. Other active applications are retained but, because the job is closed, may only be rejected by the existing state machine.

Submission already rejects expired deadlines. Deadline status synchronization and manual admin close are deferred to later service/automation work. The RPC is SECURITY DEFINER, uses an empty search path, and is service-role-only; FastAPI must bind the JWT subject to the recruiter ID.
