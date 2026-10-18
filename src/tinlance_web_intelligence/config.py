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

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        try:
            settings = cls(
                environment=values.get("TWI_ENV", "development").lower(),
                log_level=values.get("TWI_LOG_LEVEL", "INFO").upper(),
                max_response_bytes=int(values.get("TWI_MAX_RESPONSE_BYTES", "5000000")),
                max_redirects=int(values.get("TWI_MAX_REDIRECTS", "5")),
                request_timeout_seconds=float(values.get("TWI_REQUEST_TIMEOUT_SECONDS", "15")),
                allowed_schemes=tuple(item.strip().lower() for item in values.get("TWI_ALLOWED_SCHEMES", "https,http").split(",") if item.strip()),
                user_agent=values.get("TWI_USER_AGENT", "TinlanceWebIntelligence/0.1").strip(),
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
        if not self.allowed_schemes or any(scheme not in {"http", "https"} for scheme in self.allowed_schemes):
            raise ConfigurationError("only http and https schemes may be configured")
        if not self.user_agent or any(ord(ch) < 32 for ch in self.user_agent):
            raise ConfigurationError("user agent must be non-empty and contain no control chars")


def validate_service_base_url(value: str) -> str:
    """Validate a configured service URL; this does not replace request authentication."""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigurationError("service base URL must be HTTPS with a hostname and no userinfo")
    if parsed.fragment:
        raise ConfigurationError("service base URL must not contain a fragment")
    return value.rstrip("/")
