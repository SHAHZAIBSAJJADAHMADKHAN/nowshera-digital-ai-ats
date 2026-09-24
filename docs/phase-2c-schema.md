# Phase 2C — Interviews, AI Summaries, Outbox, and Audit Logs

## Interviews

`interviews` represents one official current interview per application, enforced by a unique `application_id`. Interviews are exactly one hour and require a nonblank location or meeting link.

The `btree_gist` extension enables a PostgreSQL exclusion constraint over a half-open `tstzrange`. This prevents overlapping interviews for a recruiter while allowing adjacent meetings (for example, 10:00–11:00 followed by 11:00–12:00). The future-only rule is intentionally enforced by the Phase 2D transaction/backend layer, because a time-dependent `CHECK` using `now()` would be incorrect after insertion.

## AI summaries

`ai_summaries` is one-to-one with applications and tracks the current state using `pending`, `processing`, `completed`, or `failed`. Completed summaries require structured JSON arrays: 3–5 profile bullets, requirements-found and requirements-not-found arrays, and exactly three interview questions. Database structure cannot enforce semantic AI safety; prompt-injection defense, sensitive-attribute handling, and no-ranking/no-recommendation rules belong to the AI layer.

## Automation outbox

`automation_events` is the future transactional outbox. A unique nonblank `idempotency_key` is the database foundation for retry-safe event delivery. Status, attempts, `available_at`, `processed_at`, payload, and error data support future worker/n8n processing without implementing it now.

## Audit logs and actors

`audit_logs` is append-only: updates and deletes are blocked by a trigger. User-originated events use `actor_id` and `actor_role`; system/automation events leave both nullable actor fields empty. If a referenced profile is later removed, `actor_id` becomes null while the audit entry remains.

## Security and deferred work

All four tables have RLS enabled with no temporary permissive policies. Future policies must keep AI summaries and recruiter-private information inaccessible to candidates.

Phase 2D will implement scheduling eligibility, future-date enforcement, stage transitions/history writes, transactional outbox writes, AI generation/retries, automatic audit event selection, and all APIs/workflows.
