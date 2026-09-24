from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ec import (
    SECP256R1,
    generate_private_key,
)
from fastapi.testclient import TestClient
from jwt import PyJWKSet

from app.core.auth import JWTVerifier, get_jwt_verifier
from app.repositories.profiles import (
    AuthorizationProfile,
    get_profile_repository,
)
from app.main import app


ISSUER = "https://auth.test/auth/v1"
KID = "test-key"


@pytest.fixture
def verifier() -> tuple[JWTVerifier, object]:
    private_key = generate_private_key(SECP256R1())

    public_jwk = jwt.algorithms.ECAlgorithm.to_jwk(
        private_key.public_key(),
        as_dict=True,
    )

    public_jwk.update(
        {
            "kid": KID,
            "alg": "ES256",
            "use": "sig",
        }
    )

    result = JWTVerifier(
        ISSUER,
        "https://unused.test/jwks",
    )

    result._jwks = PyJWKSet.from_dict(
        {
            "keys": [public_jwk],
        }
    )

    result._cached_at = float("inf")

    return result, private_key


@pytest.fixture
def client(
    verifier: tuple[JWTVerifier, object],
) -> TestClient:
    app.dependency_overrides[get_jwt_verifier] = lambda: verifier[0]

    app.dependency_overrides[get_profile_repository] = lambda: type(
        "Repo",
        (),
        {
            "get_by_user_id": lambda _, user_id: AuthorizationProfile(
                user_id,
                "candidate",
                True,
            )
        },
    )()

    yield TestClient(app)

    app.dependency_overrides.clear()


def token(
    key: object,
    **overrides: object,
) -> str:
    claims = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "fake@example.invalid",
        "role": "authenticated",
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }

    claims.update(overrides)

    return jwt.encode(
        claims,
        key,
        algorithm="ES256",
        headers={"kid": KID},
    )


def call(
    client: TestClient,
    value: str | None,
) -> object:
    return client.get(
        "/api/v1/auth/me",
        headers={} if value is None else {"Authorization": value},
    )


def test_auth_rejects_missing_wrong_scheme_and_malformed(
    client: TestClient,
) -> None:
    for value in (
        None,
        "Basic abc",
        "Bearer not-a-jwt",
    ):
        assert call(client, value).status_code == 401


def test_auth_accepts_valid_token_and_returns_safe_identity(
    client: TestClient,
    verifier: tuple[JWTVerifier, object],
) -> None:
    response = call(
        client,
        f"Bearer {token(verifier[1])}",
    )

    assert response.status_code == 200

    assert response.json() == {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "email": "fake@example.invalid",
        "role": "candidate",
        "is_active": True,
    }

    assert "token" not in response.text.lower()


@pytest.mark.parametrize(
    "claims",
    [
        {
            "exp": datetime.now(timezone.utc)
            - timedelta(minutes=1)
        },
        {
            "iss": "https://wrong.test/auth/v1"
        },
        {
            "sub": ""
        },
    ],
)
def test_auth_rejects_invalid_claims(
    client: TestClient,
    verifier: tuple[JWTVerifier, object],
    claims: dict[str, object],
) -> None:
    assert (
        call(
            client,
            f"Bearer {token(verifier[1], **claims)}",
        ).status_code
        == 401
    )


def test_auth_rejects_wrong_signing_key(
    client: TestClient,
) -> None:
    assert (
        call(
            client,
            f"Bearer {token(generate_private_key(SECP256R1()))}",
        ).status_code
        == 401
    )