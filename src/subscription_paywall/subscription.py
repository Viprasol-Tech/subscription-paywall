"""Subscription state: which plan a customer holds and whether it is live.

A :class:`Subscription` binds a :class:`~subscription_paywall.plans.Plan` to a
lifecycle :class:`SubscriptionStatus` and a ``current_period_end`` timestamp.
Liveness is evaluated against an injected ``now`` so the logic is deterministic
and fully testable offline.

Part of Subscription Paywall by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from subscription_paywall.plans import Plan


class SubscriptionStatus(str, Enum):
    """Lifecycle status of a subscription.

    - ``TRIALING``: in a free trial; grants full plan entitlements until expiry.
    - ``ACTIVE``: paid and current; grants entitlements until ``current_period_end``.
    - ``PAST_DUE``: payment failed; treated as not live (access denied).
    - ``CANCELED``: ended by the customer or provider; access denied.
    """

    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Subscription(BaseModel):
    """A customer's binding to a plan over a billing period.

    Attributes:
        plan: The plan whose entitlements and limits apply while live.
        status: Current lifecycle status.
        current_period_end: Instant at which the current paid/trial period ends.
            Access is denied at or after this instant unless renewed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    plan: Plan
    status: SubscriptionStatus
    current_period_end: datetime

    def is_active(self, now: datetime) -> bool:
        """Return ``True`` if the subscription grants access at instant ``now``.

        A subscription is live only when its status is ``ACTIVE`` or
        ``TRIALING`` *and* ``now`` is strictly before ``current_period_end``.
        ``PAST_DUE`` and ``CANCELED`` are never live, regardless of the period.
        """
        if self.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            return False
        return now < self.current_period_end

    def with_plan(self, plan: Plan) -> Subscription:
        """Return a copy of this subscription switched to ``plan``.

        Used to model an upgrade or downgrade: status and period are preserved
        while entitlements and limits follow the new plan.
        """
        return self.model_copy(update={"plan": plan})
