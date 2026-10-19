"""Validated runtime configuration; no secrets are logged or serialized."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


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
    database_url: str | None = None
    identity_issuer: str | None = None
    identity_audience: str | None = None
    identity_jwks_url: str | None = None
    brave_api_key: str | None = None
    browser_enabled: bool = False
    browser_proxy_url: str | None = None
    browser_proxy_username: str | None = None
    browser_proxy_password: str | None = None
    browser_broker_url: str | None = None
    browser_broker_token: str | None = None
    world_intelligence_url: str | None = None
    world_intelligence_token: str | None = None

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        require_identity: bool = True,
        require_database: bool = True,
    ) -> Settings:
        values = os.environ if env is None else env
        browser_enabled_raw = values.get("TWI_BROWSER_ENABLED", "false").strip().lower()
        if browser_enabled_raw not in {"true", "false"}:
            raise ConfigurationError("TWI_BROWSER_ENABLED must be true or false")
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
                database_url=values.get("TWI_DATABASE_URL", "").strip() or None,
                identity_issuer=values.get("TWI_IDENTITY_ISSUER") or None,
                identity_audience=values.get("TWI_IDENTITY_AUDIENCE") or None,
                identity_jwks_url=values.get("TWI_IDENTITY_JWKS_URL") or None,
                brave_api_key=values.get("TWI_BRAVE_SEARCH_API_KEY") or None,
                browser_enabled=browser_enabled_raw == "true",
                browser_proxy_url=values.get("TWI_BROWSER_PROXY_URL") or None,
                browser_proxy_username=values.get("TWI_BROWSER_PROXY_USERNAME") or None,
                browser_proxy_password=values.get("TWI_BROWSER_PROXY_PASSWORD") or None,
                browser_broker_url=values.get("TWI_BROWSER_BROKER_URL") or None,
                browser_broker_token=values.get("TWI_BROWSER_BROKER_TOKEN") or None,
                world_intelligence_url=values.get("TWI_WORLD_INTELLIGENCE_URL") or None,
                world_intelligence_token=values.get("TWI_WORLD_INTELLIGENCE_TOKEN") or None,
            )
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("invalid numeric or list configuration") from exc
        settings.validate(
            require_identity=require_identity, require_database=require_database
        )
        return settings

    def validate(
        self, *, require_identity: bool = True, require_database: bool = True
    ) -> None:
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
        if (
            require_database
            and self.environment in {"staging", "production"}
            and self.database_url is None
        ):
            raise ConfigurationError(
                "staging and production require TWI_DATABASE_URL PostgreSQL persistence"
            )
        if self.database_url is not None:
            try:
                database = urlsplit(self.database_url)
                query = parse_qs(database.query, keep_blank_values=True, strict_parsing=False)
            except ValueError as exc:
                raise ConfigurationError("PostgreSQL database URL is malformed") from exc
            if (
                database.scheme not in {"postgres", "postgresql"}
                or not database.hostname
                or not database.username
                or not database.password
                or not database.path.strip("/")
                or database.fragment
            ):
                raise ConfigurationError(
                    "TWI_DATABASE_URL must be a PostgreSQL URL with host, credentials, and database"
                )
            sslmode_values = query.get("sslmode", [])
            if len(sslmode_values) > 1:
                raise ConfigurationError("PostgreSQL sslmode must be specified exactly once")
            sslmode = sslmode_values[0] if sslmode_values else ""
            if sslmode and sslmode not in {
                "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
            }:
                raise ConfigurationError("unsupported PostgreSQL sslmode")
            if self.environment in {"staging", "production"} and sslmode != "verify-full":
                raise ConfigurationError(
                    "staging and production PostgreSQL require sslmode=verify-full"
                )
        identity_values = (self.identity_issuer, self.identity_audience, self.identity_jwks_url)
        if any(identity_values) and not all(identity_values):
            raise ConfigurationError(
                "identity issuer, audience, and JWKS URL must be configured together"
            )
        if require_identity and self.environment == "production" and not all(identity_values):
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
        proxy_values = (
            self.browser_proxy_url,
            self.browser_proxy_username,
            self.browser_proxy_password,
        )
        if any(proxy_values) and not all(proxy_values):
            raise ConfigurationError(
                "browser proxy URL, username, and password must be configured together"
            )
        broker_values = (self.browser_broker_url, self.browser_broker_token)
        if any(broker_values) and not all(broker_values):
            raise ConfigurationError(
                "browser broker URL and service token must be configured together"
            )
        if self.browser_broker_url is not None:
            try:
                broker_url = urlsplit(self.browser_broker_url)
                broker_port = broker_url.port
            except ValueError as exc:
                raise ConfigurationError("browser broker URL or port is malformed") from exc
            if (
                broker_url.scheme not in {"http", "https"}
                or not broker_url.hostname
                or broker_url.username is not None
                or broker_url.password is not None
                or broker_url.path not in {"", "/"}
                or broker_url.query
                or broker_url.fragment
                or (broker_port is not None and not 1 <= broker_port <= 65535)
            ):
                raise ConfigurationError("browser broker URL must be an absolute HTTP(S) origin")
            if (
                self.browser_broker_token is None
                or len(self.browser_broker_token) < 32
                or self.browser_broker_token != self.browser_broker_token.strip()
            ):
                raise ConfigurationError(
                    "browser broker token must contain at least 32 non-padded characters"
                )
        world_intelligence_values = (
            self.world_intelligence_url,
            self.world_intelligence_token,
        )
        if any(world_intelligence_values) and not all(world_intelligence_values):
            raise ConfigurationError(
                "World Intelligence URL and service token must be configured together"
            )
        if self.world_intelligence_url is not None:
            try:
                wi_url = urlsplit(self.world_intelligence_url)
                wi_port = wi_url.port
            except ValueError as exc:
                raise ConfigurationError("World Intelligence URL or port is malformed") from exc
            local_http = (
                self.environment in {"development", "test"}
                and wi_url.scheme == "http"
                and wi_url.hostname in {"localhost", "127.0.0.1", "world-intelligence"}
            )
            if (
                (wi_url.scheme != "https" and not local_http)
                or not wi_url.hostname
                or wi_url.username is not None
                or wi_url.password is not None
                or wi_url.path not in {"", "/"}
                or wi_url.query
                or wi_url.fragment
                or (wi_port is not None and not 1 <= wi_port <= 65535)
            ):
                raise ConfigurationError(
                    "World Intelligence URL must be an HTTPS service origin "
                    "(HTTP is allowed only for local development)"
                )
            if (
                self.world_intelligence_token is None
                or len(self.world_intelligence_token) < 32
                or self.world_intelligence_token != self.world_intelligence_token.strip()
            ):
                raise ConfigurationError(
                    "World Intelligence service token must contain at least 32 "
                    "non-padded characters"
                )
        if self.browser_proxy_url is not None:
            try:
                parsed_proxy = urlsplit(self.browser_proxy_url)
                proxy_port = parsed_proxy.port
            except ValueError as exc:
                raise ConfigurationError("browser proxy URL or port is malformed") from exc
            if (
                parsed_proxy.scheme not in {"http", "https"}
                or not parsed_proxy.hostname
                or parsed_proxy.username is not None
                or parsed_proxy.password is not None
                or parsed_proxy.path not in {"", "/"}
                or parsed_proxy.query
                or parsed_proxy.fragment
                or proxy_port is None
                or not 1 <= proxy_port <= 65535
            ):
                raise ConfigurationError(
                    "browser proxy must be an absolute HTTP(S) host:port URL"
                )
            if (
                not self.browser_proxy_username
                or self.browser_proxy_username != self.browser_proxy_username.strip()
            ):
                raise ConfigurationError(
                    "browser proxy username must be non-empty and normalized"
                )
            if (
                self.browser_proxy_password is None
                or len(self.browser_proxy_password) < 24
                or self.browser_proxy_password != self.browser_proxy_password.strip()
                or any(ord(ch) < 33 or ord(ch) > 126 for ch in self.browser_proxy_password)
            ):
                raise ConfigurationError(
                    "browser proxy password must be at least 24 printable ASCII characters"
                )


def validate_service_base_url(value: str) -> str:
    """Validate a configured HTTPS service endpoint; it is not a credential check."""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigurationError("service base URL must be HTTPS with a hostname and no userinfo")
    if parsed.fragment:
        raise ConfigurationError("service base URL must not contain a fragment")
    return value.rstrip("/")
