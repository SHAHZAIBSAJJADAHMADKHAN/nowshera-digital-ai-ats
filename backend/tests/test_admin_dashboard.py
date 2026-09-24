from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin_dashboard import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.admin_dashboard import AdminJobDashboardResponse
from app.services.admin_dashboard import AdminDashboardOperationError, AdminDashboardService


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ADMIN_ID = "99999999-9999-9999-9999-999999999999"
JOB_ID = UUID("22222222-2222-2222-2222-222222222222")


def dashboard_row(**changes: object) -> AdminJobDashboardResponse:
    data: dict[str, object] = {
        "job_id": JOB_ID,
        "title": "Backend Engineer",
        "department": "Engineering",
        "status": "open",
        "application_deadline": datetime(2027, 1, 1, tzinfo=timezone.utc),
        "openings": 2,
        "total_applied": 7,
        "applied_count": 1,
        "shortlisted_count": 1,
        "interview_count": 1,
        "offer_count": 1,
        "hired_count": 1,
        "rejected_count": 1,
        "withdrawn_count": 1,
    }
    return AdminJobDashboardResponse.model_validate(data | changes)


class FakeDashboardService:
    def __init__(self, result: list[AdminJobDashboardResponse] | None = None) -> None:
        self.result = result if result is not None else [dashboard_row()]
        self.error: Exception | None = None
        self.calls: list[str] = []

    def get_job_dashboard(self, admin_id: str) -> list[AdminJobDashboardResponse]:
        self.calls.append(admin_id)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client_factory():
    def create(role: str = "admin", service: FakeDashboardService | None = None) -> tuple[TestClient, FakeDashboardService]:
        fake_service = service or FakeDashboardService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "admin@example.com")
        app.dependency_overrides[get_service] = lambda: fake_service
        return TestClient(app), fake_service

    yield create
    app.dependency_overrides.clear()


def test_dashboard_requires_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).get("/api/v1/admin/dashboard/jobs")
    app.dependency_overrides.clear()
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["candidate", "recruiter"])
def test_dashboard_rejects_non_admin_roles(client_factory, role: str) -> None:
    client, service = client_factory(role)
    assert client.get("/api/v1/admin/dashboard/jobs").status_code == 403
    assert service.calls == []


def test_dashboard_passes_current_user_actor_and_ignores_query_spoofing(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/admin/dashboard/jobs?admin_id={OTHER_ADMIN_ID}")
    assert response.status_code == 200
    assert service.calls == [ACTOR_ID]


def test_dashboard_returns_empty_list(client_factory) -> None:
    client, service = client_factory(service=FakeDashboardService([]))
    response = client.get("/api/v1/admin/dashboard/jobs")
    assert response.status_code == 200
    assert response.json() == []
    assert service.calls == [ACTOR_ID]


def test_dashboard_keeps_zero_application_job_and_integer_counts(client_factory) -> None:
    zero_row = dashboard_row(
        status="draft",
        total_applied=0,
        applied_count=0,
        shortlisted_count=0,
        interview_count=0,
        offer_count=0,
        hired_count=0,
        rejected_count=0,
        withdrawn_count=0,
    )
    client, _ = client_factory(service=FakeDashboardService([zero_row]))
    response = client.get("/api/v1/admin/dashboard/jobs")
    assert response.status_code == 200
    item = response.json()[0]
    counts = [item[name] for name in ("total_applied", "applied_count", "shortlisted_count", "interview_count", "offer_count", "hired_count", "rejected_count", "withdrawn_count")]
    assert counts == [0] * 8
    assert all(type(value) is int for value in counts)


def test_dashboard_serializes_exact_fields_and_current_stage_counts(client_factory) -> None:
    client, _ = client_factory()
    response = client.get("/api/v1/admin/dashboard/jobs")
    assert response.status_code == 200
    item = response.json()[0]
    assert set(item) == {
        "job_id", "title", "department", "status", "application_deadline", "openings",
        "total_applied", "applied_count", "shortlisted_count", "interview_count", "offer_count",
        "hired_count", "rejected_count", "withdrawn_count",
    }
    assert item["total_applied"] == sum(item[name] for name in (
        "applied_count", "shortlisted_count", "interview_count", "offer_count", "hired_count", "rejected_count", "withdrawn_count"
    ))


def test_dashboard_preserves_withdraw_then_reapply_counts(client_factory) -> None:
    reapplication = dashboard_row(
        total_applied=2,
        applied_count=1,
        shortlisted_count=0,
        interview_count=0,
        offer_count=0,
        hired_count=0,
        rejected_count=0,
        withdrawn_count=1,
    )
    client, _ = client_factory(service=FakeDashboardService([reapplication]))
    item = client.get("/api/v1/admin/dashboard/jobs").json()[0]
    assert item["total_applied"] == 2
    assert item["applied_count"] == 1
    assert item["withdrawn_count"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"total_applied": -1, "applied_count": -1},
        {"total_applied": 2, "applied_count": 1, "shortlisted_count": 0, "interview_count": 0, "offer_count": 0, "hired_count": 0, "rejected_count": 0, "withdrawn_count": 0},
        {"total_applied": 1.0, "applied_count": 1.0, "shortlisted_count": 0, "interview_count": 0, "offer_count": 0, "hired_count": 0, "rejected_count": 0, "withdrawn_count": 0},
    ],
)
def test_service_rejects_negative_inconsistent_or_float_trusted_counts(changes: dict[str, object]) -> None:
    raw = dashboard_row().model_dump() | changes

    class Client:
        calls = 0

        def get_admin_job_dashboard(self, admin_id: str) -> list[dict[str, object]]:
            self.calls += 1
            return [raw]

    client = Client()
    with pytest.raises(AdminDashboardOperationError):
        AdminDashboardService(client).get_job_dashboard(ACTOR_ID)
    assert client.calls == 1


def test_dashboard_normalizes_service_error_without_leaking_internals(client_factory) -> None:
    service = FakeDashboardService()
    service.error = AdminDashboardOperationError(
        "SUPABASE_SECRET_KEY service_role Authorization: Bearer raw SQL PostgREST https://internal.example"
    )
    client, _ = client_factory(service=service)
    response = client.get("/api/v1/admin/dashboard/jobs")
    assert response.status_code == 503
    assert response.json() == {"detail": "Dashboard service is unavailable"}
    for marker in ("supabase_secret_key", "service_role", "authorization: bearer", "raw sql", "postgrest", "internal.example"):
        assert marker not in response.text.lower()


def test_service_performs_one_dashboard_rpc_for_one_retrieval() -> None:
    class Client:
        calls = 0

        def get_admin_job_dashboard(self, admin_id: str) -> list[dict[str, object]]:
            self.calls += 1
            return [dashboard_row().model_dump()]

    client = Client()
    result = AdminDashboardService(client).get_job_dashboard(ACTOR_ID)
    assert len(result) == 1
    assert client.calls == 1
