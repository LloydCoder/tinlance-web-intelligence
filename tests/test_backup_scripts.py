from __future__ import annotations

import pytest
from scripts.check_database_tls import main, validate_database_url


def test_backup_database_url_requires_hostname_verifying_tls() -> None:
    validate_database_url(
        "postgresql://backup:secret@db.example.com:5432/twi?sslmode=verify-full"
    )


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://backup:secret@db.example.com:5432/twi",
        "postgresql://backup:secret@db.example.com:5432/twi?sslmode=require",
        "postgresql://backup:secret@db.example.com:5432/twi?sslmode=verify-full&sslmode=require",
        "postgresql://backup:secret@db.example.com:5432/twi?sslmode=verify-ca",
        "sqlite:///tmp/twi.db",
    ],
)
def test_backup_database_url_rejects_noncompliant_tls(dsn: str) -> None:
    with pytest.raises(ValueError):
        validate_database_url(dsn)



def test_tls_cli_selects_dedicated_dsn_environment_without_printing_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret_dsn = (
        "postgresql://backup:super-secret@db.example.com:5432/twi"
        "?sslmode=verify-full"
    )
    monkeypatch.delenv("TWI_DATABASE_URL", raising=False)
    monkeypatch.setenv("TWI_BACKUP_DATABASE_URL", secret_dsn)
    assert main(["--env", "TWI_BACKUP_DATABASE_URL"]) == 0
    captured = capsys.readouterr()
    assert "super-secret" not in captured.out + captured.err
