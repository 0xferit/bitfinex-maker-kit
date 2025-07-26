"""
Dependency injection container for Maker-Kit.

Centralizes the creation and management of all service dependencies,
replacing scattered create_client() calls with proper dependency injection.
"""

import logging
from typing import Any, TypeVar

from ..bitfinex_client import BitfinexClientWrapper, create_wrapper_client
from ..utilities.auth import get_credentials
from .trading_service import TradingService

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """
    Dependency injection container for managing service lifecycle.

    Provides factory methods for creating and caching service instances,
    enabling proper dependency injection throughout the application.
    """

    def __init__(self) -> None:
        """Initialize the service container."""
        self._instances: dict[type, Any] = {}
        self._singletons: dict[type, Any] = {}
        self._config: dict[str, Any] | None = None

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the container with application settings."""
        self._config = config
        logger.debug(f"Container configured with {len(config)} settings")

    def get_config(self) -> dict[str, Any]:
        """Get the container configuration."""
        if self._config is None:
            self._config = {}
        return self._config

    def register_singleton(self, service_type: type[T], instance: T) -> None:
        """Register a singleton instance for a service type."""
        self._singletons[service_type] = instance
        logger.debug(f"Registered singleton for {service_type.__name__}")

    def get_singleton(self, service_type: type[T]) -> T | None:
        """Get a singleton instance if registered."""
        return self._singletons.get(service_type)

    def create_bitfinex_client(self) -> BitfinexClientWrapper:
        """
        Create a Bitfinex API client with proper configuration.

        Returns:
            Configured BitfinexClientWrapper instance

        Raises:
            ValueError: If credentials are not available
        """
        # Check if we have a singleton
        singleton = self.get_singleton(BitfinexClientWrapper)
        if singleton:
            return singleton

        try:
            # Get credentials from environment/config
            api_key, api_secret = get_credentials()
            if not api_key or not api_secret:
                raise ValueError("Bitfinex API credentials not found in environment")

            # Create client with wrapper
            client = create_wrapper_client(api_key, api_secret)

            logger.info("Created Bitfinex client successfully")
            return client

        except Exception as e:
            logger.error(f"Failed to create Bitfinex client: {e}")
            raise ValueError(f"Failed to initialize Bitfinex client: {e}") from e

    def create_trading_service(self) -> TradingService:
        """
        Create the main trading service with all dependencies.

        Returns:
            Configured TradingService instance
        """
        # Check for singleton
        singleton = self.get_singleton(TradingService)
        if singleton:
            return singleton

        try:
            # Create dependencies
            client = self.create_bitfinex_client()
            config = self.get_config()

            # Create trading service
            trading_service = TradingService(client, config)

            logger.info("Created trading service successfully")
            return trading_service

        except Exception as e:
            logger.error(f"Failed to create trading service: {e}")
            raise ValueError(f"Failed to initialize trading service: {e}") from e

    def create_order_manager(
        self,
        symbol: str,
        levels: int,
        spread_pct: float,
        size: float,
        side_filter: str | None = None,
    ) -> Any:
        """
        Create an order manager with injected dependencies.

        Args:
            symbol: Trading symbol
            levels: Number of price levels
            spread_pct: Spread percentage
            size: Order size
            side_filter: Optional side filter

        Returns:
            Configured OrderManager instance
        """
        from ..core.order_manager import OrderManager

        try:
            client = self.create_bitfinex_client()
            return OrderManager(symbol, levels, spread_pct, size, side_filter, client)
        except Exception as e:
            logger.error(f"Failed to create order manager: {e}")
            raise ValueError(f"Failed to create order manager: {e}") from e

    def create_websocket_handler(self, order_manager: Any) -> Any:
        """
        Create WebSocket event handler with injected dependencies.

        Args:
            order_manager: OrderManager instance

        Returns:
            Configured WebSocketEventHandler instance
        """
        from ..websocket.event_handler import WebSocketEventHandler

        try:
            client = self.create_bitfinex_client()
            return WebSocketEventHandler(order_manager, client)
        except Exception as e:
            logger.error(f"Failed to create WebSocket handler: {e}")
            raise ValueError(f"Failed to create WebSocket handler: {e}") from e

    def create_market_maker_ui(
        self,
        symbol: str,
        center_price: float,
        levels: int,
        spread_pct: float,
        size: float,
        side_filter: str | None = None,
    ) -> Any:
        """
        Create market maker UI with configuration.

        Args:
            symbol: Trading symbol
            center_price: Center price for orders
            levels: Number of price levels
            spread_pct: Spread percentage
            size: Order size
            side_filter: Optional side filter

        Returns:
            Configured MarketMakerUI instance
        """
        from ..ui.market_maker_console import MarketMakerUI

        return MarketMakerUI(symbol, center_price, levels, spread_pct, size, side_filter)

    def create_order_generator(
        self, levels: int, spread_pct: float, size: float, side_filter: str | None = None
    ) -> Any:
        """
        Create order generator with configuration.

        Args:
            levels: Number of price levels
            spread_pct: Spread percentage
            size: Order size
            side_filter: Optional side filter

        Returns:
            Configured OrderGenerator instance
        """
        from ..strategies.order_generator import OrderGenerator

        return OrderGenerator(levels, spread_pct, size, side_filter)

    def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            # Close any WebSocket connections
            client = self.get_singleton(BitfinexClientWrapper)
            if client and hasattr(client, "wss"):
                # Note: Actual cleanup would need async context
                pass

            # Clear instances
            self._instances.clear()
            self._singletons.clear()

            logger.info("Service container cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during container cleanup: {e}")


# Global container instance
_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    """
    Get the global service container instance.

    Returns:
        Global ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def configure_container(config: dict[str, Any]) -> ServiceContainer:
    """
    Configure the global service container.

    Args:
        config: Configuration dictionary

    Returns:
        Configured ServiceContainer instance
    """
    container = get_container()
    container.configure(config)
    return container


def reset_container() -> None:
    """Reset the global container (mainly for testing)."""
    global _container
    if _container:
        _container.cleanup()
    _container = None
