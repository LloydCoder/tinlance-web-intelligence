from datetime import UTC, datetime

import pytest

from tinlance_web_intelligence.contracts.observations import (
    ContractError,
    Observation,
    SourceReference,
    content_digest,
)


def make_observation() -> Observation:
    now = datetime(2026, 10, 18, tzinfo=UTC)
    source = SourceReference(
        "https://example.com/news",
        now,
        content_sha256=content_digest(b"source body"),
    )
    return Observation(
        "obs-01",
        "Example company announced a product update.",
        source,
        now,
        "rules/1",
        0.8,
    )


def test_observation_serializes_with_utc_timestamps() -> None:
    payload = make_observation().to_dict()
    assert payload["source"]["url"] == "https://example.com/news"
    assert payload["observed_at"].endswith("+00:00")


def test_observation_rejects_naive_datetime() -> None:
    invalid_source = SourceReference("https://example.com", datetime(2026, 1, 1))
    invalid = Observation(
        "obs-02", "statement", invalid_source,
        datetime(2026, 1, 1, tzinfo=UTC), "rules/1"
    )
    with pytest.raises(ContractError):
        invalid.validate()


def test_confidence_bounds_enforced() -> None:
    observation = make_observation()
    invalid = Observation(
        observation.observation_id,
        observation.statement,
        observation.source,
        observation.observed_at,
        observation.extractor_version,
        1.1,
    )
    with pytest.raises(ContractError):
        invalid.validate()
