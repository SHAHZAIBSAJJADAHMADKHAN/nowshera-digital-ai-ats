# Phase 9B-2 Step 1 — dedicated AI event claim boundary

`public.claim_ai_summary_events(p_limit)` is a service-role-only atomic claim RPC. It selects only eligible pending `ai_summary_requested` rows, respects `available_at`, locks candidates with `FOR UPDATE SKIP LOCKED`, changes rows to `processing`, and increments `attempt_count`.

The returned batch contains only `event_id`, `application_id`, `attempt_count`, and `created_at`. It contains no CV text, candidate PII, provider credentials, or storage data. Browser roles cannot execute the RPC.

`POST /api/v1/internal/automation-events/ai/claim` requires the existing constant-time `INTERNAL_AUTOMATION_KEY` check and accepts only a bounded `limit`; it does not accept event types. Existing completion and failure endpoints settle the claimed event and remain shared lifecycle infrastructure.

The email claim RPC/schema/workflow remain unchanged and continue to reject `ai_summary_requested`. A future dedicated AI n8n worker will claim from this endpoint, call the internal AI processing endpoint with the application ID, then settle the exact event. No worker, Gemini call, or n8n execution is created in this step.
