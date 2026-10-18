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
