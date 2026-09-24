from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin_jobs import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.admin_jobs import JobResponse
from app.services.admin_jobs import (
    AdminJobConflictError,
    AdminJobNotFoundError,
    AdminJobOperationError,
)


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
JOB_ID = UUID("22222222-2222-2222-2222-222222222222")


def job(status: str = "draft") -> JobResponse:
    return JobResponse(
        id=JOB_ID,
        title="Backend Engineer",
        department="Engineering",
        location="Nowshera",
        job_type="full-time",
        description="Build reliable services.",
        requirements="Python experience.",
        application_deadline=datetime(2027, 1, 1, tzinfo=timezone.utc),
        openings=2,
        status=status,
        created_by=UUID(ACTOR_ID),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        closed_at=None if status != "closed" else datetime(2026, 2, 1, tzinfo=timezone.utc),
    )


class FakeJobService:
    def __init__(self) -> None:
        self.list_result = [job("draft"), job("open"), job("closed")]
        self.get_result = job()
        self.errors: dict[str, Exception] = {}
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _result(self, name: str, value: object) -> object:
        if name in self.errors:
            raise self.errors[name]
        return value

    def list_jobs(self) -> list[JobResponse]:
        self.calls.append(("list_jobs", ()))
        return self._result("list_jobs", self.list_result)  # type: ignore[return-value]

    def get_job(self, job_id: UUID) -> JobResponse:
        self.calls.append(("get_job", (job_id,)))
        return self._result("get_job", self.get_result)  # type: ignore[return-value]

    def create_job(self, actor_id: str, data: object) -> JobResponse:
        self.calls.append(("create_job", (actor_id, data)))
        return self._result("create_job", job())  # type: ignore[return-value]

    def update_job(self, actor_id: str, job_id: UUID, data: object) -> JobResponse:
        self.calls.append(("update_job", (actor_id, job_id, data)))
        return self._result("update_job", job())  # type: ignore[return-value]

    def open_job(self, actor_id: str, job_id: UUID) -> JobResponse:
        self.calls.append(("open_job", (actor_id, job_id)))
        return self._result("open_job", job("open"))  # type: ignore[return-value]

    def close_job(self, actor_id: str, job_id: UUID) -> JobResponse:
        self.calls.append(("close_job", (actor_id, job_id)))
        return self._result("close_job", job("closed"))  # type: ignore[return-value]


@pytest.fixture
def client_factory():
    def create(role: str = "admin", service: FakeJobService | None = None) -> tuple[TestClient, FakeJobService]:
        fake_service = service or FakeJobService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "admin@example.invalid")
        app.dependency_overrides[get_service] = lambda: fake_service
        return TestClient(app), fake_service

    yield create
    app.dependency_overrides.clear()


def valid_payload() -> dict[str, object]:
    return {
        "title": "Backend Engineer",
        "department": "Engineering",
        "location": "Nowshera",
        "job_type": "full-time",
        "description": "Build reliable services.",
        "requirements": "Python experience.",
        "application_deadline": "2027-01-01T00:00:00+00:00",
        "openings": 2,
    }


def test_admin_job_list_requires_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).get("/api/v1/admin/jobs")
    app.dependency_overrides.clear()
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["candidate", "recruiter"])
def test_non_admin_roles_cannot_list_or_create_jobs(client_factory, role: str) -> None:
    client, _ = client_factory(role)
    assert client.get("/api/v1/admin/jobs").status_code == 403
    assert client.post("/api/v1/admin/jobs", json=valid_payload()).status_code == 403


def test_admin_can_list_draft_open_and_closed_jobs(client_factory) -> None:
    client, service = client_factory()
    response = client.get("/api/v1/admin/jobs")
    assert response.status_code == 200
    assert [item["status"] for item in response.json()] == ["draft", "open", "closed"]
    assert service.calls == [("list_jobs", ())]


