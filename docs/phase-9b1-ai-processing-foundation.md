# Phase 9B-1 — AI processing foundation

## Exact CV work item

The trusted processor resolves an application by ID using `applications.cv_id`, then joins the referenced `candidate_cvs` row and job. It verifies that the joined CV ID equals the immutable application snapshot before downloading the object's private `storage_path`. It never accepts a CV ID from a browser, and never queries a candidate's newest CV.

## Private PDF extraction

CV objects remain in the existing private `candidate-cvs` Supabase Storage bucket. The backend service-role client downloads the resolved object server-side, checks the recorded PDF MIME type and existing 2 MiB size limit, and uses pinned `pypdf` to extract text. Corrupt, invalid, over-sized, and textless PDFs become controlled failed AI summaries; no stage is changed.

## Gemini provider and configuration

`app.ai.gemini.GeminiProvider` is a small HTTP provider abstraction, invoked only by `AIProcessingService`, never by a route handler or browser. `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.0-flash`), and the optional timeout come from server settings. Startup succeeds without a key; processing records a safe unavailable failure when it is invoked without configuration. Tests use fakes, so no network or real key is required.

## Safety and output validation

The existing Phase 9A instruction remains the single safety contract. Prompt construction labels CV content as `<cv_untrusted_data>`, retains the prompt-injection instruction, forbids sensitive-attribute use/inference (age, gender, religion, marital status), and forbids scoring, ranking, recommendations, and decisions. Provider text is treated as untrusted: it must parse as JSON, have no prohibited decision/scoring fields, satisfy the existing strict Pydantic shape, have 3–5 nonempty profile bullets, and exactly 3 nonempty interview questions.

## Failure and trusted boundary

`POST /api/v1/internal/ai-summaries/{application_id}/process` requires the existing Phase 8 internal automation key. A normal browser JWT cannot invoke it. It returns no CV text or provider data. Controlled provider, timeout, malformed-result, configuration, and extraction failures are persisted through the existing Phase 9A `save_ai_summary_result` RPC as a safe failed result. The processing code has no application-stage or email/outbox write path; `application_received` emails are not created or resent.

## Future n8n handoff

When academy infrastructure is restored, the workflow should claim only `ai_summary_requested`, invoke the internal process endpoint with its server-to-server key, then complete/fail that automation event. The processor resolves the work item, extracts the snapshot, calls Gemini, validates it, and reuses Phase 9A result persistence. AI and email events remain separate. No workflow was executed, published, or activated in this phase.

## Automated coverage

Focused tests cover immutable CV resolution, valid/corrupt/textless PDF handling, valid and malformed provider output, counts and prohibited fields, missing configuration/provider failure, safe persistence, and deterministic prompt-injection and sensitive-attribute guards. Phase 9A action tests remain regression coverage.

**LIVE N8N/GEMINI END-TO-END VERIFICATION IS DEFERRED.**
