"""Access checks: combine a subscription's liveness with its plan's policy.

Two questions matter at a paywall:

1. *Feature gating* — may this subscriber use feature ``X`` right now?
   :func:`can_access`.
2. *Limit enforcement* — would one more unit of usage exceed the plan cap?
   :func:`within_limit`.

Both return an :class:`AccessDecision` carrying a boolean plus a human-readable
reason, so callers can both branch and surface upgrade prompts.

Part of Subscription Paywall by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from subscription_paywall.subscription import Subscription


class AccessDecision(BaseModel):
    """The outcome of an access check.

    Attributes:
        allowed: Whether the action is permitted.
        reason: Stable machine/human reason code, e.g. ``"ok"``,
            ``"subscription_inactive"``, ``"feature_not_in_plan"``,
            ``"limit_exceeded"``.
    """

    allowed: bool
    reason: str

    def __bool__(self) -> bool:
        """Allow truthiness checks: ``if can_access(...):``."""
        return self.allowed


def can_access(subscription: Subscription, feature: str, now: datetime) -> AccessDecision:
    """Decide whether ``subscription`` may use ``feature`` at instant ``now``.

    Access requires both that the subscription is live (see
    :meth:`Subscription.is_active`) and that its plan entitles the feature.
    """
    if not subscription.is_active(now):
        return AccessDecision(allowed=False, reason="subscription_inactive")
    if not subscription.plan.has_feature(feature):
        return AccessDecision(allowed=False, reason="feature_not_in_plan")
    return AccessDecision(allowed=True, reason="ok")


def within_limit(
    subscription: Subscription,
    metric: str,
    current_usage: int,
    *,
    requested: int = 1,
    now: datetime | None = None,
) -> AccessDecision:
    """Decide whether ``requested`` more units of ``metric`` stay within the cap.

    The check passes when ``current_usage + requested <= cap``. A cap of
    ``None`` means unlimited and always passes. A metric absent from the plan
    has an effective cap of ``0`` and only passes when nothing is requested.

    Args:
        subscription: The subscription whose plan supplies the cap.
        metric: The named usage metric, e.g. ``"seats"``.
        current_usage: Units already consumed in the current period.
        requested: Additional units the caller wants to consume (default ``1``).
        now: Optional instant; when given, an inactive subscription is denied
            before the limit is even consulted.

    Raises:
        ValueError: if ``current_usage`` or ``requested`` is negative.
    """
    if current_usage < 0:
        raise ValueError("current_usage must be non-negative")
    if requested < 0:
        raise ValueError("requested must be non-negative")
    if now is not None and not subscription.is_active(now):
        return AccessDecision(allowed=False, reason="subscription_inactive")

    cap = subscription.plan.limit_for(metric)
    if cap is None:
        return AccessDecision(allowed=True, reason="unlimited")
    if current_usage + requested <= cap:
        return AccessDecision(allowed=True, reason="ok")
    return AccessDecision(allowed=False, reason="limit_exceeded")
