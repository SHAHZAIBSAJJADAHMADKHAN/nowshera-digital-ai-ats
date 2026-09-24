# Phase 9B-2 Step 2 — n8n AI worker

The dedicated inactive n8n workflow polls the Step 1 AI-only claim endpoint, expands the identifier-only batch, sends each application ID to the internal FastAPI processor, and settles the exact claimed event with the existing Phase 8 endpoints.

Expected processing failures are handled by the backend: it persists a safe failed `ai_summaries` result and responds successfully, so the worker completes that outbox event. Only unhandled request/delivery failures call the shared fail endpoint, retaining Phase 8 retry and terminal-failure semantics.

Each batch item carries its own event/application IDs. The settlement nodes use paired-item correlation from the preparation node, rather than a fixed item or `.first()`, preventing cross-event settlement in multi-item batches.

The workflow uses protected `ATS_INTERNAL_API_BASE_URL` and `INTERNAL_AUTOMATION_KEY` configuration only. It does not include Gemini/Supabase credentials, raw CV text, email nodes, or candidate-facing actions. The email worker remains unchanged and claims only email event types.

Live import, protected configuration, activation, and Gemini end-to-end verification are deferred.
