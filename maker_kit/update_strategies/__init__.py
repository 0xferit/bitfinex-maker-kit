"""
Order update strategies for BitfinexClientWrapper.

This package implements the Strategy pattern for different order update approaches:
- WebSocket atomic updates (safer, preferred)
- Cancel-and-recreate updates (fallback, riskier)

This separation allows for clean testing and future extension of update methods.
"""

from .base import OrderUpdateStrategy, OrderUpdateRequest, OrderUpdateResult
from .websocket_strategy import WebSocketUpdateStrategy
from .cancel_recreate_strategy import CancelRecreateStrategy
from .strategy_factory import UpdateStrategyFactory

__all__ = [
    'OrderUpdateStrategy',
    'OrderUpdateRequest', 
    'OrderUpdateResult',
    'WebSocketUpdateStrategy',
    'CancelRecreateStrategy',
    'UpdateStrategyFactory'
]