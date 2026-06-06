"""Command-line interface for Subscription Paywall.

``subscription-paywall demo`` evaluates feature access and usage limits for a
handful of representative subscriptions against an injected ``now`` — no clock,
no network, fully deterministic.

Part of Subscription Paywall by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from datetime import UTC, datetime

import typer
from rich.console import Console
from rich.table import Table

from subscription_paywall import __version__
from subscription_paywall.access import can_access, within_limit
from subscription_paywall.plans import get_plan
from subscription_paywall.subscription import Subscription, SubscriptionStatus

app = typer.Typer(add_completion=False, help="Subscription Paywall — by Viprasol Tech.")
console = Console()

# A fixed reference instant so the demo is deterministic and offline.
_NOW = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


def _sample_subscriptions() -> dict[str, Subscription]:
    """Build representative subscriptions evaluated relative to ``_NOW``."""
    future = datetime(2025, 7, 1, tzinfo=UTC)
    past = datetime(2025, 5, 1, tzinfo=UTC)
    return {
        "free-active": Subscription(
            plan=get_plan("free"),
            status=SubscriptionStatus.ACTIVE,
            current_period_end=future,
        ),
        "pro-trialing": Subscription(
            plan=get_plan("pro"),
            status=SubscriptionStatus.TRIALING,
            current_period_end=future,
        ),
        "pro-expired": Subscription(
            plan=get_plan("pro"),
            status=SubscriptionStatus.ACTIVE,
            current_period_end=past,
        ),
        "enterprise-canceled": Subscription(
            plan=get_plan("enterprise"),
            status=SubscriptionStatus.CANCELED,
            current_period_end=future,
        ),
    }


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"subscription-paywall [bold cyan]{__version__}[/] — by Viprasol Tech")


@app.command()
def demo() -> None:
    """Evaluate access and limits for sample subscriptions offline."""
    subs = _sample_subscriptions()
    console.print(f"Evaluating at [bold]{_NOW.isoformat()}[/]\n")

    feature_table = Table(title="Feature access (can_access)")
    feature_table.add_column("Subscription", style="cyan")
    feature_table.add_column("Plan")
    feature_table.add_column("api_access")
    feature_table.add_column("export")
    feature_table.add_column("sso")
    for label, sub in subs.items():
        cells = [label, sub.plan.title]
        for feature in ("api_access", "export", "sso"):
            decision = can_access(sub, feature, _NOW)
            mark = "[green]allow[/]" if decision.allowed else f"[red]deny[/] ({decision.reason})"
            cells.append(mark)
        feature_table.add_row(*cells)
    console.print(feature_table)

    limit_table = Table(title="Limit enforcement (within_limit: seats, +1)")
    limit_table.add_column("Subscription", style="cyan")
    limit_table.add_column("Cap")
    limit_table.add_column("Usage 0", justify="center")
    limit_table.add_column("At cap", justify="center")
    for label, sub in subs.items():
        cap = sub.plan.limit_for("seats")
        cap_text = "unlimited" if cap is None else str(cap)
        at_zero = within_limit(sub, "seats", current_usage=0).allowed
        at_cap_usage = 0 if cap is None else cap
        at_cap = within_limit(sub, "seats", current_usage=at_cap_usage).allowed
        limit_table.add_row(
            label,
            cap_text,
            "[green]ok[/]" if at_zero else "[red]blocked[/]",
            "[green]ok[/]" if at_cap else "[red]blocked[/]",
        )
    console.print(limit_table)

    # Demonstrate an upgrade flipping an entitlement on.
    free_sub = subs["free-active"]
    before = can_access(free_sub, "api_access", _NOW)
    upgraded = free_sub.with_plan(get_plan("pro"))
    after = can_access(upgraded, "api_access", _NOW)
    console.print(
        f"\nUpgrade free -> pro: api_access [red]{before.reason}[/] -> [green]{after.reason}[/]"
    )


if __name__ == "__main__":
    app()
