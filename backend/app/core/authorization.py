from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException

from app.core.auth import AuthenticatedPrincipal, get_authenticated_principal
from app.repositories.profiles import AppRole, ProfileRepository, get_profile_repository


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: AppRole
    is_active: bool
    email: str | None


def get_current_user(principal: AuthenticatedPrincipal = Depends(get_authenticated_principal), repository: ProfileRepository = Depends(get_profile_repository)) -> CurrentUser:
    profile = repository.get_by_user_id(principal.user_id)
    if profile is None or not profile.is_active:
        raise HTTPException(status_code=403, detail="ATS access is not permitted")
    return CurrentUser(principal.user_id, profile.role, profile.is_active, principal.email)


def _require(role: AppRole):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role != role:
            raise HTTPException(status_code=403, detail="Required ATS role is not permitted")
        return user
    return dependency


require_candidate = _require("candidate")
require_recruiter = _require("recruiter")
require_admin = _require("admin")
