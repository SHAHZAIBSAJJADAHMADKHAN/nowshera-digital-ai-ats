"""Supabase JWT authentication primitives; authorization belongs to later phases."""

from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from typing import Any
from urllib.request import urlopen

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKSet

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)
_allowed_algorithms = {"RS256", "ES256"}


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    email: str | None
    token_role: str | None
    claims: dict[str, Any]


class JWTVerifier:
    def __init__(
        self,
        issuer: str,
        jwks_url: str,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.jwks_url = jwks_url
        self.cache_ttl_seconds = cache_ttl_seconds
        self._jwks: PyJWKSet | None = None
        self._cached_at = 0.0

    def _load_jwks(self) -> PyJWKSet:
        if (
            self._jwks is None
            or monotonic() - self._cached_at >= self.cache_ttl_seconds
        ):
            with urlopen(
                self.jwks_url,
                timeout=5,
            ) as response:  # nosec B310: configured HTTPS JWKS endpoint
                self._jwks = PyJWKSet.from_dict(
                    __import__("json").load(response)
                )
            self._cached_at = monotonic()

        return self._jwks

    def verify(self, token: str) -> AuthenticatedPrincipal:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")

            if algorithm not in _allowed_algorithms or not isinstance(key_id, str):
                raise InvalidTokenError("unsupported token header")

            jwk = next(
                (
                    key
                    for key in self._load_jwks().keys
                    if key.key_id == key_id
                ),
                None,
            )

            if jwk is None:
                # Refresh once for normal signing-key rotation.
                self._jwks = None

                jwk = next(
                    (
                        key
                        for key in self._load_jwks().keys
                        if key.key_id == key_id
                    ),
                    None,
                )

            if jwk is None:
                raise InvalidTokenError("unknown signing key")

            claims = jwt.decode(
                token,
                jwk.key,
                algorithms=[algorithm],
                issuer=self.issuer,
                audience="authenticated",
                options={
                    "require": [
                        "exp",
                        "iss",
                        "sub",
                        "aud",
                    ]
                },
            )

            subject = claims.get("sub")

            if not isinstance(subject, str) or not subject:
                raise InvalidTokenError("missing subject")

            return AuthenticatedPrincipal(
                subject,
                claims.get("email"),
                claims.get("role"),
                claims,
            )

        except (
            InvalidTokenError,
            OSError,
            ValueError,
            StopIteration,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None


@lru_cache
def _cached_verifier(
    issuer: str,
    jwks_url: str,
    cache_ttl_seconds: int,
) -> JWTVerifier:
    return JWTVerifier(
        issuer,
        jwks_url,
        cache_ttl_seconds,
    )


def get_jwt_verifier(
    settings: Settings = Depends(get_settings),
) -> JWTVerifier:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured",
        )

    issuer = (
        settings.supabase_jwt_issuer
        or f"{settings.supabase_url.rstrip('/')}/auth/v1"
    )

    jwks_url = (
        settings.supabase_jwks_url
        or f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    )

    return _cached_verifier(
        issuer,
        jwks_url,
        settings.jwks_cache_ttl_seconds,
    )


def get_authenticated_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    verifier: JWTVerifier = Depends(get_jwt_verifier),
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verifier.verify(credentials.credentials)