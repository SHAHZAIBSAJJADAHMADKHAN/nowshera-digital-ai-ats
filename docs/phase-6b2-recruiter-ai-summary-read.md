# Phase 6B Step 2 — Recruiter AI Summary Read Boundary

Adds only `GET /api/v1/recruiter/applications/{application_id}/ai-summary`. The actual database statuses are `pending`, `processing`, `completed`, and `failed`. The API preserves these states; a missing legacy row is represented as safe `unavailable`. `completed` is the only available state. Every response is marked `is_ai_generated: true`.

The endpoint authenticates with `require_recruiter`, binds authorization to `CurrentUser.user_id`, resolves the exact application, and verifies its current `job_recruiters` assignment. Unknown and unassigned applications return the same 404. Existing RLS grants assigned recruiters AI-summary reads and denies candidate reads; unassignment immediately revokes access. Historical applications are not filtered by stage.

Only the database's approved structured columns are returned: profile bullets (3–5), requirements found, requirements not found, and exactly three interview questions. Raw provider payloads/errors, prompts, CV text, scores, rankings, recommendations, and decisions are excluded. Reads do not mutate applications, history, automation, or summaries. No Gemini/n8n/retry execution is included; retry remains Phase 9.

Focused API tests: 11 passed. The complete backend suite and frontend production build are recorded in the Phase 6B closure gate.

## Closure verification status (2026-09-23)

The environment remediation is deployed: `20260923170000_grant_service_role_backend_table_access.sql` resolved the previous `42501` service-role table-access failure, and the publishable key, JWT issuer, and JWKS URL are configured. JWKS is reachable and service-role reads succeeded for profiles, jobs, assignments, CVs, applications, stage history, notes, and AI summaries.

A tagged, fully cleaned R1/R2/C1/C2/J1/J2/A1/A2 live fixture verified pending, processing, completed, failed, and missing AI states; exact application isolation; current-assignment API authorization; direct authenticated recruiter and candidate RLS; candidate API privacy; decision-safe response allowlisting; immutable application stage/history; immediate AI and notes revocation on unassignment; and reassignment restoration. No automation event, Gemini/n8n call, retry, email resend, or fixture data remained. Focused tests: 26 passed. Complete suite: 201 passed. Frontend production build: passed.

The historical withdrawn-read check was intentionally not run in this REST-only verification session: its required authoritative `submit_application` then `withdraw_application` flow creates immutable audit records and cannot be rolled back safely without a transaction-capable SQL session. The route itself has no stage filter; rerun that one live check in a rollback-capable database session before claiming the combined Phase 6B gate as fully closed.
