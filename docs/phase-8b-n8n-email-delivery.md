# Phase 8B — n8n email delivery workflows

## Workflow

The importable workflow is [`nowshera-digital-email-delivery.json`](../n8n/workflows/nowshera-digital-email-delivery.json). One inactive worker has both manual and five-minute polling triggers. It claims email work only through the protected FastAPI API, expands events, routes four event types, sends with an n8n Gmail credential, then invokes the appropriate callback.

## Recipient resolution and privacy

Phase 8A outbox payloads deliberately contain IDs, not recipient PII. Phase 8B adds a service-only claim projection that atomically claims and returns only the delivery fields needed by n8n: candidate email/name, job title, and interview starts-at/location/meeting link when applicable. It never persists those fields to `automation_events`, and it does not return CV data, AI summaries, recruiter notes, audit data, credentials, or the internal key.

## Event and email mapping

| Event | Subject/purpose | Safe data used |
| --- | --- | --- |
| `application_received` | Application Received | candidate name, job title, Applied confirmation |
| `interview_invitation` | Interview Invitation | candidate name, job title, authoritative schedule/location or meeting link |
| `application_hired` | Application Update | candidate name, job title, Hired confirmation |
| `application_rejected` | Application Update | candidate name, job title, neutral status update |

The workflow excludes `ai_summary_requested`. It makes no claim about AI selecting, ranking, rejecting, or hiring anyone. Hiring remains a human decision.

## Delivery state and security

The workflow sends `X-Internal-Automation-Key` through an n8n environment expression, never a literal. Gmail uses a named n8n OAuth2 credential reference with no credential material committed. Gmail success calls complete; its error output calls fail with a fixed safe diagnostic. Phase 8A still owns `FOR UPDATE SKIP LOCKED` claiming, retry after five minutes for attempts one/two, terminal failure on attempt three, unique business idempotency keys, and idempotent completion.

## Verification and remaining gate

The workflow JSON is structurally validated locally. Focused backend contract tests verify safe candidate delivery fields and exclusion of AI/notes/secrets. Connected Supabase verification uses synthetic rolled-back fixtures to validate all four event projections, AI exclusion, completed non-reclaimability, retry behavior, function privileges, and browser outbox denial. Real provider delivery remains pending a separately configured n8n Gmail credential and designated test recipient; no real candidate email is sent in this phase.