def test_get_job_returns_safe_response_and_not_found_is_normalized(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/admin/jobs/{JOB_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == str(JOB_ID)

    service.errors["get_job"] = AdminJobNotFoundError("select * from jobs")
    response = client.get(f"/api/v1/admin/jobs/{JOB_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
    assert "select" not in response.text.lower()


def test_create_uses_authenticated_actor_and_rejects_privileged_fields(client_factory) -> None:
    client, service = client_factory()
    response = client.post("/api/v1/admin/jobs", json=valid_payload())
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert service.calls[0][1][0] == ACTOR_ID

    spoofed = valid_payload() | {"admin_id": "other-user", "created_by": "other-user", "status": "open", "closed_at": "2027-01-02T00:00:00+00:00"}
    response = client.post("/api/v1/admin/jobs", json=spoofed)
    assert response.status_code == 422
    assert len(service.calls) == 1


@pytest.mark.parametrize("change", [
    {"openings": 0},
    {"openings": -1},
    {"job_type": "contract"},
    {"title": "   "},
    {"application_deadline": "2027-01-01T00:00:00"},
    {"openings": None},
])
def test_create_rejects_invalid_business_input(client_factory, change: dict[str, object]) -> None:
    client, service = client_factory()
    response = client.post("/api/v1/admin/jobs", json=valid_payload() | change)
    assert response.status_code == 422
    assert not service.calls


def test_create_rejects_missing_required_field(client_factory) -> None:
    client, service = client_factory()
    payload = valid_payload()
    del payload["department"]
    assert client.post("/api/v1/admin/jobs", json=payload).status_code == 422
    assert not service.calls


def test_update_keeps_partial_update_semantics_and_maps_errors(client_factory) -> None:
    client, service = client_factory()
    response = client.patch(f"/api/v1/admin/jobs/{JOB_ID}", json={"title": "Updated title"})
    assert response.status_code == 200
    actor_id, called_job_id, update = service.calls[0][1]
    assert actor_id == ACTOR_ID and called_job_id == JOB_ID
    assert update.model_fields_set == {"title"}

    response = client.patch(f"/api/v1/admin/jobs/{JOB_ID}", json={"status": "open", "created_by": "other", "closed_at": "2027-01-01T00:00:00+00:00"})
    assert response.status_code == 422

    service.errors["update_job"] = AdminJobConflictError("only draft jobs can be edited")
    assert client.patch(f"/api/v1/admin/jobs/{JOB_ID}", json={"title": "Another"}).status_code == 409
    service.errors["update_job"] = AdminJobNotFoundError("job missing")
    assert client.patch(f"/api/v1/admin/jobs/{JOB_ID}", json={"title": "Another"}).status_code == 404


@pytest.mark.parametrize("message", ["expired draft", "already open", "closed job"])
def test_open_conflicts_map_to_409(client_factory, message: str) -> None:
    service = FakeJobService()
    service.errors["open_job"] = AdminJobConflictError(message)
    client, _ = client_factory(service=service)
    assert client.post(f"/api/v1/admin/jobs/{JOB_ID}/open").status_code == 409


def test_open_uses_authenticated_actor_and_maps_not_found(client_factory) -> None:
    client, service = client_factory()
    assert client.post(f"/api/v1/admin/jobs/{JOB_ID}/open").status_code == 200
    assert service.calls[0] == ("open_job", (ACTOR_ID, JOB_ID))
    service.errors["open_job"] = AdminJobNotFoundError("missing")
    assert client.post(f"/api/v1/admin/jobs/{JOB_ID}/open").status_code == 404


def test_close_is_idempotent_at_api_boundary_and_uses_authenticated_actor(client_factory) -> None:
    client, service = client_factory()
    first = client.post(f"/api/v1/admin/jobs/{JOB_ID}/close")
    second = client.post(f"/api/v1/admin/jobs/{JOB_ID}/close")
    assert first.status_code == second.status_code == 200
    assert service.calls == [("close_job", (ACTOR_ID, JOB_ID)), ("close_job", (ACTOR_ID, JOB_ID))]
    service.errors["close_job"] = AdminJobNotFoundError("missing")
    assert client.post(f"/api/v1/admin/jobs/{JOB_ID}/close").status_code == 404


def test_service_unavailability_is_safe_and_does_not_leak_internals(client_factory) -> None:
    service = FakeJobService()
    service.errors["list_jobs"] = AdminJobOperationError("PostgREST service_role SUPABASE_SECRET_KEY Authorization: Bearer raw SQL")
    client, _ = client_factory(service=service)
    response = client.get("/api/v1/admin/jobs")
    assert response.status_code == 503
    assert response.json() == {"detail": "Job service is unavailable"}
    for secret_marker in ("service_role", "supabase_secret_key", "authorization: bearer", "raw sql", "postgrest"):
        assert secret_marker not in response.text.lower()
