from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_cvs import get_service as get_cv_service
from app.api.v1.candidate_profile import get_service as get_profile_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.candidate_cvs import CandidateCVResponse
from app.schemas.candidate_profile import CandidateProfileResponse
from app.services.candidate_profile import CandidateProfileOperationError


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ID = "99999999-9999-9999-9999-999999999999"
CV_ID = UUID("22222222-2222-2222-2222-222222222222")


def profile() -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=UUID(ACTOR_ID),
        full_name="Candidate One",
        email="candidate@example.com",
        phone="+923001234567",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )


def cv() -> CandidateCVResponse:
    return CandidateCVResponse(
        id=CV_ID,
        original_filename="candidate-cv.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        uploaded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class FakeProfileService:
    def __init__(self) -> None:
        self.result = profile()
        self.error: Exception | None = None
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get_profile(self, candidate_id: str) -> CandidateProfileResponse:
        self.calls.append(("get", (candidate_id,)))
        if self.error:
            raise self.error
        return self.result

    def update_profile(self, candidate_id: str, data: object) -> CandidateProfileResponse:
        self.calls.append(("update", (candidate_id, data)))
        if self.error:
            raise self.error
        return self.result


class FakeCVService:
    def __init__(self, result: list[CandidateCVResponse] | None = None) -> None:
        self.result = result if result is not None else [cv()]
        self.error: Exception | None = None
        self.calls: list[str] = []

    def list_cvs(self, candidate_id: str) -> list[CandidateCVResponse]:
        self.calls.append(candidate_id)
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client_factory():
    def create(
        role: str = "candidate",
        profile_service: FakeProfileService | None = None,
        cv_service: FakeCVService | None = None,
    ) -> tuple[TestClient, FakeProfileService, FakeCVService]:
        profiles = profile_service or FakeProfileService()
        cvs = cv_service or FakeCVService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "candidate@example.com")
        app.dependency_overrides[get_profile_service] = lambda: profiles
        app.dependency_overrides[get_cv_service] = lambda: cvs
        return TestClient(app), profiles, cvs

    yield create
    app.dependency_overrides.clear()


def test_candidate_profile_and_cvs_require_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    client = TestClient(app)
    assert client.get("/api/v1/candidate/profile").status_code == 401
    assert client.patch("/api/v1/candidate/profile", json={"full_name": "Name"}).status_code == 401
    assert client.get("/api/v1/candidate/cvs").status_code == 401
    app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_non_candidates_cannot_access_candidate_endpoints(client_factory, role: str) -> None:
    client, profiles, cvs = client_factory(role)
    assert client.get("/api/v1/candidate/profile").status_code == 403
    assert client.patch("/api/v1/candidate/profile", json={"full_name": "Name"}).status_code == 403
    assert client.get("/api/v1/candidate/cvs").status_code == 403
    assert profiles.calls == []
    assert cvs.calls == []


def test_candidate_reads_own_safe_profile_only(client_factory) -> None:
    client, profiles, _ = client_factory()
    response = client.get(f"/api/v1/candidate/profile?candidate_id={OTHER_ID}")
    assert response.status_code == 200
    assert response.json() == {
        "id": ACTOR_ID,
        "full_name": "Candidate One",
        "email": "candidate@example.com",
        "phone": "+923001234567",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
    }
    assert profiles.calls == [("get", (ACTOR_ID,))]


def test_candidate_updates_only_allowed_fields_using_authenticated_actor(client_factory) -> None:
    client, profiles, _ = client_factory()
    response = client.patch(
        f"/api/v1/candidate/profile?candidate_id={OTHER_ID}",
        json={"full_name": "Updated Name", "phone": "+923009999999"},
    )
    assert response.status_code == 200
    name, (actor, update) = profiles.calls[0]
    assert name == "update" and actor == ACTOR_ID
    assert update.model_fields_set == {"full_name", "phone"}


def test_candidate_profile_update_trims_name_and_phone(client_factory) -> None:
    client, profiles, _ = client_factory()
    response = client.patch("/api/v1/candidate/profile", json={"full_name": "  Updated Name  ", "phone": " +923009999999 "})
    assert response.status_code == 200
    _, (_, update) = profiles.calls[0]
    assert update.full_name == "Updated Name"
    assert update.phone == "+923009999999"


@pytest.mark.parametrize(
    "payload",
    [
        {"id": OTHER_ID},
        {"role": "admin"},
        {"is_active": False},
        {"email": "other@example.com"},
        {"candidate_id": OTHER_ID},
        {"created_at": "2027-01-01T00:00:00+00:00"},
        {"full_name": "   "},
        {"phone": "   "},
        {},
    ],
)
def test_candidate_profile_update_rejects_privileged_unknown_or_invalid_fields(client_factory, payload: dict[str, object]) -> None:
    client, profiles, _ = client_factory()
    assert client.patch("/api/v1/candidate/profile", json=payload).status_code == 422
    assert profiles.calls == []


def test_candidate_lists_only_own_safe_cv_metadata_and_preserves_empty_list(client_factory) -> None:
    client, _, cvs = client_factory()
    response = client.get(f"/api/v1/candidate/cvs?candidate_id={OTHER_ID}")
    assert response.status_code == 200
    assert response.json() == [{
        "id": str(CV_ID), "original_filename": "candidate-cv.pdf", "mime_type": "application/pdf",
        "file_size_bytes": 1024, "uploaded_at": "2026-01-01T00:00:00Z",
    }]
    assert cvs.calls == [ACTOR_ID]

    empty_client, _, empty_cvs = client_factory(cv_service=FakeCVService([]))
    empty = empty_client.get("/api/v1/candidate/cvs")
    assert empty.status_code == 200 and empty.json() == []
    assert empty_cvs.calls == [ACTOR_ID]


def test_candidate_services_normalize_failures_without_leaking_internals(client_factory) -> None:
    profile_service, cv_service = FakeProfileService(), FakeCVService()
    profile_service.error = CandidateProfileOperationError("SUPABASE_SECRET_KEY service_role Authorization: Bearer raw SQL")
    cv_service.error = CandidateProfileOperationError("SUPABASE_SECRET_KEY service_role Authorization: Bearer raw SQL")
    client, _, _ = client_factory(profile_service=profile_service, cv_service=cv_service)
    profile_response = client.get("/api/v1/candidate/profile")
    cv_response = client.get("/api/v1/candidate/cvs")
    assert profile_response.status_code == cv_response.status_code == 503
    for response in (profile_response, cv_response):
        assert "supabase_secret_key" not in response.text.lower()
        assert "service_role" not in response.text.lower()
        assert "raw sql" not in response.text.lower()
