# Phase 8A — Automation outbox and n8n delivery foundation

## Architecture

Authoritative application, interview, rejection, and hire RPCs commit their business change and outbox row in one transaction. External delivery remains outside it:

`business RPC → automation_events → protected internal API → n8n → provider`

The existing outbox has RLS enabled, no browser policies, no `anon`/`authenticated` table grants, a unique `idempotency_key`, and indexes on `(status, available_at)` and aggregate identity. The service role remains the only trusted database caller.

## Delivery lifecycle

Phase 8A adds service-only RPCs for claim, completion, and failure. Claim accepts only existing email events and atomically selects eligible `pending` rows using `FOR UPDATE SKIP LOCKED`, marks them `processing`, and increments `attempt_count`. Completion is restricted to `processing`, records `processed_at`, and is idempotent when already completed. Failure stores a bounded safe message: attempts one and two return to `pending` after five minutes; attempt three is terminal `failed`. No delivery operation changes a business record.

## Protected API

- `POST /api/v1/internal/automation-events/claim`
- `POST /api/v1/internal/automation-events/{event_id}/complete`
- `POST /api/v1/internal/automation-events/{event_id}/fail`

Each route requires `X-Internal-Automation-Key`, compared in constant time. Browser JWTs for Candidate, Recruiter, and Admin do not satisfy this dependency. Only an empty placeholder exists in `.env.example`.

## Event routing

| Event | Aggregate | Payload | Email worker |
| --- | --- | --- | --- |
| `application_received` | application | application ID | included |
| `interview_invitation` | interview | application ID, interview ID, starts-at | included |
| `application_hired` | application | application ID | included |
| `application_rejected` | application | application ID | included |
| `ai_summary_requested` | application | application ID | excluded |

Payloads stay ID-first and add no candidate PII. Phase 9 owns the excluded AI event.

## Recruiter invitations

Recruiter provisioning calls Supabase Auth's invitation endpoint before the service-only profile provisioning RPC. Supabase Auth owns password/setup invitations; Phase 8A creates no duplicate outbox event.

## Verification scope

Focused tests cover internal-key denial/acceptance, browser JWT insufficiency, email-only claim validation, and the claim/complete/fail contracts. Connected Supabase transactional verification covers claim exclusivity, completion idempotency, bounded retry, privileges, and browser RLS denial, with all fixtures rolled back. Phase 8B can use [the delivery contract](../n8n/documentation/email-outbox-contract.md) without changing lifecycle transactions.
