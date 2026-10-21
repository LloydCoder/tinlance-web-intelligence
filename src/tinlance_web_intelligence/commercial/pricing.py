"""Versioned, exact-arithmetic Tinlyt public unit pricing.

These values are a pricing catalogue primitive, not a payment provider, invoice ledger,
subscription entitlement resolver, or permission to enable paid production execution.
Amounts use integer micro-USD ($0.000001) to avoid floating-point billing errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

PRICING_VERSION = 1
CURRENCY = "USD"
MICRO_USD_PER_USD = 1_000_000
CENTS_PER_USD = 100


@dataclass(frozen=True, slots=True)
class UsageRate:
    """Exact unit rate for one explicitly defined billable meter."""

    meter: str
    unit: str
    unit_price_microusd: int
    version: int = PRICING_VERSION
    currency: str = CURRENCY

    def __post_init__(self) -> None:
        if not self.meter or len(self.meter) > 80:
            raise ValueError("meter must contain 1 to 80 characters")
        if not self.unit or len(self.unit) > 80:
            raise ValueError("unit must contain 1 to 80 characters")
        if (
            isinstance(self.unit_price_microusd, bool)
            or not isinstance(self.unit_price_microusd, int)
            or self.unit_price_microusd < 0
        ):
            raise ValueError("unit price must be a non-negative integer number of micro-USD")
        if self.version < 1:
            raise ValueError("pricing version must be positive")
        if self.currency != CURRENCY:
            raise ValueError("only USD is supported by this pricing catalogue")


# $0.014 per completed billable agent step; $0.002 per standalone browser minute.
USAGE_RATES: MappingProxyType[str, UsageRate] = MappingProxyType({
    "agent_step": UsageRate(
        meter="agent_step",
        unit="completed_billable_step",
        unit_price_microusd=14_000,
    ),
    "standalone_browser": UsageRate(
        meter="standalone_browser",
        unit="billable_browser_minute",
        unit_price_microusd=2_000,
    ),
})


# Monthly subscription headline prices in USD cents. None means contract-priced.
# Included usage and overage entitlements are deliberately not inferred here.
MONTHLY_PLAN_PRICES_CENTS: MappingProxyType[str, int | None] = MappingProxyType({
    "free": 0,
    "starter": 2_900,
    "pro": 9_900,
    "business": 29_900,
    "scale": 79_900,
    "enterprise": None,
})


def calculate_usage_charge_microusd(*, meter: str, quantity: int) -> int:
    """Return exact charge in micro-USD for an integer quantity of a billable meter.

    Quantity is the count of completed billable steps or already-rounded billable
    browser minutes. Browser duration measurement and rounding are separate runtime
    policy and must be fixed before production browser metering is enabled.
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise ValueError("quantity must be a non-negative integer")
    try:
        rate = USAGE_RATES[meter]
    except (KeyError, TypeError) as exc:
        raise ValueError("unknown or unsupported usage meter") from exc
    return rate.unit_price_microusd * quantity


def monthly_plan_price_cents(*, plan_id: str) -> int | None:
    """Return the headline monthly subscription price in cents; Enterprise is custom."""
    if not isinstance(plan_id, str):
        raise ValueError("plan_id must be a string")
    try:
        return MONTHLY_PLAN_PRICES_CENTS[plan_id]
    except KeyError as exc:
        raise ValueError("unknown plan") from exc
