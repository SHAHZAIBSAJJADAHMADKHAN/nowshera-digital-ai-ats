from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_jobs import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.integrations.supabase_admin import SupabaseAdminClient
from app.main import app
from app.schemas.candidate_jobs import CandidateJobDetailResponse, CandidateJobListResponse
from app.services.candidate_jobs import CandidateJobNotFoundError, CandidateJobOperationError

ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ID = "99999999-9999-9999-9999-999999999999"
VISIBLE_ID = UUID("22222222-2222-2222-2222-222222222222")
SECOND_ID = UUID("33333333-3333-3333-3333-333333333333")
THIRD_ID = UUID("44444444-4444-4444-4444-444444444444")
NOW = datetime(2027, 1, 1, tzinfo=timezone.utc)
LIST_FIELDS = {"id", "title", "department", "location", "job_type", "application_deadline", "openings"}
DETAIL_FIELDS = LIST_FIELDS | {"description", "requirements", "created_at"}


def list_job(job_id: UUID = VISIBLE_ID, deadline: datetime = NOW + timedelta(days=1)) -> CandidateJobListResponse:
    return CandidateJobListResponse(id=job_id, title="Open role", department="Engineering", location="Remote", job_type="full-time", application_deadline=deadline, openings=2)


def detail_job(job_id: UUID = VISIBLE_ID, deadline: datetime = NOW + timedelta(days=1)) -> CandidateJobDetailResponse:
    return CandidateJobDetailResponse(**list_job(job_id, deadline).model_dump(), description="Build secure systems.", requirements="Python experience.", created_at=NOW - timedelta(days=2))


class FakeCandidateJobService:
    def __init__(self, listed: list[CandidateJobListResponse] | None = None, detail: CandidateJobDetailResponse | None = None) -> None:
        self.listed = [list_job()] if listed is None else listed
        self.detail = detail or detail_job()
        self.list_error: Exception | None = None
        self.detail_error: Exception | None = None
        self.calls: list[tuple[str, object | None]] = []

    def list_jobs(self) -> list[CandidateJobListResponse]:
        self.calls.append(("list", None))
        if self.list_error:
            raise self.list_error
        return self.listed

    def get_job(self, job_id: UUID) -> CandidateJobDetailResponse:
        self.calls.append(("detail", job_id))
        if self.detail_error:
            raise self.detail_error
        return self.detail


@pytest.fixture
def client_factory():
    def create(role: str = "candidate", service: FakeCandidateJobService | None = None) -> tuple[TestClient, FakeCandidateJobService]:
        fake_service = service or FakeCandidateJobService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "candidate@example.com")
        app.dependency_overrides[get_service] = lambda: fake_service
        return TestClient(app), fake_service

    yield create
    app.dependency_overrides.clear()


def test_candidate_job_routes_require_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    client = TestClient(app)
    assert client.get("/api/v1/candidate/jobs").status_code == 401
    assert client.get(f"/api/v1/candidate/jobs/{VISIBLE_ID}").status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_non_candidates_cannot_access_candidate_job_routes(client_factory, role: str) -> None:
    client, service = client_factory(role)
    assert client.get("/api/v1/candidate/jobs").status_code == 403
    assert client.get(f"/api/v1/candidate/jobs/{VISIBLE_ID}").status_code == 403
    assert service.calls == []


