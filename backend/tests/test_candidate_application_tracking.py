from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_application_tracking import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.integrations.supabase_admin import SupabaseAdminClient
from app.main import app
from app.schemas.candidate_application_tracking import CandidateApplicationDetailResponse, CandidateApplicationListResponse
from app.services.candidate_application_tracking import CandidateApplicationTrackingNotFoundError, CandidateApplicationTrackingOperationError, CandidateApplicationTrackingService


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ID = "99999999-9999-9999-9999-999999999999"
APP_ID = UUID("22222222-2222-2222-2222-222222222222")
SECOND_APP_ID = UUID("33333333-3333-3333-3333-333333333333")
JOB_ID = UUID("44444444-4444-4444-4444-444444444444")
CV_ID = UUID("55555555-5555-5555-5555-555555555555")
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
LIST_FIELDS = {"id", "stage", "applied_at", "job", "cv"}
DETAIL_FIELDS = LIST_FIELDS | {"stage_history", "interview"}


def listed(application_id: UUID = APP_ID, stage: str = "applied", applied_at: datetime = NOW) -> CandidateApplicationListResponse:
    return CandidateApplicationListResponse.model_validate({
        "id": application_id, "stage": stage, "applied_at": applied_at,
        "job": {"id": JOB_ID, "title": "Closed historical job", "department": "Engineering", "location": "Remote", "job_type": "full-time", "application_deadline": NOW - timedelta(days=1)},
        "cv": {"id": CV_ID, "original_filename": "submitted-cv-1.pdf", "uploaded_at": NOW - timedelta(days=2)},
    })


def detailed() -> CandidateApplicationDetailResponse:
    return CandidateApplicationDetailResponse.model_validate({
        **listed().model_dump(),
        "job": {**listed().job.model_dump(), "description": "Safe description", "requirements": "Safe requirements"},
        "stage_history": [{"stage": "applied", "changed_at": NOW}, {"stage": "interview", "changed_at": NOW + timedelta(days=1)}],
        "interview": {"starts_at": NOW + timedelta(days=2), "ends_at": NOW + timedelta(days=2, hours=1), "location": "Video", "meeting_link": "https://meeting.example.invalid"},
    })


class FakeTrackingService:
    def __init__(self, records: list[CandidateApplicationListResponse] | None = None) -> None:
        self.records = [listed()] if records is None else records
        self.detail = detailed()
        self.list_error: Exception | None = None
        self.detail_error: Exception | None = None
        self.calls: list[tuple[str, object, object | None]] = []

    def list_applications(self, candidate_id: str) -> list[CandidateApplicationListResponse]:
        self.calls.append(("list", candidate_id, None))
        if self.list_error: raise self.list_error
        return self.records

    def get_application(self, candidate_id: str, application_id: UUID) -> CandidateApplicationDetailResponse:
        self.calls.append(("detail", candidate_id, application_id))
        if self.detail_error: raise self.detail_error
        return self.detail


@pytest.fixture
def client_factory():
    def create(role: str = "candidate", service: FakeTrackingService | None = None) -> tuple[TestClient, FakeTrackingService]:
        fake = service or FakeTrackingService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "candidate@example.com")
        app.dependency_overrides[get_service] = lambda: fake
        return TestClient(app), fake
    yield create
    app.dependency_overrides.clear()


def test_tracking_routes_require_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    client = TestClient(app)
    assert client.get("/api/v1/candidate/applications").status_code == 401
    assert client.get(f"/api/v1/candidate/applications/{APP_ID}").status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_non_candidates_cannot_access_tracking(client_factory, role: str) -> None:
    client, service = client_factory(role)
    assert client.get("/api/v1/candidate/applications").status_code == 403
    assert client.get(f"/api/v1/candidate/applications/{APP_ID}").status_code == 403
    assert service.calls == []


