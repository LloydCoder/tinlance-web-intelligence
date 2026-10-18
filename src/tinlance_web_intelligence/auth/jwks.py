"""Strict resource-server validation for Platform-issued audience-bound access tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import jwt
from jwt import PyJWKClient

from tinlance_web_intelligence.auth.principal import Principal


_ALLOWED_ALGORITHMS = frozenset({"RS256", "PS256", "ES256", "EdDSA"})
_ALLOWED_PRINCIPAL_TYPES = frozenset({"user", "service", "agent", "workload"})


class PlatformTokenVerifier:
    """Verify tokens minted by the Platform issuer; this class does not grant policy."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: tuple[str, ...] = ("RS256", "ES256", "EdDSA"),
        leeway_seconds: int = 60,
        jwks_timeout_seconds: float = 5.0,
    ) -> None:
        for value, label in ((issuer, "issuer"), (jwks_url, "JWKS URL")):
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
            ):
                raise ValueError(
                    f"{label} must be an absolute HTTPS URL without userinfo"
                )
        if not audience or audience != audience.strip():
            raise ValueError("audience is required and must be normalized")
        if not algorithms or len(set(algorithms)) != len(algorithms):
            raise ValueError("JWT algorithms must be non-empty and unique")
        if any(item not in _ALLOWED_ALGORITHMS for item in algorithms):
            raise ValueError("JWT algorithm is not allowed")
        if not 0 <= leeway_seconds <= 300 or jwks_timeout_seconds <= 0:
            raise ValueError("JWT leeway or JWKS timeout is outside the allowed range")
        self._issuer = issuer
        self._audience = audience
        self._algorithms = algorithms
        self._leeway = leeway_seconds
        self._keys = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            lifespan=300,
            timeout=jwks_timeout_seconds,
        )

    def verify(self, token: str) -> Principal:
        if not isinstance(token, str) or not token or any(ch.isspace() for ch in token):
            raise PermissionError("access token is malformed")
        try:
            header = jwt.get_unverified_header(token)
            if not isinstance(header.get("typ"), str) or header["typ"].lower() != "at+jwt":
                raise PermissionError("access token type is not trusted")
            if header.get("alg") not in self._algorithms:
                raise PermissionError("access token algorithm is not trusted")
            if not isinstance(header.get("kid"), str) or not header["kid"].strip():
                raise PermissionError("access token key identifier is required")
            key = self._keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=list(self._algorithms),
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "iss", "sub", "jti", "client_id"]},
            )
        except PermissionError:
            raise
        except Exception as exc:
            raise PermissionError("access token verification failed") from exc
        subject = self._claim_string(claims, "sub")
        client_id = self._claim_string(claims, "client_id")
        token_id = self._claim_string(claims, "jti")
        principal_type = self._claim_string(claims, "principal_type")
        if principal_type not in _ALLOWED_PRINCIPAL_TYPES:
            raise PermissionError("access token principal type is not trusted")
        tenant_values = [claims[name] for name in ("tenant_id", "tid") if name in claims]
        invalid_tenant = any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in tenant_values
        )
        if not tenant_values or invalid_tenant or len(set(tenant_values)) != 1:
            raise PermissionError("access token tenant claim is missing or contradictory")
        scopes = self._claim_set(claims, ("scope", "scp"), required=False)
        roles = self._claim_set(claims, ("roles",), required=False)
        expires = claims.get("exp")
        if not isinstance(expires, (int, float)) or isinstance(expires, bool):
            raise PermissionError("access token expiry is invalid")
        try:
            expires_at = datetime.fromtimestamp(expires, UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise PermissionError("access token expiry is invalid") from exc
        if expires_at <= datetime.now(UTC):
            raise PermissionError("access token has expired")
        return Principal(
            tenant_id=str(tenant_values[0]),
            subject_id=subject,
            client_id=client_id,
            principal_type=principal_type,
            token_id=token_id,
            scopes=frozenset(scopes),
            roles=frozenset(roles),
            expires_at=expires_at,
        )

    @staticmethod
    def _claim_string(claims: dict[str, Any], name: str) -> str:
        value = claims.get(name)
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or any(ord(ch) < 0x21 or ord(ch) == 0x7F for ch in value)
        ):
            raise PermissionError(f"access token claim {name!r} is invalid")
        return value

    @staticmethod
    def _claim_set(
        claims: dict[str, Any], names: tuple[str, ...], *, required: bool
    ) -> tuple[str, ...]:
        values: list[tuple[str, ...]] = []
        for name in names:
            if name not in claims:
                continue
            value = claims[name]
            if isinstance(value, str):
                items = tuple(value.split())
            elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                items = tuple(value)
            else:
                raise PermissionError(f"access token claim {name!r} is malformed")
            if any(not item or item != item.strip() for item in items):
                raise PermissionError("access token values must be normalized")
            values.append(tuple(sorted(set(items))))
        if not values:
            if required:
                raise PermissionError("access token scope claim is required")
            return ()
        if any(value != values[0] for value in values[1:]):
            raise PermissionError("access token claims are contradictory")
        return values[0]