def test_candidate_lists_only_safe_visible_job_fields_and_spoofing_is_ineffective(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/candidate/jobs?candidate_id={OTHER_ID}")
    assert response.status_code == 200 and len(response.json()) == 1
    assert set(response.json()[0]) == LIST_FIELDS
    assert service.calls == [("list", None)]


def test_candidate_reads_safe_visible_job_detail(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/candidate/jobs/{VISIBLE_ID}")
    assert response.status_code == 200 and set(response.json()) == DETAIL_FIELDS
    assert service.calls == [("detail", VISIBLE_ID)]


def test_no_visible_jobs_returns_empty_list(client_factory) -> None:
    client, service = client_factory(service=FakeCandidateJobService(listed=[]))
    response = client.get("/api/v1/candidate/jobs")
    assert response.status_code == 200 and response.json() == []
    assert service.calls == [("list", None)]


@pytest.mark.parametrize("hidden_state", ["draft", "closed", "expired-open", "deadline-at-now", "unknown"])
def test_hidden_or_unavailable_details_are_generic_not_found(client_factory, hidden_state: str) -> None:
    service = FakeCandidateJobService()
    service.detail_error = CandidateJobNotFoundError(hidden_state)
    client, _ = client_factory(service=service)
    response = client.get(f"/api/v1/candidate/jobs/{VISIBLE_ID}")
    assert response.status_code == 404 and response.json() == {"detail": "Job not found"}
    assert hidden_state not in response.text


def test_malformed_job_id_is_validation_error(client_factory) -> None:
    client, service = client_factory()
    assert client.get("/api/v1/candidate/jobs/not-a-uuid").status_code == 422
    assert service.calls == []


def test_discovery_preserves_integration_deadline_then_id_ordering(client_factory) -> None:
    ordered = [list_job(SECOND_ID, NOW + timedelta(days=1)), list_job(THIRD_ID, NOW + timedelta(days=2)), list_job(VISIBLE_ID, NOW + timedelta(days=2))]
    client, _ = client_factory(service=FakeCandidateJobService(listed=ordered))
    response = client.get("/api/v1/candidate/jobs")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(SECOND_ID), str(THIRD_ID), str(VISIBLE_ID)]


def test_integration_requests_open_future_jobs_with_deterministic_bounded_order(monkeypatch) -> None:
    client = SupabaseAdminClient("https://example.supabase.co", "not-a-real-secret")
    captured: dict[str, object] = {}

    class Response:
        def json(self): return []

    def request(method, path, **kwargs):
        captured.update({"method": method, "path": path, **kwargs})
        return Response()

    monkeypatch.setattr(client, "_request", request)
    assert client.list_candidate_jobs() == []
    params = captured["params"]
    assert isinstance(params, dict)
    assert params["status"] == "eq.open" and params["application_deadline"].startswith("gt.")
    assert params["order"] == "application_deadline.asc,id.asc" and params["limit"] == 100
    assert set(params["select"].split(",")) == LIST_FIELDS


def test_detail_integration_uses_same_visibility_predicate_and_safe_allowlist(monkeypatch) -> None:
    client = SupabaseAdminClient("https://example.supabase.co", "not-a-real-secret")
    captured: dict[str, object] = {}

    class Response:
        def json(self): return []

    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: (captured.update(kwargs), Response())[1])
    with pytest.raises(LookupError):
        client.get_candidate_job(str(VISIBLE_ID))
    params = captured["params"]
    assert params["id"] == f"eq.{VISIBLE_ID}" and params["status"] == "eq.open"
    assert params["application_deadline"].startswith("gt.")
    assert set(params["select"].split(",")) == DETAIL_FIELDS


def test_candidate_job_failures_are_normalized_without_secret_leakage(client_factory) -> None:
    service = FakeCandidateJobService()
    leaked = "SUPABASE_SECRET_KEY service_role Authorization: Bearer PostgREST https://internal.supabase.co raw SQL"
    service.list_error = CandidateJobOperationError(leaked)
    service.detail_error = CandidateJobOperationError(leaked)
    client, _ = client_factory(service=service)
    for response in (client.get("/api/v1/candidate/jobs"), client.get(f"/api/v1/candidate/jobs/{VISIBLE_ID}")):
        assert response.status_code == 503 and response.json() == {"detail": "Candidate job discovery is unavailable"}
        for forbidden in ("supabase_secret_key", "service_role", "authorization: bearer", "postgrest", "internal.supabase.co", "raw sql"):
            assert forbidden not in response.text.lower()
