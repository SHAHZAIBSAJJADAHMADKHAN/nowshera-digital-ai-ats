# Phase 9A — AI CV summary backend foundation

## Architecture

Application submission already creates one pending `ai_summaries` row and an ID-only `ai_summary_requested` outbox event. Phase 9A preserves that transaction and adds service-only result ingestion plus authorized retry. No Gemini, n8n, email provider, or application-stage operation is called.

## Contract and snapshot

Completed results require exactly 3–5 factual `profile_summary` bullets, `requirements_analysis` split into mentioned/not-found arrays, and exactly 3 `interview_questions`. The internal API rejects extra fields and malformed outcomes. The work is always tied to `applications.cv_id`, the immutable CV snapshot selected at submission; subsequent candidate CV uploads cannot alter it.

## Safety and privacy

The provider instruction contract treats CV content as untrusted data, ignores embedded instructions/prompt injection, prohibits sensitive-attribute inference (age, gender, religion, marital status), and forbids scores, ranking, recommendations, or employment decisions. AI summaries remain decision-support only.

Candidate reads remain denied by existing RLS and API authorization. Assigned recruiters retain the existing read endpoint; admins have a server-authorized read endpoint. Result ingestion requires the Phase 8 internal automation key, so a browser JWT alone is insufficient. The trusted result only accepts `completed` or `failed` states and safe failure text.

## Retry and failure

An assigned recruiter or admin can retry a failed/unavailable summary. The service-only RPC creates a distinct `ai_summary_requested` retry event, resets the summary to pending, and does not touch the application stage or create `application_received` email events. AI failure leaves the application intact. AI events remain excluded from Phase 8 email claims.

## Deferred

Phase 9B will implement provider/n8n execution, CV content extraction, trusted work-item resolution, and live integration. No credentials or external automation were configured or executed in Phase 9A.
