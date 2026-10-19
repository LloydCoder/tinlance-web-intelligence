from __future__ import annotations

import pytest

from tinlance_web_intelligence.commercial.entitlements import (
    EntitlementError,
    PlanEntitlements,
    evaluate_feature,
    evaluate_quota,
)


def test_feature_grant_requires_explicit_feature_and_known_plan() -> None:
    plan = PlanEntitlements("starter", 1, frozenset({"search"}), {"requests_month": 10})
    assert evaluate_feature(plan, feature="search").allowed
    assert evaluate_feature(plan, feature="browser").reason == "feature_not_entitled"
    assert evaluate_feature(None, feature="search").reason == "unknown_plan"


def test_quota_enforces_exact_boundary_and_rejects_overage() -> None:
    plan = PlanEntitlements("starter", 1, frozenset({"search"}), {"requests_month": 10})
    assert evaluate_quota(
        plan, feature="search", dimension="requests_month", observed=9, requested=1
    ).allowed
    decision = evaluate_quota(
        plan, feature="search", dimension="requests_month", observed=10, requested=1
    )
    assert not decision.allowed
    assert decision.reason == "quota_exceeded"
    assert decision.limit == 10


def test_unconfigured_quota_dimension_fails_closed() -> None:
    plan = PlanEntitlements("starter", 1, frozenset({"search"}), {})
    decision = evaluate_quota(
        plan, feature="search", dimension="requests_month", observed=0
    )
    assert not decision.allowed
    assert decision.reason == "quota_dimension_not_configured"


@pytest.mark.parametrize("limit", [-1, True, 1.5, "10"])
def test_plan_rejects_invalid_limits(limit: object) -> None:
    with pytest.raises(EntitlementError):
        PlanEntitlements("starter", 1, frozenset({"search"}), {"requests_month": limit})  # type: ignore[dict-item]


@pytest.mark.parametrize("observed,requested", [(-1, 1), (True, 1), (0, 0), (0, True)])
def test_quota_rejects_invalid_quantities(observed: object, requested: object) -> None:
    plan = PlanEntitlements("starter", 1, frozenset({"search"}), {"requests_month": 10})
    decision = evaluate_quota(
        plan, feature="search", dimension="requests_month",
        observed=observed, requested=requested,  # type: ignore[arg-type]
    )
    assert not decision.allowed
    assert decision.reason in {"invalid_observed_usage", "invalid_requested_usage"}


def test_limits_are_copied_and_read_only() -> None:
    source = {"requests_month": 10}
    plan = PlanEntitlements("starter", 1, frozenset({"search"}), source)
    source["requests_month"] = 999
    assert plan.limits["requests_month"] == 10
    with pytest.raises(TypeError):
        plan.limits["requests_month"] = 5  # type: ignore[index]
