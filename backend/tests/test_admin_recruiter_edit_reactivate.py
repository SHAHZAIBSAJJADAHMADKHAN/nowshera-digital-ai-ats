from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin_recruiters import get_service
from app.core.auth import get_jwt_verifier
from app.core.authorization import CurrentUser, get_current_user
from app.main import app
from app.schemas.admin_recruiters import RecruiterUpdate
from app.services.admin_recruiters import AdminRecruiterService


ADMIN_ID = "11111111-1111-1111-1111-111111111111"
RECRUITER_ID = "22222222-2222-2222-2222-222222222222"


class Client:
    def __init__(self, role: str = "recruiter", active: bool = False) -> None:
        self.recruiter = {
            "id": RECRUITER_ID,
            "full_name": "Recruiter One",
            "email": "recruiter@example.com",
            "phone": "+923001234567",
            "role": role,
            "is_active": active,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.assignment_snapshot = ["existing-job-assignment"]
        self.history_snapshot = ["existing-stage-history"]
        self.notes_snapshot = ["existing-private-note"]

    def get_recruiter(self, recruiter_id: str):
        self.calls.append(("get", (recruiter_id,)))
        if recruiter_id == "missing":
            raise LookupError("missing")
        return self.recruiter.copy()

    def update_recruiter(self, admin_id: str, recruiter_id: str, full_name: str, phone: str | None) -> None:
        self.calls.append(("update", (admin_id, recruiter_id, full_name, phone)))
        self.recruiter.update(full_name=full_name, phone=phone)

    def reactivate(self, admin_id: str, recruiter_id: str) -> bool:
        self.calls.append(("reactivate", (admin_id, recruiter_id)))
        changed = not self.recruiter["is_active"]
        self.recruiter["is_active"] = True
        return changed


def test_admin_updates_only_recruiter_name_and_phone() -> None:
    client = Client()
    result = AdminRecruiterService(client).update(ADMIN_ID, RECRUITER_ID, RecruiterUpdate(full_name="  Updated Recruiter  ", phone=None))
    assert result["full_name"] == "Updated Recruiter"
    assert result["phone"] is None
    assert client.calls[1] == ("update", (ADMIN_ID, RECRUITER_ID, "Updated Recruiter", None))


@pytest.mark.parametrize("payload", [
    {"email": "other@example.invalid"}, {"role": "admin"}, {"is_active": True},
    {"id": ADMIN_ID}, {"created_at": "2026-02-01T00:00:00Z"}, {"updated_at": "2026-02-01T00:00:00Z"},
    {"assignments": []}, {},
])
def test_recruiter_edit_schema_rejects_protected_or_empty_fields(payload: dict[str, object]) -> None:
    with pytest.raises(Exception):
        RecruiterUpdate.model_validate(payload)


def test_reactivate_preserves_existing_identity_and_relationships() -> None:
    client = Client(active=False)
    before = (client.recruiter["id"], client.assignment_snapshot[:], client.history_snapshot[:], client.notes_snapshot[:])
    result = AdminRecruiterService(client).reactivate(ADMIN_ID, RECRUITER_ID)
    assert result["changed"] is True
    assert result["recruiter"]["id"] == before[0]
    assert client.assignment_snapshot == before[1]
    assert client.history_snapshot == before[2]
    assert client.notes_snapshot == before[3]
    assert [name for name, _ in client.calls] == ["get", "reactivate", "get"]


def test_reactivate_active_recruiter_is_safe_and_idempotent() -> None:
    client = Client(active=True)
    result = AdminRecruiterService(client).reactivate(ADMIN_ID, RECRUITER_ID)
    assert result["changed"] is False
    assert result["recruiter"]["is_active"] is True


@pytest.mark.parametrize("role", ["candidate", "recruiter"])
@pytest.mark.parametrize(("method", "path", "body"), [
    ("PATCH", f"/api/v1/admin/recruiters/{RECRUITER_ID}", {"full_name": "Updated"}),
    ("POST", f"/api/v1/admin/recruiters/{RECRUITER_ID}/reactivate", None),
])
def test_non_admin_roles_cannot_edit_or_reactivate(role: str, method: str, path: str, body: dict[str, object] | None) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN_ID, role, True, "actor@example.invalid")
    try:
        response = TestClient(app).request(method, path, json=body)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path", "body"), [
    ("PATCH", f"/api/v1/admin/recruiters/{RECRUITER_ID}", {"full_name": "Updated"}),
    ("POST", f"/api/v1/admin/recruiters/{RECRUITER_ID}/reactivate", None),
])
def test_admin_recruiter_mutations_require_authentication(method: str, path: str, body: dict[str, object] | None) -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_jwt_verifier] = lambda: object()
    try:
        response = TestClient(app).request(method, path, json=body)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_admin_endpoints_use_authenticated_admin_and_return_safe_recruiter_data() -> None:
    client = Client()
    service = AdminRecruiterService(client)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN_ID, "admin", True, "admin@example.invalid")
    app.dependency_overrides[get_service] = lambda: service
    try:
        response = TestClient(app).patch(f"/api/v1/admin/recruiters/{RECRUITER_ID}?admin_id=other", json={"full_name": "Updated"})
        assert response.status_code == 200
        assert response.json()["id"] == RECRUITER_ID
        assert client.calls[1][1][0] == ADMIN_ID
        response = TestClient(app).post(f"/api/v1/admin/recruiters/{RECRUITER_ID}/reactivate?admin_id=other")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["recruiter"]["id"] == RECRUITER_ID


@pytest.mark.parametrize("role", ["candidate", "admin"])
def test_unknown_or_non_recruiter_targets_are_not_mutated(role: str) -> None:
    client = Client(role=role)
    service = AdminRecruiterService(client)
    with pytest.raises(Exception) as error:
        service.update(ADMIN_ID, RECRUITER_ID, RecruiterUpdate(full_name="Updated"))
    assert getattr(error.value, "status_code", None) == 404
    assert not any(name == "update" for name, _ in client.calls)


def test_reactivation_migration_preserves_identity_and_relationships() -> None:
    sql = (Path(__file__).parents[2] / "supabase/migrations/20260925120000_admin_recruiter_edit_and_reactivate.sql").read_text(encoding="utf-8").lower()
    assert "create or replace function public.reactivate_recruiter" in sql
    assert "set is_active = true" in sql
    assert "for update" in sql
    assert "recruiter_reactivated" in sql
    assert "insert into public.profiles" not in sql
    assert "auth.users" not in sql
    assert "job_recruiters" not in sql
    assert "grant execute on function public.reactivate_recruiter(uuid, uuid) to service_role" in sql
    assert "revoke all on function public.reactivate_recruiter(uuid, uuid) from public, anon, authenticated" in sql


def test_recruiter_update_migration_changes_only_safe_fields_and_is_service_only() -> None:
    sql = (Path(__file__).parents[2] / "supabase/migrations/20260925120000_admin_recruiter_edit_and_reactivate.sql").read_text(encoding="utf-8").lower()
    assert "set full_name = v_full_name" in sql
    assert "phone = v_phone" in sql
    assert "recruiter_profile_updated" in sql
    assert "grant execute on function public.update_recruiter_profile(uuid, uuid, text, text) to service_role" in sql
    assert "revoke all on function public.update_recruiter_profile(uuid, uuid, text, text) from public, anon, authenticated" in sql
