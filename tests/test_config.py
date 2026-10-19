import secrets
from pathlib import Path

import pytest

from tinlance_web_intelligence.config import ConfigurationError, Settings, validate_service_base_url


def test_defaults_are_valid() -> None:
    assert Settings.from_env({}).environment == "development"


@pytest.mark.parametrize("env", [
    {"TWI_MAX_REDIRECTS": "-1"},
    {"TWI_MAX_RESPONSE_BYTES": "0"},
    {"TWI_REQUEST_TIMEOUT_SECONDS": "999"},
    {"TWI_ALLOWED_SCHEMES": "file,https"},
    {"TWI_ENV": "prod"},
])
def test_invalid_settings_are_rejected(env: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env(env)


def test_service_url_requires_https_and_no_userinfo() -> None:
    assert validate_service_base_url("https://platform.example/v1/") == "https://platform.example/v1"
    for value in ("http://platform.example", "https://user:pass@platform.example", "https:///missing"):
        with pytest.raises(ConfigurationError):
            validate_service_base_url(value)

def test_browser_proxy_configuration_fails_closed() -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"TWI_BROWSER_PROXY_URL": "http://proxy:3128"})
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            "TWI_BROWSER_PROXY_URL": "http://proxy:3128",
            "TWI_BROWSER_PROXY_USERNAME": "browser-worker",
            "TWI_BROWSER_PROXY_PASSWORD": "weak",
        })

    with pytest.raises(ConfigurationError):
        Settings.from_env({
            "TWI_BROWSER_PROXY_URL": "http://proxy:0",
            "TWI_BROWSER_PROXY_USERNAME": "browser-worker",
            "TWI_BROWSER_PROXY_PASSWORD": "correct-horse-battery-staple-2026",
        })
    configured = Settings.from_env({
        "TWI_BROWSER_PROXY_URL": "http://egress-proxy:3128",
        "TWI_BROWSER_PROXY_USERNAME": "browser-worker",
        "TWI_BROWSER_PROXY_PASSWORD": "correct-horse-battery-staple-2026",
    })
    assert configured.browser_proxy_url == "http://egress-proxy:3128"


def test_browser_worker_requires_enabled_flag_and_authenticated_proxy() -> None:
    from tinlance_web_intelligence.browser.service import BrowserService

    with pytest.raises(ConfigurationError):
        BrowserService(Settings.from_env({}))
    with pytest.raises(ConfigurationError):
        BrowserService(Settings.from_env({"TWI_BROWSER_ENABLED": "true"}))


def test_example_environment_file_has_valid_defaults() -> None:
    example_path = Path(__file__).resolve().parents[1] / ".env.example"
    values: dict[str, str] = {}
    for line in example_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    settings = Settings.from_env(values)
    assert settings.browser_enabled is False


def test_world_intelligence_service_settings_fail_closed() -> None:
    token = secrets.token_urlsafe(32)
    with pytest.raises(ConfigurationError):
        Settings.from_env({"TWI_WORLD_INTELLIGENCE_URL": "https://wi.example"})
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            "TWI_WORLD_INTELLIGENCE_URL": "http://wi.example",
            "TWI_WORLD_INTELLIGENCE_TOKEN": token,
        })
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            "TWI_WORLD_INTELLIGENCE_URL": "https://wi.example/path",
            "TWI_WORLD_INTELLIGENCE_TOKEN": token,
        })
    configured = Settings.from_env({
        "TWI_WORLD_INTELLIGENCE_URL": "http://world-intelligence:8080",
        "TWI_WORLD_INTELLIGENCE_TOKEN": token,
    })
    assert configured.world_intelligence_url == "http://world-intelligence:8080"



def test_production_requires_postgres_with_verified_tls() -> None:
    identity = {
        "TWI_ENV": "production",
        "TWI_IDENTITY_ISSUER": "https://identity.example/issuer",
        "TWI_IDENTITY_AUDIENCE": "twi-api",
        "TWI_IDENTITY_JWKS_URL": "https://identity.example/.well-known/jwks.json",
    }
    with pytest.raises(ConfigurationError):
        Settings.from_env(identity)
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            **identity,
            "TWI_DATABASE_URL": "postgresql://twi:secret@db.example/twi?sslmode=require",
        })
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            **identity,
            "TWI_DATABASE_URL": (
                "postgresql://twi:secret@db.example/twi?"
                "sslmode=verify-full&sslmode=require"
            ),
        })
    settings = Settings.from_env({
        **identity,
        "TWI_DATABASE_URL": "postgresql://twi:secret@db.example/twi?sslmode=verify-full",
    })
    assert settings.database_url is not None


@pytest.mark.parametrize("database_url", [
    "sqlite:///tmp/twi.db",
    "postgresql:///missing-host",
    "postgresql://twi@db.example/twi",
    "postgresql://twi:secret@db.example/",
    "postgresql://twi:secret@db.example/twi#fragment",
])
def test_invalid_postgres_urls_are_rejected(database_url: str) -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"TWI_DATABASE_URL": database_url})


def test_staging_requires_postgres_with_verified_tls() -> None:
    with pytest.raises(ConfigurationError):
        Settings.from_env({"TWI_ENV": "staging"})
    with pytest.raises(ConfigurationError):
        Settings.from_env({
            "TWI_ENV": "staging",
            "TWI_DATABASE_URL": "postgresql://twi:secret@db.example/twi?sslmode=require",
        })
    configured = Settings.from_env({
        "TWI_ENV": "staging",
        "TWI_DATABASE_URL": "postgresql://twi:secret@db.example/twi?sslmode=verify-full",
    })
    assert configured.environment == "staging"


def test_production_browser_worker_can_start_without_database_credentials() -> None:
    token = secrets.token_urlsafe(32)
    settings = Settings.from_env(
        {
            "TWI_ENV": "production",
            "TWI_BROWSER_ENABLED": "true",
            "TWI_BROWSER_BROKER_URL": "http://browser-broker:8081",
            "TWI_BROWSER_BROKER_TOKEN": token,
            "TWI_BROWSER_PROXY_URL": "http://egress-proxy:3128",
            "TWI_BROWSER_PROXY_USERNAME": "browser-worker",
            "TWI_BROWSER_PROXY_PASSWORD": "browser-proxy-password-123456",
        },
        require_identity=False,
        require_database=False,
    )
    assert settings.database_url is None
    assert settings.browser_enabled is True
