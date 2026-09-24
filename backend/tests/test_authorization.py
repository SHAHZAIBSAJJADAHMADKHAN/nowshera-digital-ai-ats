import pytest
from fastapi import HTTPException

from app.core.auth import AuthenticatedPrincipal
from app.core.authorization import CurrentUser, get_current_user, require_admin, require_candidate, require_recruiter
from app.repositories.profiles import AuthorizationProfile


class Repository:
    def __init__(self, profile: AuthorizationProfile | None) -> None:
        self.profile = profile

    def get_by_user_id(self, _: str) -> AuthorizationProfile | None:
        return self.profile


def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal("verified-id", "safe@example.invalid", "admin", {})


@pytest.mark.parametrize("role", ["candidate", "recruiter", "admin"])
def test_current_user_uses_database_role_not_jwt(role: str) -> None:
    user = get_current_user(principal(), Repository(AuthorizationProfile("verified-id", role, True)))
    assert user.user_id == "verified-id"
    assert user.role == role


@pytest.mark.parametrize("profile", [None, AuthorizationProfile("verified-id", "candidate", False), AuthorizationProfile("verified-id", "recruiter", False), AuthorizationProfile("verified-id", "admin", False)])
def test_missing_or_inactive_profile_is_forbidden(profile: AuthorizationProfile | None) -> None:
    with pytest.raises(HTTPException) as error:
        get_current_user(principal(), Repository(profile))
    assert error.value.status_code == 403


@pytest.mark.parametrize(("dependency", "role", "allowed"), [(require_candidate, "candidate", True), (require_candidate, "recruiter", False), (require_candidate, "admin", False), (require_recruiter, "candidate", False), (require_recruiter, "recruiter", True), (require_recruiter, "admin", False), (require_admin, "candidate", False), (require_admin, "recruiter", False), (require_admin, "admin", True)])
def test_exact_role_dependencies(dependency: object, role: str, allowed: bool) -> None:
    user = CurrentUser("verified-id", role, True, None)
    if allowed:
        assert dependency(user) == user
    else:
        with pytest.raises(HTTPException) as error:
            dependency(user)
        assert error.value.status_code == 403
