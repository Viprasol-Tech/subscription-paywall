"""Subscription paywall — plans, entitlements, and access checks by Viprasol Tech."""

from __future__ import annotations

from subscription_paywall.access import AccessDecision, can_access, within_limit
from subscription_paywall.plans import Plan, default_plans, get_plan
from subscription_paywall.subscription import Subscription, SubscriptionStatus

__version__ = "0.1.0"
__author__ = "Viprasol Tech Private Limited"
__all__ = [
    "AccessDecision",
    "Plan",
    "Subscription",
    "SubscriptionStatus",
    "__version__",
    "can_access",
    "default_plans",
    "get_plan",
    "within_limit",
]
