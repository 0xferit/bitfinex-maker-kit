"""
Shared protocol types for structural typing across services and clients.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..utilities.constants import OrderSide


@runtime_checkable
class TradingClient(Protocol):
    """Minimal client contract used by trading services.

    Structural typing keeps the architecture simple and testable, allowing
    real clients and mocks to be used interchangeably as long as they
    implement the required methods.
    """

    def submit_order(
        self, symbol: str, side: str | OrderSide, amount: float, price: float | None = None
    ) -> Any: ...

    def cancel_order(self, order_id: int) -> Any: ...

    def get_orders(self) -> list[Any]: ...

    def get_wallets(self) -> Any: ...

    def get_ticker(self, symbol: str) -> Any: ...
    def get_trades(self, symbol: str, limit: int = 1) -> Any: ...

    def update_order(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
        use_cancel_recreate: bool = False,
    ) -> Any: ...

    @property
    def wss(self) -> Any: ...
