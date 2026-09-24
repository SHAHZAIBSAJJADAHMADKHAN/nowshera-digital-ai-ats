# Phase 8A email outbox contract

n8n polls the ATS internal API; it never reads `automation_events` from a browser client and it must not call business lifecycle RPCs.

## Configuration

Set `INTERNAL_AUTOMATION_KEY` only in the ignored backend environment and configure the same value in n8n's encrypted credential store. Send it as `X-Internal-Automation-Key`. This is server-to-server authentication; a Supabase browser JWT is not a substitute.

## Poll and settle sequence

1. `POST /api/v1/internal/automation-events/claim` with `{ "event_types": [..], "limit": 10 }`.
2. Route each returned event by `event_type`, resolve necessary recipient data through a future trusted integration, then invoke the provider.
3. On confirmed provider acceptance, call `POST /api/v1/internal/automation-events/{event_id}/complete`.
4. On delivery failure, call `POST /api/v1/internal/automation-events/{event_id}/fail` with a short safe diagnostic (maximum 500 characters, no credentials or provider stack trace).

Atomic claim changes an eligible event from `pending` to `processing` with `FOR UPDATE SKIP LOCKED` and increments `attempt_count`. A second worker cannot claim it. Completion is idempotent: a repeat returns the completed record. Failure returns attempts one and two to `pending` after five minutes; attempt three becomes terminal `failed`. Completed and terminal failed events are never claimed again.

## Email event map

| Event type | Aggregate | Payload |
| --- | --- | --- |
| `application_received` | `application` | `{ "application_id": "uuid" }` |
| `interview_invitation` | `interview` | `{ "application_id": "uuid", "interview_id": "uuid", "starts_at": "timestamptz" }` |
| `application_hired` | `application` | `{ "application_id": "uuid" }` |
| `application_rejected` | `application` | `{ "application_id": "uuid" }` |

`ai_summary_requested` is deliberately excluded. Phase 9 owns AI processing, and the email claim operation rejects it.

## Idempotency and safety

Business RPCs create each logical event using the existing unique `idempotency_key`. Delivery workers should also use `event_id` as their provider-facing idempotency reference where supported. Do not complete an event until the provider accepts it. This phase creates no provider credentials, email templates, or external calls.

Recruiter password/setup invitations remain owned by the existing Supabase Auth invite flow; n8n must not send a duplicate recruiter invitation.
