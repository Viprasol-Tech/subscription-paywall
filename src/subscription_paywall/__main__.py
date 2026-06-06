"""Enable ``python -m subscription_paywall`` to invoke the CLI.

Part of Subscription Paywall by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from subscription_paywall.cli import app

if __name__ == "__main__":
    app()
