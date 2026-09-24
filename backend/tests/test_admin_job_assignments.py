from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin_job_assignments import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.admin_job_assignments import AssignedRecruiterResponse, AssignmentResult
from app.services.admin_jobs import AdminJobConflictError, AdminJobNotFoundError, AdminJobOperationError


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
JOB_ID = UUID("22222222-2222-2222-2222-222222222222")
RECRUITER_ID = UUID("33333333-3333-3333-3333-333333333333")


def assigned_recruiter(is_active: bool = True) -> AssignedRecruiterResponse:
    return AssignedRecruiterResponse(
        id=RECRUITER_ID,
        full_name="Recruiter Name",
        email="recruiter@example.com",
        is_active=is_active,
        assigned_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class FakeAssignmentService:
    def __init__(self) -> None:
        self.list_result = [assigned_recruiter(), assigned_recruiter(is_active=False)]
        self.assign_result = AssignmentResult(changed=True)
        self.unassign_result = AssignmentResult(changed=True)
        self.errors: dict[str, Exception] = {}
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def _result(self, name: str, value: object) -> object:
        if name in self.errors:
            raise self.errors[name]
        return value

    def list_assigned_recruiters(self, job_id: UUID) -> list[AssignedRecruiterResponse]:
        self.calls.append(("list", (job_id,)))
        return self._result("list", self.list_result)  # type: ignore[return-value]

    def assign_recruiter(self, actor_id: str, job_id: UUID, recruiter_id: UUID) -> AssignmentResult:
        self.calls.append(("assign", (actor_id, job_id, recruiter_id)))
        return self._result("assign", self.assign_result)  # type: ignore[return-value]

    def unassign_recruiter(self, actor_id: str, job_id: UUID, recruiter_id: UUID) -> AssignmentResult:
        self.calls.append(("unassign", (actor_id, job_id, recruiter_id)))
        return self._result("unassign", self.unassign_result)  # type: ignore[return-value]


@pytest.fixture
def client_factory():
    def create(role: str = "admin", service: FakeAssignmentService | None = None) -> tuple[TestClient, FakeAssignmentService]:
        fake_service = service or FakeAssignmentService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "admin@example.invalid")
        app.dependency_overrides[get_service] = lambda: fake_service
        return TestClient(app), fake_service

    yield create
    app.dependency_overrides.clear()


def assignment_path() -> str:
    return f"/api/v1/admin/jobs/{JOB_ID}/recruiters/{RECRUITER_ID}"


@pytest.mark.parametrize(("method", "path"), [
    ("GET", f"/api/v1/admin/jobs/{JOB_ID}/recruiters"),
    ("POST", assignment_path()),
    ("DELETE", assignment_path()),
])
def test_assignment_routes_require_authentication(method: str, path: str) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).request(method, path)
    app.dependency_overrides.clear()
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["candidate", "recruiter"])
@pytest.mark.parametrize(("method", "path"), [
    ("GET", f"/api/v1/admin/jobs/{JOB_ID}/recruiters"),
    ("POST", assignment_path()),
    ("DELETE", assignment_path()),
])
def test_non_admin_roles_cannot_manage_assignments(client_factory, role: str, method: str, path: str) -> None:
    client, _ = client_factory(role)
    assert client.request(method, path).status_code == 403


def test_admin_lists_safe_assignments_including_inactive_history(client_factory) -> None:
    client, service = client_factory()
    response = client.get(f"/api/v1/admin/jobs/{JOB_ID}/recruiters")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(RECRUITER_ID)
    assert response.json()[1]["is_active"] is False
    assert service.calls == [("list", (JOB_ID,))]


def test_admin_lists_empty_assignments_and_maps_unknown_job(client_factory) -> None:
    client, service = client_factory()
    service.list_result = []
    assert client.get(f"/api/v1/admin/jobs/{JOB_ID}/recruiters").json() == []
    service.errors["list"] = AdminJobNotFoundError("select * from jobs")
    response = client.get(f"/api/v1/admin/jobs/{JOB_ID}/recruiters")
    assert response.status_code == 404
    assert "select" not in response.text.lower()


def test_assignment_uses_authenticated_actor_and_preserves_idempotency(client_factory) -> None:
    client, service = client_factory()
    response = client.post(assignment_path())
    assert response.status_code == 200
    assert response.json() == {"changed": True}
    assert service.calls[0] == ("assign", (ACTOR_ID, JOB_ID, RECRUITER_ID))

    service.assign_result = AssignmentResult(changed=False)
    response = client.post(f"{assignment_path()}?admin_id=other-user&actor_id=other-user")
    assert response.status_code == 200
    assert response.json() == {"changed": False}
    assert service.calls[1] == ("assign", (ACTOR_ID, JOB_ID, RECRUITER_ID))


@pytest.mark.parametrize(("error", "expected_status"), [
    (AdminJobNotFoundError("missing job"), 404),
    (AdminJobNotFoundError("missing recruiter"), 404),
    (AdminJobConflictError("inactive recruiter"), 409),
    (AdminJobConflictError("candidate target"), 409),
    (AdminJobConflictError("admin target"), 409),
    (AdminJobConflictError("closed job"), 409),
])
def test_assignment_maps_normalized_errors(client_factory, error: Exception, expected_status: int) -> None:
    service = FakeAssignmentService()
    service.errors["assign"] = error
    client, _ = client_factory(service=service)
    assert client.post(assignment_path()).status_code == expected_status


def test_unassignment_uses_authenticated_actor_and_preserves_idempotency(client_factory) -> None:
    client, service = client_factory()
    response = client.delete(assignment_path())
    assert response.status_code == 200
    assert response.json() == {"changed": True}
    assert service.calls[0] == ("unassign", (ACTOR_ID, JOB_ID, RECRUITER_ID))

    service.unassign_result = AssignmentResult(changed=False)
    response = client.delete(f"{assignment_path()}?admin_id=other-user")
    assert response.status_code == 200
    assert response.json() == {"changed": False}
    assert service.calls[1] == ("unassign", (ACTOR_ID, JOB_ID, RECRUITER_ID))


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_mutation_maps_unknown_resources(client_factory, method: str) -> None:
    service = FakeAssignmentService()
    service.errors["assign" if method == "POST" else "unassign"] = AdminJobNotFoundError("not found")
    client, _ = client_factory(service=service)
    assert client.request(method, assignment_path()).status_code == 404


@pytest.mark.parametrize(("method", "path"), [
    ("GET", "/api/v1/admin/jobs/not-a-uuid/recruiters"),
    ("POST", f"/api/v1/admin/jobs/{JOB_ID}/recruiters/not-a-uuid"),
])
def test_assignment_paths_validate_uuids(client_factory, method: str, path: str) -> None:
    client, _ = client_factory()
    assert client.request(method, path).status_code == 422


def test_service_unavailability_is_safe_and_does_not_leak_internals(client_factory) -> None:
    service = FakeAssignmentService()
    service.errors["assign"] = AdminJobOperationError("PostgREST service_role SUPABASE_SECRET_KEY Authorization: Bearer raw SQL")
    client, _ = client_factory(service=service)
    response = client.post(assignment_path())
    assert response.status_code == 503
    assert response.json() == {"detail": "Recruiter assignment service is unavailable"}
    for secret_marker in ("service_role", "supabase_secret_key", "authorization: bearer", "raw sql", "postgrest"):
        assert secret_marker not in response.text.lower()
