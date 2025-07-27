"""
Order update strategies for BitfinexClientWrapper.

This package implements the Strategy pattern for different order update approaches:
- WebSocket atomic updates (safer, preferred)
- Cancel-and-recreate updates (fallback, riskier)

This separation allows for clean testing and future extension of update methods.
"""

from .base import OrderUpdateRequest, OrderUpdateResult, OrderUpdateStrategy
from .cancel_recreate_strategy import CancelRecreateStrategy
from .strategy_factory import UpdateStrategyFactory
from .websocket_strategy import WebSocketUpdateStrategy

__all__ = [
    "CancelRecreateStrategy",
    "OrderUpdateRequest",
    "OrderUpdateResult",
    "OrderUpdateStrategy",
    "UpdateStrategyFactory",
    "WebSocketUpdateStrategy",
]
