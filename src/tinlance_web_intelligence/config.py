"""Validated runtime configuration; no secrets are logged or serialized."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Raised when runtime configuration violates an invariant."""


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = "development"
    log_level: str = "INFO"
    max_response_bytes: int = 5_000_000
    max_redirects: int = 5
    request_timeout_seconds: float = 15.0
    allowed_schemes: tuple[str, ...] = ("https", "http")
    user_agent: str = "TinlanceWebIntelligence/0.1"
    database_path: str = "./var/twi.sqlite3"
    identity_issuer: str | None = None
    identity_audience: str | None = None
    identity_jwks_url: str | None = None
    brave_api_key: str | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        try:
            schemes = values.get("TWI_ALLOWED_SCHEMES", "https,http").split(",")
            settings = cls(
                environment=values.get("TWI_ENV", "development").lower(),
                log_level=values.get("TWI_LOG_LEVEL", "INFO").upper(),
                max_response_bytes=int(values.get("TWI_MAX_RESPONSE_BYTES", "5000000")),
                max_redirects=int(values.get("TWI_MAX_REDIRECTS", "5")),
                request_timeout_seconds=float(values.get("TWI_REQUEST_TIMEOUT_SECONDS", "15")),
                allowed_schemes=tuple(item.strip().lower() for item in schemes if item.strip()),
                user_agent=values.get("TWI_USER_AGENT", "TinlanceWebIntelligence/0.1").strip(),
                database_path=values.get("TWI_DATABASE_PATH", "./var/twi.sqlite3").strip(),
                identity_issuer=values.get("TWI_IDENTITY_ISSUER") or None,
                identity_audience=values.get("TWI_IDENTITY_AUDIENCE") or None,
                identity_jwks_url=values.get("TWI_IDENTITY_JWKS_URL") or None,
                brave_api_key=values.get("TWI_BRAVE_SEARCH_API_KEY") or None,
            )
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("invalid numeric or list configuration") from exc
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ConfigurationError("TWI_ENV must be development, test, staging, or production")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("TWI_LOG_LEVEL is not a supported level")
        if not 1 <= self.max_response_bytes <= 100_000_000:
            raise ConfigurationError("response byte limit must be between 1 and 100000000")
        if not 0 <= self.max_redirects <= 10:
            raise ConfigurationError("redirect limit must be between 0 and 10")
        if not 0.1 <= self.request_timeout_seconds <= 120:
            raise ConfigurationError("request timeout must be between 0.1 and 120 seconds")
        if not self.allowed_schemes or any(
            scheme not in {"http", "https"} for scheme in self.allowed_schemes
        ):
            raise ConfigurationError("only http and https schemes may be configured")
        if not self.user_agent or any(ord(ch) < 32 for ch in self.user_agent):
            raise ConfigurationError("user agent must be non-empty and contain no control chars")
        if not self.database_path or "\x00" in self.database_path:
            raise ConfigurationError("database path must be non-empty")
        identity_values = (self.identity_issuer, self.identity_audience, self.identity_jwks_url)
        if any(identity_values) and not all(identity_values):
            raise ConfigurationError(
                "identity issuer, audience, and JWKS URL must be configured together"
            )
        if self.environment == "production" and not all(identity_values):
            raise ConfigurationError(
                "production requires Platform identity issuer, audience, and JWKS URL"
            )
        if self.identity_audience is not None and (
            not self.identity_audience or self.identity_audience != self.identity_audience.strip()
        ):
            raise ConfigurationError("identity audience must be non-empty and normalized")
        for value in (self.identity_issuer, self.identity_jwks_url):
            if value is None:
                continue
            parsed = urlsplit(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
            ):
                raise ConfigurationError(
                    "identity issuer and JWKS URL must be absolute HTTPS URLs"
                )
        if self.brave_api_key is not None and not self.brave_api_key.strip():
            raise ConfigurationError("Brave Search API key must be non-empty when configured")


def validate_service_base_url(value: str) -> str:
    """Validate a configured HTTPS service endpoint; it is not a credential check."""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigurationError("service base URL must be HTTPS with a hostname and no userinfo")
    if parsed.fragment:
        raise ConfigurationError("service base URL must not contain a fragment")
    return value.rstrip("/")
