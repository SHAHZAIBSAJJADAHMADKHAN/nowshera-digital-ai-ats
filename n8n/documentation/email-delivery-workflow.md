# Phase 8B n8n email delivery workflow

Import [`nowshera-digital-email-delivery.json`](../workflows/nowshera-digital-email-delivery.json) into n8n. It is inactive by default and contains no credentials or secret values.

## Architecture and configuration

The workflow starts on a five-minute schedule (or its manual trigger), claims work from `POST {ATS_INTERNAL_API_BASE_URL}/api/v1/internal/automation-events/claim`, expands returned events, routes four event types, sends through the Gmail node, and then calls either complete or fail.

Configure these n8n environment variables:

- `ATS_INTERNAL_API_BASE_URL`: the trusted FastAPI base URL, without a trailing API path.
- `INTERNAL_AUTOMATION_KEY`: the same server-to-server secret configured in the ignored backend environment.

The workflow passes this value only in the `X-Internal-Automation-Key` request header. Configure an n8n Gmail OAuth2 credential named **Nowshera Digital Gmail (configure after import)**, or select the equivalent credential after import. No OAuth token, refresh token, password, or provider setting is committed.

## Claim and routing

The claim request explicitly allows only:

- `application_received`
- `interview_invitation`
- `application_hired`
- `application_rejected`

`ai_summary_requested` is absent from both the workflow and the server-side email claim RPC. A zero-event claim expands to zero items and ends cleanly.

The service-only claim projection resolves the minimum required candidate-facing data after it atomically claims the row: candidate email/name, job title, and—only for an interview—authoritative starts-at, location, and meeting link. It does not add PII to the persisted outbox payload and returns no CV, AI summary, recruiter note, audit data, or internal secret.

## Email content

The workflow creates responsive, simple HTML emails with plain wording and no remote assets or tracking pixels. Application Received confirms Applied; Interview Invitation uses the authoritative appointment details; Hired confirms Hired without inventing terms; Rejected is respectful and neutral. None describe AI as making a decision or disclose scoring, notes, or rejection reasons.

## Completion, failure, and idempotency

The Gmail node uses n8n's `continueErrorOutput` mode. Its success output alone invokes `POST .../{event_id}/complete`; its error output invokes `POST .../{event_id}/fail` with a fixed safe diagnostic rather than the provider's raw error. The Phase 8A database lifecycle retries attempts one and two after five minutes and makes attempt three terminal. Claim locking prevents concurrent workers; completed rows are never reclaimed; completion itself is idempotent. The provider should use `event_id` as its idempotency reference if it supports one.

## Safe validation and live sending

Validate the JSON before import, import with the workflow inactive, set the two environment variables and a Gmail credential, then use the manual trigger with a designated test recipient only. Confirm the success path transitions the event to `completed`, and deliberately test a non-delivery configuration only against a synthetic event to confirm the fail callback/retry path. Do not enable the schedule or send to real candidates until the credential/live-delivery gate is authorized.
