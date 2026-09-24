from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.candidate_application_withdrawal import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.integrations.supabase_admin import SupabaseAdminClient
from app.main import app
from app.schemas.candidate_application_withdrawal import CandidateApplicationWithdrawalResponse
from app.services.candidate_application_withdrawal import CandidateWithdrawalConflictError, CandidateWithdrawalNotFoundError, CandidateWithdrawalOperationError


ACTOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_ID = "99999999-9999-9999-9999-999999999999"
APPLICATION_ID = UUID("22222222-2222-2222-2222-222222222222")


def withdrawn() -> CandidateApplicationWithdrawalResponse:
    return CandidateApplicationWithdrawalResponse(id=APPLICATION_ID, stage="withdrawn", withdrawn_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


class FakeWithdrawalService:
    def __init__(self) -> None:
        self.result = withdrawn()
        self.error: Exception | None = None
        self.calls: list[tuple[str, UUID]] = []

    def withdraw_application(self, candidate_id: str, application_id: UUID) -> CandidateApplicationWithdrawalResponse:
        self.calls.append((candidate_id, application_id))
        if self.error: raise self.error
        return self.result


@pytest.fixture
def client_factory():
    def create(role: str = "candidate", service: FakeWithdrawalService | None = None) -> tuple[TestClient, FakeWithdrawalService]:
        fake = service or FakeWithdrawalService()
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(ACTOR_ID, role, True, "candidate@example.com")
        app.dependency_overrides[get_service] = lambda: fake
        return TestClient(app), fake
    yield create
    app.dependency_overrides.clear()


def test_withdrawal_requires_authentication() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw")
    app.dependency_overrides.clear()
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["recruiter", "admin"])
def test_non_candidates_cannot_withdraw(client_factory, role: str) -> None:
    client, service = client_factory(role)
    assert client.post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw").status_code == 403
    assert service.calls == []


def test_candidate_withdraws_with_authenticated_actor_and_safe_response(client_factory) -> None:
    client, service = client_factory()
    response = client.post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw?candidate_id={OTHER_ID}")
    assert response.status_code == 200
    assert response.json() == {"id": str(APPLICATION_ID), "stage": "withdrawn", "withdrawn_at": "2026-01-01T00:00:00Z"}
    assert service.calls == [(ACTOR_ID, APPLICATION_ID)]


@pytest.mark.parametrize("state", ["foreign", "unknown"])
def test_foreign_and_unknown_withdrawal_are_privacy_safe_not_found(client_factory, state: str) -> None:
    service = FakeWithdrawalService(); service.error = CandidateWithdrawalNotFoundError(state)
    client, _ = client_factory(service=service)
    response = client.post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw")
    assert response.status_code == 404 and response.json() == {"detail": "Application not found"}
    assert state not in response.text


@pytest.mark.parametrize("state", ["hired", "rejected", "withdrawn"])
def test_terminal_withdrawal_is_safe_conflict(client_factory, state: str) -> None:
    service = FakeWithdrawalService(); service.error = CandidateWithdrawalConflictError(state)
    client, _ = client_factory(service=service)
    response = client.post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw")
    assert response.status_code == 409 and response.json() == {"detail": "This application cannot be withdrawn."}
    if state != "withdrawn":
        assert state not in response.text


def test_malformed_application_id_is_validation_error(client_factory) -> None:
    client, service = client_factory()
    assert client.post("/api/v1/candidate/applications/not-a-uuid/withdraw").status_code == 422
    assert service.calls == []


def test_integration_failure_is_normalized_without_leakage(client_factory) -> None:
    service = FakeWithdrawalService(); service.error = CandidateWithdrawalOperationError("SUPABASE_SECRET_KEY service_role Authorization: Bearer PostgREST raw SQL https://internal")
    client, _ = client_factory(service=service)
    response = client.post(f"/api/v1/candidate/applications/{APPLICATION_ID}/withdraw")
    assert response.status_code == 503 and response.json() == {"detail": "Candidate application service is unavailable"}
    for marker in ("supabase_secret_key", "service_role", "authorization: bearer", "postgrest", "raw sql", "internal"):
        assert marker not in response.text.lower()


def test_integration_calls_authoritative_rpc_and_returns_minimal_result(monkeypatch) -> None:
    client = SupabaseAdminClient("https://example.supabase.co", "not-a-real-secret")
    called: dict[str, object] = {}
    class PostResponse:
        status_code = 204
        def json(self): return {}
        def raise_for_status(self): pass
    monkeypatch.setattr("app.integrations.supabase_admin.httpx.post", lambda *args, **kwargs: (called.update({"args": args, **kwargs}), PostResponse())[1])
    class GetResponse:
        def json(self): return [{"id": str(APPLICATION_ID), "stage": "withdrawn", "withdrawn_at": "2026-01-01T00:00:00+00:00"}]
    monkeypatch.setattr(client, "_request", lambda *args, **kwargs: GetResponse())
    result = client.withdraw_candidate_application(ACTOR_ID, str(APPLICATION_ID))
    assert called["json"] == {"p_candidate_id": ACTOR_ID, "p_application_id": str(APPLICATION_ID)}
    assert result["stage"] == "withdrawn"
