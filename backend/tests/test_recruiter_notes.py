from datetime import datetime, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.recruiter_notes import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.recruiter_notes import RecruiterNoteResponse
from app.services.recruiter_notes import RecruiterNotesNotFoundError, RecruiterNotesOperationError


RECRUITER_ID = "11111111-1111-1111-1111-111111111111"
APPLICATION_ID = UUID("22222222-2222-2222-2222-222222222222")
NOTE_ID = UUID("33333333-3333-3333-3333-333333333333")


class FakeNotesService:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.error: Exception | None = None

    def list_notes(self, recruiter_id: str, application_id: UUID) -> list[RecruiterNoteResponse]:
        self.calls.append(("list", recruiter_id, application_id))
        if self.error:
            raise self.error
        return [
            RecruiterNoteResponse(id=NOTE_ID, content="First", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            RecruiterNoteResponse(id=UUID("44444444-4444-4444-4444-444444444444"), content="Second", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        ]

    def create_note(self, recruiter_id: str, application_id: UUID, content: str) -> RecruiterNoteResponse:
        self.calls.append(("create", recruiter_id, application_id, content))
        if self.error:
            raise self.error
        return RecruiterNoteResponse(id=NOTE_ID, content=content, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def client(role: str = "recruiter", service: FakeNotesService | None = None) -> tuple[TestClient, FakeNotesService]:
    fake = service or FakeNotesService()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(RECRUITER_ID, role, True, f"{role}@example.invalid")
    app.dependency_overrides[get_service] = lambda: fake
    return TestClient(app), fake


def test_unauthenticated_recruiter_notes_is_rejected() -> None:
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    response = TestClient(app).get(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["candidate", "admin"])
def test_non_recruiters_cannot_use_notes_routes(role: str) -> None:
    http, _ = client(role)
    assert http.get(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes").status_code == 403
    assert http.post(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes", json={"content": "x"}).status_code == 403


def test_assigned_recruiter_reads_deterministic_safe_notes() -> None:
    http, fake = client()
    response = http.get(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes?recruiter_id=spoofed")
    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["First", "Second"]
    assert set(response.json()[0]) == {"id", "content", "created_at"}
    assert fake.calls == [("list", RECRUITER_ID, APPLICATION_ID)]


@pytest.mark.parametrize("error", [RecruiterNotesNotFoundError(), RecruiterNotesNotFoundError()])
def test_unknown_or_unassigned_application_is_privacy_safe_404(error: Exception) -> None:
    service = FakeNotesService()
    service.error = error
    http, _ = client(service=service)
    response = http.get(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes")
    assert response.status_code == 404 and response.json()["detail"] == "Resource not found"


def test_assigned_recruiter_creates_note_with_current_user_as_author() -> None:
    http, fake = client()
    response = http.post(
        f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes?recruiter_id=spoofed",
        json={"content": "Strong backend experience."},
    )
    assert response.status_code == 201
    assert fake.calls == [("create", RECRUITER_ID, APPLICATION_ID, "Strong backend experience.")]
    assert set(response.json()) == {"id", "content", "created_at"}


@pytest.mark.parametrize("payload", [
    {"content": ""},
    {"content": "   \t"},
    {"content": "x" * 5001},
    {"content": "valid", "recruiter_id": "spoofed"},
])
def test_invalid_or_spoofed_note_payload_is_rejected(payload: dict[str, str]) -> None:
    http, fake = client()
    response = http.post(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes", json=payload)
    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_malformed_application_id_is_422(method: str) -> None:
    http, _ = client()
    if method == "post":
        response = http.post("/api/v1/recruiter/applications/not-a-uuid/notes", json={"content": "x"})
    else:
        response = http.get("/api/v1/recruiter/applications/not-a-uuid/notes")
    assert response.status_code == 422


@pytest.mark.parametrize("error", [RecruiterNotesNotFoundError(), RecruiterNotesOperationError()])
def test_create_errors_are_safe_and_do_not_leak_integration_details(error: Exception) -> None:
    service = FakeNotesService()
    service.error = error
    http, _ = client(service=service)
    response = http.post(f"/api/v1/recruiter/applications/{APPLICATION_ID}/notes", json={"content": "x"})
    expected = 404 if isinstance(error, RecruiterNotesNotFoundError) else 503
    assert response.status_code == expected
    assert "integration" not in response.text.lower()
