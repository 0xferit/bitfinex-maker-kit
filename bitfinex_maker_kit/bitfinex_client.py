"""
Bitfinex API Wrapper with POST_ONLY enforcement.

This wrapper class sits between the application and the Bitfinex API library,
enforcing POST_ONLY for all limit orders at the API boundary level.
This makes it architecturally impossible to place non-POST_ONLY limit orders.

REFACTORED: Now uses focused components internally while maintaining
backward compatibility for existing code.
"""

from typing import Any

from bfxapi.types import Notification, Order  # type: ignore

from .core.trading_facade import create_trading_facade
from .utilities.constants import OrderSide

# Re-export types for application use (API boundary isolation)
__all__ = ["BitfinexClientWrapper", "Notification", "Order", "create_wrapper_client"]


class BitfinexClientWrapper:
    """
    Wrapper around Bitfinex API Client that ENFORCES POST_ONLY for all limit orders.

    REFACTORED: This class now delegates to focused components while maintaining
    the same external interface for backward compatibility.

    Key Features:
    - ✅ POST_ONLY enforcement at API boundary
    - ✅ Impossible to bypass from application layer
    - ✅ Clean separation of concerns through focused components
    - ✅ Market orders handled correctly (no POST_ONLY flag)
    - ✅ Backward compatible interface
    """

    def __init__(self, api_key: str, api_secret: str):
        """Initialize wrapper with API credentials using focused facade."""
        self.trading_facade = create_trading_facade(api_key, api_secret)

    def submit_order(
        self, symbol: str, side: str | OrderSide, amount: float, price: float | None = None
    ) -> Any:
        """
        Submit order with ENFORCED POST_ONLY for limit orders.

        Delegates to the focused trading facade.
        """
        return self.trading_facade.submit_order(symbol, side, amount, price)

    def get_orders(self) -> list[Any]:
        """Get all active orders."""
        return self.trading_facade.get_orders()

    def cancel_order(self, order_id: int) -> Any:
        """Cancel a single order by ID."""
        return self.trading_facade.cancel_order(order_id)

    def cancel_order_multi(self, order_ids: list[int]) -> Any:
        """Cancel multiple orders by IDs."""
        return self.trading_facade.cancel_order_multi(order_ids)

    def update_order(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
        use_cancel_recreate: bool = False,
    ) -> dict[str, Any]:
        """
        Update an existing order using configurable strategies.

        Delegates to the focused trading facade.
        """
        return self.trading_facade.update_order(order_id, price, amount, delta, use_cancel_recreate)

    def get_wallets(self) -> Any:
        """Get wallet balances."""
        return self.trading_facade.get_wallets()

    def get_ticker(self, symbol: str) -> Any:
        """Get ticker data for symbol."""
        return self.trading_facade.get_ticker(symbol)

    def get_trades(self, symbol: str, limit: int = 1) -> Any:
        """Get recent trades for symbol."""
        return self.trading_facade.get_trades(symbol, limit)

    @property
    def wss(self) -> Any:
        """Access to WebSocket interface for real-time data."""
        return self.trading_facade.wss


def create_wrapper_client(api_key: str, api_secret: str) -> BitfinexClientWrapper:
    """
    Factory function to create Bitfinex wrapper client.

    Args:
        api_key: Bitfinex API key
        api_secret: Bitfinex API secret

    Returns:
        BitfinexClientWrapper instance with POST_ONLY enforcement
    """
    return BitfinexClientWrapper(api_key, api_secret)
