import hmac

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


def require_internal_automation(
    settings: Settings = Depends(get_settings),
    automation_key: str | None = Header(default=None, alias="X-Internal-Automation-Key"),
) -> None:
    """Authorize only the configured server-to-server automation caller."""
    if (
        not settings.internal_automation_key
        or not automation_key
        or not hmac.compare_digest(automation_key, settings.internal_automation_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Internal automation authentication is required",
        )