def test_list_uses_authenticated_actor_and_has_safe_allowlist(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/candidate/applications?candidate_id={OTHER_ID}")
    assert response.status_code == 200 and set(response.json()[0]) == LIST_FIELDS
    assert service.calls == [("list", ACTOR_ID, None)]
    assert "storage_path" not in response.text and "recruiter" not in response.text.lower() and "ai_" not in response.text.lower()


@pytest.mark.parametrize("stage", ["applied", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"])
def test_all_current_and_terminal_stages_remain_visible(client_factory, stage: str) -> None:
    client, _ = client_factory(service=FakeTrackingService([listed(stage=stage)]))
    response = client.get("/api/v1/candidate/applications")
    assert response.status_code == 200 and response.json()[0]["stage"] == stage


def test_closed_or_expired_job_and_multiple_history_records_remain_distinct(client_factory) -> None:
    records = [listed(APP_ID, "withdrawn", NOW), listed(SECOND_APP_ID, "applied", NOW - timedelta(days=1))]
    client, _ = client_factory(service=FakeTrackingService(records))
    response = client.get("/api/v1/candidate/applications")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(APP_ID), str(SECOND_APP_ID)]
    assert all(item["job"]["application_deadline"] < NOW.isoformat().replace("+00:00", "Z") for item in response.json())


def test_empty_list_is_safe(client_factory) -> None:
    client, _ = client_factory(service=FakeTrackingService([]))
    assert client.get("/api/v1/candidate/applications").json() == []


def test_detail_returns_exact_snapshot_chronological_history_and_safe_interview(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/candidate/applications/{APP_ID}")
    assert response.status_code == 200 and set(response.json()) == DETAIL_FIELDS
    assert response.json()["cv"]["id"] == str(CV_ID)
    assert [item["stage"] for item in response.json()["stage_history"]] == ["applied", "interview"]
    assert set(response.json()["interview"]) == {"starts_at", "ends_at", "location", "meeting_link"}
    assert service.calls == [("detail", ACTOR_ID, APP_ID)]
    for forbidden in ("recruiter_id", "notes", "ai_summary", "storage_path", "created_by"):
        assert forbidden not in response.text


@pytest.mark.parametrize("state", ["foreign", "unknown"])
def test_foreign_or_unknown_detail_is_privacy_safe_not_found(client_factory, state: str) -> None:
    service = FakeTrackingService(); service.detail_error = CandidateApplicationTrackingNotFoundError(state)
    client, _ = client_factory(service=service)
    response = client.get(f"/api/v1/candidate/applications/{APP_ID}")
    assert response.status_code == 404 and response.json() == {"detail": "Application not found"}
    assert state not in response.text


def test_malformed_application_id_is_validation_error(client_factory) -> None:
    client, service = client_factory()
    assert client.get("/api/v1/candidate/applications/not-a-uuid").status_code == 422
    assert service.calls == []


def test_service_sorts_history_chronologically_and_uses_application_stage() -> None:
    class Client:
        def get_candidate_application(self, candidate_id, application_id):
            return {"id": str(APP_ID), "stage": "offer", "applied_at": NOW.isoformat(), "jobs": {"id": str(JOB_ID), "title": "Job", "department": "Eng", "location": "Remote", "job_type": "full-time", "description": "D", "requirements": "R", "application_deadline": NOW.isoformat()}, "candidate_cvs": {"id": str(CV_ID), "original_filename": "cv-1.pdf", "uploaded_at": NOW.isoformat()}, "application_stage_history": [{"stage": "offer", "changed_at": (NOW + timedelta(days=2)).isoformat()}, {"stage": "applied", "changed_at": NOW.isoformat()}], "interviews": []}
    result = CandidateApplicationTrackingService(Client()).get_application(ACTOR_ID, APP_ID)
    assert result.stage == "offer" and [item.stage for item in result.stage_history] == ["applied", "offer"] and result.interview is None


def test_integration_is_bounded_set_oriented_and_ownership_scoped(monkeypatch) -> None:
    client = SupabaseAdminClient("https://example.supabase.co", "not-a-real-secret")
    captured: dict[str, object] = {}
    class Response:
        def json(self): return []
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: (captured.update(kwargs), Response())[1])
    assert client.list_candidate_applications(ACTOR_ID) == []
    params = captured["params"]
    assert params["candidate_id"] == f"eq.{ACTOR_ID}" and params["limit"] == 100 and params["order"] == "applied_at.desc,id.desc"
    assert "recruiter_notes" not in params["select"] and "ai_summaries" not in params["select"] and "storage_path" not in params["select"]


def test_detail_integration_scopes_owner_and_never_selects_private_data(monkeypatch) -> None:
    client = SupabaseAdminClient("https://example.supabase.co", "not-a-real-secret")
    captured: dict[str, object] = {}
    class Response:
        def json(self): return []
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: (captured.update(kwargs), Response())[1])
    with pytest.raises(LookupError):
        client.get_candidate_application(ACTOR_ID, APP_ID)
    params = captured["params"]
    assert params["candidate_id"] == f"eq.{ACTOR_ID}" and params["id"] == f"eq.{APP_ID}"
    assert "recruiter_notes" not in params["select"] and "ai_summaries" not in params["select"] and "storage_path" not in params["select"]


def test_safe_503_hides_integration_details(client_factory) -> None:
    service = FakeTrackingService(); service.list_error = CandidateApplicationTrackingOperationError("SUPABASE_SECRET_KEY service_role Authorization: Bearer PostgREST raw SQL https://internal")
    client, _ = client_factory(service=service)
    response = client.get("/api/v1/candidate/applications")
    assert response.status_code == 503 and response.json() == {"detail": "Candidate application service is unavailable"}
    for marker in ("supabase_secret_key", "service_role", "authorization: bearer", "postgrest", "raw sql", "internal"):
        assert marker not in response.text.lower()
