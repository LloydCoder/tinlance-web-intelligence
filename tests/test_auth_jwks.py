from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from tinlance_web_intelligence.auth.jwks import PlatformTokenVerifier


class FakeJwksClient:
    def __init__(self, key: Any) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        del token
        return SimpleNamespace(key=self.key)


def make_verifier() -> tuple[PlatformTokenVerifier, Any, Any]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = PlatformTokenVerifier(
        issuer="https://identity.example.com",
        audience="urn:tinlance:twi-api",
        jwks_url="https://identity.example.com/.well-known/jwks.json",
    )
    verifier._keys = cast(Any, FakeJwksClient(private_key.public_key()))
    return verifier, private_key, jwt


def token_for(private_key: Any, **overrides: Any) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": "https://identity.example.com",
        "aud": "urn:tinlance:twi-api",
        "sub": "subject-1",
        "jti": "token-1",
        "client_id": "platform-mcp-gateway",
        "principal_type": "user",
        "tenant_id": "tenant-1",
        "scope": "twi:search twi:jobs:read",
        "roles": ["member"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"typ": "at+jwt", "kid": "test-key"},
    )


def test_platform_token_verification_returns_scoped_principal() -> None:
    verifier, private_key, _ = make_verifier()
    principal = verifier.verify(token_for(private_key))
    assert principal.tenant_id == "tenant-1"
    assert principal.subject_id == "subject-1"
    assert principal.client_id == "platform-mcp-gateway"
    assert principal.scopes == frozenset({"twi:search", "twi:jobs:read"})


def test_token_with_wrong_audience_is_rejected() -> None:
    verifier, private_key, _ = make_verifier()
    with pytest.raises(PermissionError):
        verifier.verify(token_for(private_key, aud="urn:other-service"))


def test_contradictory_tenant_claims_are_rejected() -> None:
    verifier, private_key, _ = make_verifier()
    with pytest.raises(PermissionError):
        verifier.verify(token_for(private_key, tid="tenant-2"))


def test_non_access_token_typ_is_rejected() -> None:
    verifier, private_key, _ = make_verifier()
    token = jwt.encode(
        {
            "iss": "https://identity.example.com",
            "aud": "urn:tinlance:twi-api",
            "sub": "subject-1",
            "jti": "token-1",
            "client_id": "platform-mcp-gateway",
            "principal_type": "user",
            "tenant_id": "tenant-1",
            "scope": "twi:search",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"typ": "JWT", "kid": "test-key"},
    )
    with pytest.raises(PermissionError):
        verifier.verify(token)


def test_identity_endpoints_must_be_https() -> None:
    with pytest.raises(ValueError):
        PlatformTokenVerifier(
            issuer="http://identity.example.com",
            audience="urn:tinlance:twi-api",
            jwks_url="https://identity.example.com/jwks.json",
        )
