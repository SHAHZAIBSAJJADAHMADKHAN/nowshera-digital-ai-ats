from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_applications import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.candidate_applications import CandidateApplicationResponse
from app.services.candidate_applications import (
    CandidateApplicationConflictError,
    CandidateApplicationCVError,
    CandidateApplicationOperationError,
    CandidateApplicationUnavailableError,
)


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ID = "99999999-9999-9999-9999-999999999999"
JOB_ID = UUID("22222222-2222-2222-2222-222222222222")
CV_ID = UUID("33333333-3333-3333-3333-333333333333")
APPLICATION_ID = UUID("44444444-4444-4444-4444-444444444444")


def application() -> CandidateApplicationResponse:
    return CandidateApplicationResponse(
        id=APPLICATION_ID, job_id=JOB_ID, cv_id=CV_ID, stage="applied",
        applied_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class FakeApplicationService:
    def __init__(self) -> None:
        self.result = application()
        self.error: Exception | None = None
        self.calls: list[tuple[str, UUID, UUID]] = []

    def submit_application(self, candidate_id: str, job_id: UUID, cv_id: UUID) -> CandidateApplicationResponse:
        self.calls.append((candidate_id, job_id, cv_id))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client_factory():
    def create(role: str = "candidate", service: FakeApplicationService | None = None) -> tuple[TestClient, FakeApplicationService]:
        fake_service = service or FakeApplicationService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "candidate@example.com")
        app.dependency_overrides[get_service] = lambda: fake_service
        return TestClient(app), fake_service

    yield create
    app.dependency_overrides.clear()


def test_submission_requires_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).post(f"/api/v1/candidate/jobs/{JOB_ID}/applications", json={"cv_id": str(CV_ID)})
    app.dependency_overrides.clear()
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_non_candidates_cannot_submit(client_factory, role: str) -> None:
    client, service = client_factory(role)
    assert client.post(f"/api/v1/candidate/jobs/{JOB_ID}/applications", json={"cv_id": str(CV_ID)}).status_code == 403
    assert service.calls == []


def test_candidate_submits_exact_cv_with_authenticated_actor_and_safe_response(client_factory) -> None:
    client, service = client_factory()
    response = client.post(f"/api/v1/candidate/jobs/{JOB_ID}/applications?candidate_id={OTHER_ID}", json={"cv_id": str(CV_ID)})
    assert response.status_code == 201
    assert response.json() == {"id": str(APPLICATION_ID), "job_id": str(JOB_ID), "cv_id": str(CV_ID), "stage": "applied", "applied_at": "2026-01-01T00:00:00Z"}
    assert service.calls == [(ACTOR_ID, JOB_ID, CV_ID)]


@pytest.mark.parametrize("body", [
    {"cv_id": str(CV_ID), "candidate_id": OTHER_ID},
    {"cv_id": str(CV_ID), "stage": "hired"},
    {"cv_id": str(CV_ID), "status": "open"},
    {"cv_id": str(CV_ID), "created_at": "2026-01-01T00:00:00Z"},
    {"cv_id": str(CV_ID), "notes": "internal"},
    {},
    {"cv_id": "not-a-uuid"},
])
def test_submission_rejects_spoofed_or_invalid_body_fields(client_factory, body: dict[str, object]) -> None:
    client, service = client_factory()
    assert client.post(f"/api/v1/candidate/jobs/{JOB_ID}/applications", json=body).status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (CandidateApplicationConflictError("duplicate"), 409, "You already have an active application for this job."),
        (CandidateApplicationUnavailableError("expired/draft/closed/full"), 409, "This job is not available for applications."),
        (CandidateApplicationCVError("foreign-or-unknown"), 404, "Selected CV is not available."),
    ],
)
def test_known_business_failures_have_stable_safe_responses(client_factory, error: Exception, status_code: int, detail: str) -> None:
    service = FakeApplicationService()
    service.error = error
    client, _ = client_factory(service=service)
    response = client.post(f"/api/v1/candidate/jobs/{JOB_ID}/applications", json={"cv_id": str(CV_ID)})
    assert response.status_code == status_code and response.json() == {"detail": detail}
    assert "foreign-or-unknown" not in response.text and "expired/draft/closed/full" not in response.text


def test_integration_failures_are_normalized_without_leaking_internals(client_factory) -> None:
    service = FakeApplicationService()
    service.error = CandidateApplicationOperationError("SUPABASE_SECRET_KEY service_role Authorization: Bearer PostgREST raw SQL https://internal")
    client, _ = client_factory(service=service)
    response = client.post(f"/api/v1/candidate/jobs/{JOB_ID}/applications", json={"cv_id": str(CV_ID)})
    assert response.status_code == 503 and response.json() == {"detail": "Candidate application service is unavailable"}
    for forbidden in ("supabase_secret_key", "service_role", "authorization: bearer", "postgrest", "raw sql", "internal"):
        assert forbidden not in response.text.lower()
