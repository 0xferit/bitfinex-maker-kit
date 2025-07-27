"""
Wallet command - Show wallet balances.

REFACTORED: Now supports dependency injection pattern.
"""

from typing import Any

from ..utilities.client_factory import get_client
from ..utilities.console import print_operation_error


def wallet_command() -> list[Any]:
    """Get and display wallet balances - with dependency injection support."""
    client = get_client()

    try:
        wallets = client.get_wallets()

        print("\n💰 Wallet Balances:")
        print("─" * 60)
        print(f"{'Type':<15} {'Currency':<10} {'Balance':<15} {'Available':<15}")
        print("─" * 60)

        for wallet in wallets:
            wallet_type = wallet.wallet_type
            currency = wallet.currency
            balance = float(wallet.balance)
            available = float(wallet.available_balance)

            # Only show non-zero balances
            if balance != 0 or available != 0:
                print(f"{wallet_type:<15} {currency:<10} {balance:<15.6f} {available:<15.6f}")

        print("─" * 60)
        # Convert to list[Any] for type safety
        return list(wallets) if wallets else []
    except Exception as e:
        print_operation_error("get wallet data", e)
        return []
