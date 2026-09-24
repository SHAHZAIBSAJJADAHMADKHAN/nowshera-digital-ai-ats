from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.internal_automation_events import get_service
from app.core.automation_auth import require_internal_automation
from app.core.config import Settings, get_settings
from app.main import app

EVENT_ID = UUID("11111111-1111-1111-1111-111111111111")
AGGREGATE_ID = UUID("22222222-2222-2222-2222-222222222222")


class Service:
    def __init__(self):
        self.claimed = []
        self.completed = []
        self.failed = []

    def claim(self, event_types, limit):
        self.claimed.append((event_types, limit))
        return {"events": [{"event_id": EVENT_ID, "event_type": "application_received", "aggregate_type": "application", "aggregate_id": AGGREGATE_ID, "payload": {"application_id": str(AGGREGATE_ID)}, "attempt_count": 1, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "recipient_email": "candidate@example.invalid", "candidate_name": "Synthetic Candidate", "job_title": "Synthetic Role", "interview_starts_at": None, "interview_location": None, "interview_meeting_link": None}]}

    def complete(self, event_id):
        self.completed.append(event_id)
        return {"event_id": event_id, "status": "completed", "attempt_count": 1, "processed_at": datetime(2026, 1, 1, tzinfo=timezone.utc), "available_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}

    def fail(self, event_id, error):
        self.failed.append((event_id, error))
        return {"event_id": event_id, "status": "pending", "attempt_count": 1, "processed_at": None, "available_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}


@pytest.fixture(autouse=True)
def clean_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_internal_auth_requires_matching_configured_key():
    settings = Settings(internal_automation_key="synthetic-key")
    with pytest.raises(HTTPException) as missing:
        require_internal_automation(settings, None)
    with pytest.raises(HTTPException) as wrong:
        require_internal_automation(settings, "wrong")
    assert missing.value.status_code == 401
    assert wrong.value.status_code == 401
    assert require_internal_automation(settings, "synthetic-key") is None


@pytest.mark.parametrize("browser_authorization", ["Bearer candidate", "Bearer recruiter", "Bearer admin"])
def test_browser_jwt_cannot_replace_internal_key(browser_authorization):
    service = Service()
    app.dependency_overrides[get_settings] = lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_service] = lambda: service
    response = TestClient(app).post("/api/v1/internal/automation-events/claim", headers={"Authorization": browser_authorization}, json={"event_types": ["application_received"], "limit": 1})
    assert response.status_code == 401
    assert service.claimed == []


def test_email_claim_contract_has_only_safe_candidate_delivery_fields():
    event = Service().claim(["application_received"], 1)["events"][0]
    assert event["recipient_email"] == "candidate@example.invalid"
    assert event["candidate_name"] == "Synthetic Candidate"
    assert event["job_title"] == "Synthetic Role"
    assert "ai_summary" not in event
    assert "recruiter_notes" not in event
    assert "internal_automation_key" not in event


def test_claim_complete_and_fail_contracts_are_internal_only():
    service = Service()
    app.dependency_overrides[get_settings] = lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    headers = {"X-Internal-Automation-Key": "synthetic-key"}
    claim = client.post("/api/v1/internal/automation-events/claim", headers=headers, json={"event_types": ["application_received", "application_hired"], "limit": 1})
    assert claim.status_code == 200
    assert claim.json()["events"][0]["event_type"] == "application_received"
    assert service.claimed == [(["application_received", "application_hired"], 1)]
    complete = client.post(f"/api/v1/internal/automation-events/{EVENT_ID}/complete", headers=headers)
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    failed = client.post(f"/api/v1/internal/automation-events/{EVENT_ID}/fail", headers=headers, json={"error": "provider timed out"})
    assert failed.status_code == 200
    assert failed.json()["status"] == "pending"
    assert service.failed == [(EVENT_ID, "provider timed out")]


def test_claim_only_accepts_authoritative_email_event_types():
    service = Service()
    app.dependency_overrides[get_settings] = lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_service] = lambda: service
    response = TestClient(app).post("/api/v1/internal/automation-events/claim", headers={"X-Internal-Automation-Key": "synthetic-key"}, json={"event_types": ["ai_summary_requested"], "limit": 1})
    assert response.status_code == 422
    assert service.claimed == []
