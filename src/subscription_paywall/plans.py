"""Plan definitions: feature entitlements and usage limits.

A :class:`Plan` is an immutable bundle of *features* (boolean entitlements, e.g.
``"api_access"``) and *limits* (named integer caps, e.g. ``{"seats": 5}``). A
limit value of ``None`` means *unlimited*. Plans are the policy layer of the
paywall; subscriptions (see :mod:`subscription_paywall.subscription`) bind a
customer to a plan, and access checks (see :mod:`subscription_paywall.access`)
combine the two.

Part of Subscription Paywall by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Plan(BaseModel):
    """An immutable subscription plan.

    Attributes:
        name: Stable identifier for the plan, e.g. ``"pro"``.
        title: Human-friendly display name, e.g. ``"Pro"``.
        price_cents: Monthly price in the smallest currency unit (cents).
        features: Names of boolean entitlements this plan grants.
        limits: Named usage caps. A value of ``None`` means unlimited; a
            missing key means the metric is not offered (treated as ``0``).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    title: str
    price_cents: int = Field(ge=0)
    features: frozenset[str] = Field(default_factory=frozenset)
    limits: dict[str, int | None] = Field(default_factory=dict)

    def has_feature(self, feature: str) -> bool:
        """Return ``True`` if this plan entitles ``feature``."""
        return feature in self.features

    def limit_for(self, metric: str) -> int | None:
        """Return the cap for ``metric``.

        Returns ``None`` for an explicitly unlimited metric, or ``0`` when the
        metric is not part of the plan at all.
        """
        return self.limits.get(metric, 0)


def default_plans() -> dict[str, Plan]:
    """Return the built-in free / pro / enterprise plan catalogue.

    The catalogue is escalating: each tier is a superset of the one below it,
    which makes upgrades strictly additive in entitlements and limits.
    """
    free = Plan(
        name="free",
        title="Free",
        price_cents=0,
        features=frozenset({"dashboard"}),
        limits={"seats": 1, "projects": 1, "api_calls_per_day": 100},
    )
    pro = Plan(
        name="pro",
        title="Pro",
        price_cents=2900,
        features=frozenset({"dashboard", "api_access", "export"}),
        limits={"seats": 5, "projects": 20, "api_calls_per_day": 10_000},
    )
    enterprise = Plan(
        name="enterprise",
        title="Enterprise",
        price_cents=9900,
        features=frozenset({"dashboard", "api_access", "export", "sso", "audit_log"}),
        limits={"seats": None, "projects": None, "api_calls_per_day": None},
    )
    return {p.name: p for p in (free, pro, enterprise)}


def get_plan(name: str, catalogue: dict[str, Plan] | None = None) -> Plan:
    """Look up a plan by name in ``catalogue`` (defaults to :func:`default_plans`).

    Raises:
        KeyError: if no plan with ``name`` exists in the catalogue.
    """
    cat = catalogue if catalogue is not None else default_plans()
    return cat[name]
