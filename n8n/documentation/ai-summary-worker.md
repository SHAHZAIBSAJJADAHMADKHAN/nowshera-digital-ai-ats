# Phase 9B-2 AI summary worker

Import `nowshera-digital-ai-summary-worker.json` as a separate workflow. It is inactive by default and must remain separate from the email delivery workflow.

The worker calls the AI-only internal claim endpoint with `{ "limit": 10 }`, expands its identifier-only results, and calls the internal processing endpoint once per `application_id`. Its processing HTTP node has a success and error output. A successful `204` means the trusted backend handled the application, including controlled Gemini/PDF/validation failures that are persisted as failed AI summaries; the worker completes the corresponding outbox event. An unhandled request failure records the fixed safe diagnostic through the existing fail endpoint.

The workflow preserves `event_id` and `application_id` per item. Completion/failure use n8n paired-item lookup from **Prepare AI Process Request**, so each settlement URL references the matching claimed event in a multi-item batch. It never uses `.first()`.

Configure `ATS_INTERNAL_API_BASE_URL` and `INTERNAL_AUTOMATION_KEY` only through protected n8n environment/credential configuration. The key is sent as `X-Internal-Automation-Key`. No Gemini or Supabase credential belongs in this workflow; Gemini remains backend-only. If the hosted n8n service does not provide environment variables, put the base URL and internal key in an encrypted n8n HTTP-request credential/configuration and keep them out of the exported workflow JSON.

This worker claims only `ai_summary_requested`, never transports CV text, and has no email/Gmail nodes. Live import, activation, and verification remain deferred.
