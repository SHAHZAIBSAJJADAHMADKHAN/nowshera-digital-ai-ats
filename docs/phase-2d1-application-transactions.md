# Phase 2D-1 — Application Submission and Withdrawal

`submit_application` atomically validates an active candidate, an open future-deadline job with positive current openings, and a candidate-owned CV. It always writes an `applied` application, initial stage history, pending AI summary, two deterministic outbox events, and a minimal audit record. Any failure rolls back every write.

The CV ID is stored directly and protected by the existing composite FK; later uploads cannot change an existing application's snapshot. Outbox keys are `application-received:<application-id>` and `ai-summary:<application-id>`.

`withdraw_application` locks the candidate-owned application, permits only active pre-final stages, then atomically marks it withdrawn, timestamps it, records history, and appends an audit entry. Withdrawn rows remain historical and the partial unique index permits a later application using a new CV.

Both functions are `SECURITY DEFINER` with an empty search path. Browser roles have no execute permission; only `service_role` may call them. Candidate identity is therefore supplied by the trusted future backend, not a browser RPC. The backend must verify the authenticated JWT subject matches `p_candidate_id` before invocation; direct candidate RPC access will be added only with the later Auth/RLS design.

General recruiter transitions, interview scheduling, hiring capacity consumption, and business APIs remain deferred.
