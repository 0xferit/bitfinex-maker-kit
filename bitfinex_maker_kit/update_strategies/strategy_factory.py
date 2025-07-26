"""
Factory for creating order update strategies.

Provides a centralized way to create and configure update strategies
based on user preferences and system capabilities.
"""

import logging

from .base import OrderUpdateRequest, OrderUpdateStrategy
from .cancel_recreate_strategy import CancelRecreateStrategy
from .websocket_strategy import WebSocketUpdateStrategy

logger = logging.getLogger(__name__)


class UpdateStrategyFactory:
    """
    Factory class for creating order update strategies.

    Handles strategy selection based on user preferences and system
    capabilities, with intelligent fallback logic.
    """

    def __init__(self) -> None:
        """Initialize the factory with available strategies."""
        self._websocket_strategy = WebSocketUpdateStrategy()
        self._cancel_recreate_strategy = CancelRecreateStrategy()

    def create_strategy(self, use_cancel_recreate: bool = False) -> OrderUpdateStrategy:
        """
        Create an appropriate update strategy.

        Args:
            use_cancel_recreate: If True, prefer cancel-recreate strategy

        Returns:
            Selected update strategy
        """
        if use_cancel_recreate:
            logger.info("Using cancel-and-recreate strategy (user requested)")
            return self._cancel_recreate_strategy
        else:
            logger.info("Using WebSocket atomic update strategy (safer default)")
            return self._websocket_strategy

    def get_recommended_strategy(
        self, request: OrderUpdateRequest, client_capabilities: dict | None = None
    ) -> OrderUpdateStrategy:
        """
        Get the recommended strategy based on request and client capabilities.

        Args:
            request: The update request
            client_capabilities: Optional dict of client capabilities

        Returns:
            Recommended update strategy
        """
        # For now, always recommend WebSocket atomic update as it's safer
        # In the future, this could be enhanced with more sophisticated logic
        # based on client capabilities, network conditions, etc.

        logger.debug(f"Recommending WebSocket atomic strategy for order {request.order_id}")
        return self._websocket_strategy

    def get_fallback_strategy(
        self, failed_strategy: OrderUpdateStrategy
    ) -> OrderUpdateStrategy | None:
        """
        Get a fallback strategy when the primary strategy fails.

        Args:
            failed_strategy: The strategy that failed

        Returns:
            Fallback strategy, or None if no fallback available
        """
        if isinstance(failed_strategy, WebSocketUpdateStrategy):
            logger.warning("WebSocket strategy failed, suggesting cancel-recreate as fallback")
            return self._cancel_recreate_strategy
        else:
            # No fallback for cancel-recreate (it's already the fallback)
            logger.error("Cancel-recreate strategy failed, no further fallback available")
            return None

    def get_all_strategies(self) -> list[OrderUpdateStrategy]:
        """Get all available strategies."""
        return [self._websocket_strategy, self._cancel_recreate_strategy]

    def get_strategy_info(self) -> dict[str, dict[str, str]]:
        """Get information about all available strategies."""
        return {
            "websocket_atomic": {
                "name": self._websocket_strategy.get_strategy_name(),
                "risk_level": self._websocket_strategy.get_risk_level(),
                "description": "Atomic updates via REST API or WebSocket (safer)",
            },
            "cancel_recreate": {
                "name": self._cancel_recreate_strategy.get_strategy_name(),
                "risk_level": self._cancel_recreate_strategy.get_risk_level(),
                "description": "Cancel existing order and create new one (riskier)",
            },
        }
