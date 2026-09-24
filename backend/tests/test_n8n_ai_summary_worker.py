import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / "n8n/workflows/nowshera-digital-ai-summary-worker.json"
EMAIL_WORKFLOW_PATH = ROOT / "n8n/workflows/nowshera-digital-email-delivery.json"
PAIR_EXPRESSION = "$('Prepare AI Process Request').item.json.event_id"


def workflow():
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_ai_worker_is_valid_inactive_and_separate_from_email_workflow():
    data = workflow()
    assert data["name"] == "Nowshera Digital — AI CV Summary Worker"
    assert data["active"] is False
    assert EMAIL_WORKFLOW_PATH.exists()
    assert data != json.loads(EMAIL_WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_ai_worker_claims_only_the_dedicated_endpoint_and_processes_each_application():
    data = workflow()
    serialized = json.dumps(data)
    assert "/api/v1/internal/automation-events/ai/claim" in serialized
    claim = next(node for node in data["nodes"] if node["name"] == "Claim AI Summary Events")
    assert claim["parameters"]["jsonBody"] == "={\"limit\":10}"
    assert "event_types" not in serialized
    assert "/api/v1/internal/ai-summaries/' + $json.application_id + '/process" in serialized
    assert "ai_summary_requested" not in serialized  # The backend, not a caller-controlled body, chooses the event type.


def test_ai_worker_preserves_exact_paired_event_id_for_both_settlement_paths():
    data = workflow()
    serialized = json.dumps(data)
    assert serialized.count(PAIR_EXPRESSION) == 2
    assert "/complete" in serialized and "/fail" in serialized
    assert ".first()" not in serialized
    assert "pairedItem: { item: 0 }" in serialized
    assert "pairedItem: { item: index }" in serialized
    process = next(node for node in data["nodes"] if node["name"] == "Process AI Summary")
    assert process["onError"] == "continueErrorOutput"


def test_ai_worker_has_no_provider_email_or_hardcoded_secret_material():
    data = workflow()
    serialized = json.dumps(data).lower()
    node_types = {node["type"] for node in data["nodes"]}
    assert "n8n-nodes-base.gmail" not in node_types
    assert "gemini" not in serialized
    assert "api_key" not in serialized
    assert "ats_internal_api_base_url" in serialized
    assert "internal_automation_key" in serialized
