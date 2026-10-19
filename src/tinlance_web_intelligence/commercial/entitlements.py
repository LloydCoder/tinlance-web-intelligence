"""Versioned, fail-closed commercial entitlement primitives.

These pure domain functions are intentionally provider-neutral. They do not replace
Platform authorization, durable quota reservations, or a billing provider's ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


class EntitlementError(ValueError):
    """Raised when a plan definition is malformed."""


@dataclass(frozen=True, slots=True)
class PlanEntitlements:
    """Immutable plan snapshot with explicit feature grants and hard usage limits."""

    plan_id: str
    version: int
    features: frozenset[str]
    limits: Mapping[str, int]

    def __post_init__(self) -> None:
        if not self.plan_id or len(self.plan_id) > 80:
            raise EntitlementError("plan_id must contain 1 to 80 characters")
        if self.version < 1:
            raise EntitlementError("plan version must be positive")
        if any(not feature or len(feature) > 100 for feature in self.features):
            raise EntitlementError("feature names must contain 1 to 100 characters")
        normalized: dict[str, int] = {}
        for dimension, limit in self.limits.items():
            if not dimension or len(dimension) > 80:
                raise EntitlementError("limit dimensions must contain 1 to 80 characters")
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise EntitlementError("limits must be non-negative integers")
            normalized[dimension] = limit
        object.__setattr__(self, "features", frozenset(self.features))
        object.__setattr__(self, "limits", MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class EntitlementDecision:
    """Stable decision shape suitable for API mapping and audit evidence."""

    allowed: bool
    reason: str
    plan_id: str | None
    plan_version: int | None
    feature: str
    dimension: str | None = None
    limit: int | None = None
    observed: int | None = None
    requested: int | None = None


def evaluate_feature(
    plan: PlanEntitlements | None, *, feature: str
) -> EntitlementDecision:
    """Grant only an explicitly configured feature on a known plan."""
    if not feature:
        return EntitlementDecision(False, "invalid_feature", None, None, feature)
    if plan is None:
        return EntitlementDecision(False, "unknown_plan", None, None, feature)
    if feature not in plan.features:
        return EntitlementDecision(
            False, "feature_not_entitled", plan.plan_id, plan.version, feature
        )
    return EntitlementDecision(True, "feature_entitled", plan.plan_id, plan.version, feature)


def evaluate_quota(
    plan: PlanEntitlements | None,
    *,
    feature: str,
    dimension: str,
    observed: int,
    requested: int = 1,
) -> EntitlementDecision:
    """Fail closed when plan, feature, quota dimension, or quantities are invalid.

    This is a deterministic decision primitive, not an atomic quota reservation.
    Production enforcement must pair it with durable transactional reservation.
    """
    if isinstance(observed, bool) or not isinstance(observed, int) or observed < 0:
        return EntitlementDecision(False, "invalid_observed_usage", None, None, feature)
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 1:
        return EntitlementDecision(False, "invalid_requested_usage", None, None, feature)
    feature_decision = evaluate_feature(plan, feature=feature)
    if not feature_decision.allowed:
        return feature_decision
    assert plan is not None
    limit = plan.limits.get(dimension)
    if limit is None:
        return EntitlementDecision(
            False, "quota_dimension_not_configured", plan.plan_id, plan.version,
            feature, dimension, None, observed, requested
        )
    allowed = observed + requested <= limit
    return EntitlementDecision(
        allowed,
        "within_quota" if allowed else "quota_exceeded",
        plan.plan_id,
        plan.version,
        feature,
        dimension,
        limit,
        observed,
        requested,
    )
