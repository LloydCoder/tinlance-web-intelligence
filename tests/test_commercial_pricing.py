from __future__ import annotations

import pytest

from tinlance_web_intelligence.commercial.pricing import (
    MONTHLY_PLAN_PRICES_CENTS,
    PRICING_VERSION,
    USAGE_RATES,
    calculate_usage_charge_microusd,
    monthly_plan_price_cents,
)


def test_catalogue_uses_exact_integer_micro_usd_rates() -> None:
    assert PRICING_VERSION == 1
    assert USAGE_RATES["agent_step"].unit_price_microusd == 14_000
    assert USAGE_RATES["standalone_browser"].unit_price_microusd == 2_000
    assert calculate_usage_charge_microusd(meter="agent_step", quantity=1) == 14_000
    assert calculate_usage_charge_microusd(meter="agent_step", quantity=1_000) == 14_000_000
    assert calculate_usage_charge_microusd(meter="standalone_browser", quantity=60) == 120_000


def test_catalogue_matches_recorded_monthly_plan_prices() -> None:
    assert dict(MONTHLY_PLAN_PRICES_CENTS) == {
        "free": 0,
        "starter": 2_900,
        "pro": 9_900,
        "business": 29_900,
        "scale": 79_900,
        "enterprise": None,
    }
    assert monthly_plan_price_cents(plan_id="starter") == 2_900
    assert monthly_plan_price_cents(plan_id="enterprise") is None


@pytest.mark.parametrize("quantity", [-1, True, 1.5, "2", None])
def test_usage_charge_rejects_invalid_quantities(quantity: object) -> None:
    with pytest.raises(ValueError, match="quantity"):
        calculate_usage_charge_microusd(meter="agent_step", quantity=quantity)  # type: ignore[arg-type]


def test_usage_charge_rejects_unknown_meter() -> None:
    with pytest.raises(ValueError, match="meter"):
        calculate_usage_charge_microusd(meter="unknown", quantity=1)


def test_plan_lookup_rejects_unknown_plan_and_invalid_type() -> None:
    with pytest.raises(ValueError, match="unknown plan"):
        monthly_plan_price_cents(plan_id="developer")
    with pytest.raises(ValueError, match="plan_id"):
        monthly_plan_price_cents(plan_id=1)  # type: ignore[arg-type]
