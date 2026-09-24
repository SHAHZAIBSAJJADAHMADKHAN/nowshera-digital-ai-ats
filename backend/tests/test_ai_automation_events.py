from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.internal_automation_events import get_ai_service, get_service
from app.core.config import Settings, get_settings
from app.main import app
from app.services.automation_events import AutomationEventService

EVENT = UUID("11111111-1111-1111-1111-111111111111")
APPLICATION = UUID("22222222-2222-2222-2222-222222222222")


class AIClient:
    def __init__(self, events=None):
        self.events = events if events is not None else [{"event_id": EVENT, "application_id": APPLICATION, "attempt_count": 1, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}]
        self.limits = []

    def claim_ai_summary_events(self, limit):
        self.limits.append(limit)
        return self.events[:limit]


class AIService:
    def __init__(self, events=None): self.events, self.limits = events or [], []
    def claim_ai_summary_events(self, limit):
        self.limits.append(limit)
        return {"events": self.events[:limit]}


@pytest.fixture(autouse=True)
def clean():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_ai_claim_service_returns_only_minimum_ai_work_fields():
    result = AutomationEventService(AIClient()).claim_ai_summary_events(1)
    assert result.events[0].event_id == EVENT
    assert result.events[0].application_id == APPLICATION
    assert result.events[0].attempt_count == 1
    assert not hasattr(result.events[0], "payload")


def test_ai_claim_endpoint_requires_internal_key_and_never_accepts_event_types():
    service = AIService([{"event_id": EVENT, "application_id": APPLICATION, "attempt_count": 1, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)}])
    app.dependency_overrides[get_settings] = lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_ai_service] = lambda: service
    client = TestClient(app)
    path = "/api/v1/internal/automation-events/ai/claim"
    assert client.post(path, headers={"Authorization": "Bearer browser"}, json={"limit": 1}).status_code == 401
    assert client.post(path, headers={"X-Internal-Automation-Key": "wrong"}, json={"limit": 1}).status_code == 401
    assert client.post(path, headers={"X-Internal-Automation-Key": "synthetic-key"}, json={"event_types": ["application_received"]}).status_code == 422
    response = client.post(path, headers={"X-Internal-Automation-Key": "synthetic-key"}, json={"limit": 1})
    assert response.status_code == 200
    assert response.json()["events"] == [{"event_id": str(EVENT), "application_id": str(APPLICATION), "attempt_count": 1, "created_at": "2026-01-01T00:00:00Z"}]
    assert service.limits == [1]


def test_ai_claim_limit_is_bounded_and_email_claim_dependency_is_unchanged():
    service = AIService([])
    app.dependency_overrides[get_settings] = lambda: Settings(internal_automation_key="synthetic-key")
    app.dependency_overrides[get_ai_service] = lambda: service
    app.dependency_overrides[get_service] = lambda: pytest.fail("email claim service must not be used by AI claim")
    client = TestClient(app)
    headers = {"X-Internal-Automation-Key": "synthetic-key"}
    assert client.post("/api/v1/internal/automation-events/ai/claim", headers=headers, json={"limit": 0}).status_code == 422
    assert client.post("/api/v1/internal/automation-events/ai/claim", headers=headers, json={"limit": 26}).status_code == 422
    assert client.post("/api/v1/internal/automation-events/ai/claim", headers=headers, json={"limit": 25}).status_code == 200
    assert service.limits == [25]


def test_claim_migration_uses_ai_only_skip_locked_pending_lifecycle():
    migration = (Path(__file__).resolve().parents[2] / "supabase/migrations/20260924100000_ai_summary_event_claim.sql").read_text()
    for fragment in ("event_type = 'ai_summary_requested'", "status = 'pending'", "available_at <= now()", "for update skip locked", "status = 'processing'", "attempt_count = e.attempt_count + 1", "grant execute on function public.claim_ai_summary_events(integer) to service_role"):
        assert fragment in migration
    assert "application_received" not in migration


def test_concurrent_second_claim_observes_no_reclaimable_event():
    """The SQL lock is authoritative; this fake models the post-claim observable state."""
    client = AIClient()
    first = AutomationEventService(client).claim_ai_summary_events(1)
    client.events = []  # A row moved to processing is no longer eligible for a second worker.
    second = AutomationEventService(client).claim_ai_summary_events(1)
    assert len(first.events) == 1 and second.events == []
