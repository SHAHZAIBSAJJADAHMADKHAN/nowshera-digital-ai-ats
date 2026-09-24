from dataclasses import dataclass
from typing import Literal

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings

AppRole = Literal["candidate", "recruiter", "admin"]


@dataclass(frozen=True)
class AuthorizationProfile:
    user_id: str
    role: AppRole
    is_active: bool


class ProfileRepository:
    def __init__(self, url: str, secret_key: str) -> None:
        self.url, self.secret_key = url.rstrip("/"), secret_key

    def get_by_user_id(self, user_id: str) -> AuthorizationProfile | None:
        response = httpx.get(f"{self.url}/rest/v1/profiles", params={"id": f"eq.{user_id}", "select": "id,role,is_active"}, headers={"apikey": self.secret_key, "Authorization": f"Bearer {self.secret_key}"}, timeout=5)
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        row = rows[0]
        if row.get("role") not in {"candidate", "recruiter", "admin"}:
            return None
        return AuthorizationProfile(row["id"], row["role"], row["is_active"])


def get_profile_repository(settings: Settings = Depends(get_settings)) -> ProfileRepository:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError("Profile authorization is not configured")
    return ProfileRepository(settings.supabase_url, settings.supabase_secret_key)
