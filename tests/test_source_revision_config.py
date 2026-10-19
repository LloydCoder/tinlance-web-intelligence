from __future__ import annotations

import pytest

from tinlance_web_intelligence.config import ConfigurationError, Settings


def test_source_revision_is_optional_but_must_be_an_immutable_full_sha() -> None:
    base = {"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}
    assert Settings.from_env(base).source_revision is None
    assert Settings.from_env({**base, "TWI_SOURCE_REVISION": "a" * 40}).source_revision == "a" * 40
    for invalid in ("main", "a" * 39, "A" * 40, "a" * 41, " " + "a" * 40):
        with pytest.raises(ConfigurationError, match="full lowercase Git commit SHA"):
            Settings.from_env({**base, "TWI_SOURCE_REVISION": invalid})
