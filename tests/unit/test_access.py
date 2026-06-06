"""Correctness tests for plans, subscription liveness, and access checks."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from subscription_paywall.access import can_access, within_limit
from subscription_paywall.plans import default_plans, get_plan
from subscription_paywall.subscription import Subscription, SubscriptionStatus

NOW = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
FUTURE = datetime(2025, 7, 1, tzinfo=UTC)
PAST = datetime(2025, 5, 1, tzinfo=UTC)


def _sub(plan_name: str, status: SubscriptionStatus, end: datetime) -> Subscription:
    return Subscription(plan=get_plan(plan_name), status=status, current_period_end=end)


def test_default_plans_are_escalating() -> None:
    plans = default_plans()
    assert plans["free"].features < plans["pro"].features
    assert plans["pro"].features < plans["enterprise"].features
    assert plans["enterprise"].limit_for("seats") is None  # unlimited


def test_active_plan_grants_entitled_and_denies_others() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, FUTURE)
    assert can_access(sub, "api_access", NOW).allowed is True
    assert can_access(sub, "export", NOW).allowed is True
    # 'sso' is enterprise-only.
    denied = can_access(sub, "sso", NOW)
    assert denied.allowed is False
    assert denied.reason == "feature_not_in_plan"


def test_trialing_grants_access() -> None:
    sub = _sub("pro", SubscriptionStatus.TRIALING, FUTURE)
    assert sub.is_active(NOW) is True
    assert can_access(sub, "api_access", NOW).allowed is True


def test_expired_period_denies_even_if_active_status() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, PAST)
    assert sub.is_active(NOW) is False
    decision = can_access(sub, "api_access", NOW)
    assert decision.allowed is False
    assert decision.reason == "subscription_inactive"


def test_canceled_denies_within_period() -> None:
    sub = _sub("enterprise", SubscriptionStatus.CANCELED, FUTURE)
    assert sub.is_active(NOW) is False
    assert can_access(sub, "sso", NOW).reason == "subscription_inactive"


def test_past_due_denies() -> None:
    sub = _sub("pro", SubscriptionStatus.PAST_DUE, FUTURE)
    assert sub.is_active(NOW) is False
    assert can_access(sub, "api_access", NOW).allowed is False


def test_active_at_period_boundary_is_not_live() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, NOW)
    # now == current_period_end -> strictly-before fails.
    assert sub.is_active(NOW) is False


def test_limit_at_cap_allows_then_over_cap_blocks() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, FUTURE)  # seats cap = 5
    # 4 used + 1 requested == 5 -> at the cap, still allowed.
    assert within_limit(sub, "seats", current_usage=4).allowed is True
    # 5 used + 1 requested == 6 -> over the cap, blocked.
    over = within_limit(sub, "seats", current_usage=5)
    assert over.allowed is False
    assert over.reason == "limit_exceeded"


def test_unlimited_limit_always_allows() -> None:
    sub = _sub("enterprise", SubscriptionStatus.ACTIVE, FUTURE)
    decision = within_limit(sub, "seats", current_usage=1_000_000)
    assert decision.allowed is True
    assert decision.reason == "unlimited"


def test_unknown_metric_caps_at_zero() -> None:
    sub = _sub("free", SubscriptionStatus.ACTIVE, FUTURE)
    assert within_limit(sub, "nonexistent", current_usage=0, requested=1).allowed is False
    assert within_limit(sub, "nonexistent", current_usage=0, requested=0).allowed is True


def test_within_limit_respects_now_when_inactive() -> None:
    sub = _sub("enterprise", SubscriptionStatus.CANCELED, FUTURE)
    decision = within_limit(sub, "seats", current_usage=0, now=NOW)
    assert decision.allowed is False
    assert decision.reason == "subscription_inactive"


def test_within_limit_rejects_negative_inputs() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, FUTURE)
    with pytest.raises(ValueError):
        within_limit(sub, "seats", current_usage=-1)
    with pytest.raises(ValueError):
        within_limit(sub, "seats", current_usage=0, requested=-1)


def test_upgrade_changes_entitlements() -> None:
    sub = _sub("free", SubscriptionStatus.ACTIVE, FUTURE)
    assert can_access(sub, "api_access", NOW).allowed is False
    upgraded = sub.with_plan(get_plan("pro"))
    assert can_access(upgraded, "api_access", NOW).allowed is True
    # Original is untouched (immutability of the swap).
    assert can_access(sub, "api_access", NOW).allowed is False


def test_access_decision_is_truthy() -> None:
    sub = _sub("pro", SubscriptionStatus.ACTIVE, FUTURE)
    assert bool(can_access(sub, "export", NOW)) is True
    assert bool(can_access(sub, "sso", NOW)) is False


def test_get_plan_missing_raises() -> None:
    with pytest.raises(KeyError):
        get_plan("nope")
