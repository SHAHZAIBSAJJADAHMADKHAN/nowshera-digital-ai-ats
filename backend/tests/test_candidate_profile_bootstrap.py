from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_profile import get_service
from app.core.auth import AuthenticatedPrincipal, get_authenticated_principal
from app.main import app
from app.schemas.candidate_profile import CandidateProfileResponse
from app.services.candidate_profile import CandidateProfileBootstrapConflictError, CandidateProfileBootstrapValidationError, CandidateProfileService


ACTOR_ID = "11111111-1111-1111-1111-111111111111"


def profile() -> CandidateProfileResponse:
    return CandidateProfileResponse(
        id=UUID(ACTOR_ID),
        full_name="Candidate One",
        email="candidate@example.com",
        phone=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class Client:
    def __init__(self, role: str | None = None, full_name: str = "Candidate One") -> None:
        self.role = role
        self.full_name = full_name
        self.bootstrap_calls: list[tuple[str, str, str]] = []
        self.auth_calls: list[str] = []

    def get_profile_identity(self, user_id: str):
        return {"id": user_id, "role": self.role} if self.role else None

    def get_auth_user(self, user_id: str):
        self.auth_calls.append(user_id)
        return {"id": user_id, "email": "candidate@example.com", "user_metadata": {"full_name": self.full_name}}

    def bootstrap_candidate_profile(self, candidate_id: str, full_name: str, email: str) -> None:
        self.bootstrap_calls.append((candidate_id, full_name, email))
        self.role = "candidate"

    def get_candidate_profile(self, candidate_id: str):
        assert candidate_id == ACTOR_ID
        return profile().model_dump()


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(ACTOR_ID, "candidate@example.com", "authenticated", {})


def test_new_candidate_bootstrap_creates_one_candidate_profile() -> None:
    client = Client()
    result = CandidateProfileService(client).bootstrap_profile(principal())
    assert result.id == UUID(ACTOR_ID)
    assert client.bootstrap_calls == [(ACTOR_ID, "Candidate One", "candidate@example.com")]


def test_existing_candidate_bootstrap_is_idempotent_without_auth_or_insert() -> None:
    client = Client(role="candidate")
    CandidateProfileService(client).bootstrap_profile(principal())
    assert client.auth_calls == []
    assert client.bootstrap_calls == []


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_existing_non_candidate_is_never_converted(role: str) -> None:
    client = Client(role=role)
    with pytest.raises(CandidateProfileBootstrapConflictError):
        CandidateProfileService(client).bootstrap_profile(principal())
    assert client.auth_calls == []
    assert client.bootstrap_calls == []


def test_invalid_auth_metadata_is_rejected_without_profile_creation() -> None:
    client = Client(full_name="   ")
    with pytest.raises(CandidateProfileBootstrapValidationError):
        CandidateProfileService(client).bootstrap_profile(principal())
    assert client.bootstrap_calls == []


def test_bootstrap_endpoint_derives_identity_from_the_verified_principal() -> None:
    class Service:
        def __init__(self) -> None:
            self.principal = None

        def bootstrap_profile(self, actor):
            self.principal = actor
            return profile()

    service = Service()
    app.dependency_overrides[get_authenticated_principal] = principal
    app.dependency_overrides[get_service] = lambda: service
    try:
        response = TestClient(app).post("/api/v1/candidate/profile/bootstrap", json={"user_id": "other-user", "role": "admin"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert service.principal.user_id == ACTOR_ID


def test_bootstrap_migration_is_service_only_and_does_not_create_auth_insert_trigger() -> None:
    sql = (Path(__file__).parents[2] / "supabase/migrations/20260924210052_bootstrap_candidate_profile.sql").read_text(encoding="utf-8").lower()
    assert "on conflict (id) do nothing" in sql
    assert "grant execute on function public.bootstrap_candidate_profile" in sql
    assert "to service_role" in sql
    assert "create trigger" not in sql
