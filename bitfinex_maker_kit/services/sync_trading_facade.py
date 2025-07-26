"""
Synchronous trading facade for Maker-Kit.

Provides a synchronous interface that wraps the async trading service,
enabling clean sync/async separation for CLI commands.
"""

import asyncio
import logging
from typing import Any

from ..domain.amount import Amount
from ..domain.order_id import OrderId
from ..domain.price import Price
from ..domain.symbol import Symbol
from .async_trading_service import AsyncTradingService

logger = logging.getLogger(__name__)


class SyncTradingFacade:
    """
    Synchronous facade for async trading operations.

    Wraps AsyncTradingService to provide synchronous interface
    for CLI commands while maintaining clean async/sync boundaries.
    """

    def __init__(self, async_service: AsyncTradingService):
        """
        Initialize sync trading facade.

        Args:
            async_service: Async trading service to wrap
        """
        self.async_service = async_service
        self._event_loop: asyncio.AbstractEventLoop | None = None
        logger.info("Sync trading facade initialized")

    def _get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop for sync operations."""
        if self._event_loop is None or self._event_loop.is_closed():
            try:
                # Try to get the current event loop
                self._event_loop = asyncio.get_event_loop()
                if self._event_loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                # Create new event loop if none exists
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)

        return self._event_loop

    def _run_async(self, coro: Any) -> Any:
        """Run async coroutine in sync context."""
        loop = self._get_or_create_event_loop()

        try:
            # If loop is already running (in async context), use run_until_complete
            if loop.is_running():
                # Create a new task and wait for it
                task = asyncio.create_task(coro)
                return loop.run_until_complete(task)
            else:
                # If loop is not running, use run_until_complete directly
                return loop.run_until_complete(coro)
        except RuntimeError as e:
            # Handle "This event loop is already running" error
            if "already running" in str(e):
                # Use asyncio.run() in a new loop
                return asyncio.run(coro)
            else:
                raise

    def place_order(
        self, symbol: Symbol, side: str, amount: Amount, price: Price | None = None
    ) -> tuple[bool, Any]:
        """
        Place a single order synchronously.

        Args:
            symbol: Trading symbol
            side: Order side ('buy' or 'sell')
            amount: Order amount
            price: Order price (None for market order)

        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            result = self._run_async(
                self.async_service.place_order_async(symbol, side, amount, price)
            )
            return result if isinstance(result, tuple) else (True, result)
        except Exception as e:
            logger.error(f"Error in sync place_order: {e}")
            return False, str(e)

    def cancel_order(self, order_id: OrderId) -> tuple[bool, Any]:
        """
        Cancel an order by ID synchronously.

        Args:
            order_id: Order ID to cancel

        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            result = self._run_async(self.async_service.cancel_order_async(order_id))
            return result if isinstance(result, tuple) else (True, result)
        except Exception as e:
            logger.error(f"Error in sync cancel_order: {e}")
            return False, str(e)

    def get_orders(self, symbol: Symbol | None = None) -> list[Any]:
        """
        Get active orders synchronously.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of active orders
        """
        try:
            result = self._run_async(self.async_service.get_orders_async(symbol))
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in sync get_orders: {e}")
            return []

    def get_wallet_balances(self) -> list[Any]:
        """
        Get wallet balances synchronously.

        Returns:
            List of wallet balance entries
        """
        try:
            result = self._run_async(self.async_service.get_wallet_balances_async())
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in sync get_wallet_balances: {e}")
            return []

    def get_ticker(self, symbol: Symbol) -> dict[str, Any] | None:
        """
        Get ticker data for a symbol synchronously.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data or None if error
        """
        try:
            result = self._run_async(self.async_service.get_ticker_async(symbol))
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in sync get_ticker: {e}")
            return None

    def update_order(
        self,
        order_id: OrderId,
        price: Price | None = None,
        amount: Amount | None = None,
        delta: Amount | None = None,
        use_cancel_recreate: bool = False,
    ) -> tuple[bool, Any]:
        """
        Update an existing order synchronously.

        Args:
            order_id: Order ID to update
            price: New price (optional)
            amount: New amount (optional)
            delta: Amount delta (optional)
            use_cancel_recreate: Force cancel-and-recreate strategy

        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            result = self._run_async(
                self.async_service.update_order_async(
                    order_id, price, amount, delta, use_cancel_recreate
                )
            )
            return result if isinstance(result, tuple) else (True, result)
        except Exception as e:
            logger.error(f"Error in sync update_order: {e}")
            return False, str(e)

    def batch_place_orders(
        self, orders: list[tuple[Symbol, str, Amount, Price | None]]
    ) -> list[tuple[bool, Any]]:
        """
        Place multiple orders synchronously (with async concurrency).

        Args:
            orders: List of (symbol, side, amount, price) tuples

        Returns:
            List of (success, result) tuples
        """
        try:
            result = self._run_async(self.async_service.batch_place_orders_async(orders))
            return (
                result if isinstance(result, list) else [(False, "Unknown error") for _ in orders]
            )
        except Exception as e:
            logger.error(f"Error in sync batch_place_orders: {e}")
            return [(False, str(e)) for _ in orders]

    def batch_cancel_orders(self, order_ids: list[OrderId]) -> list[tuple[bool, Any]]:
        """
        Cancel multiple orders synchronously (with async concurrency).

        Args:
            order_ids: List of order IDs to cancel

        Returns:
            List of (success, result) tuples
        """
        try:
            result = self._run_async(self.async_service.batch_cancel_orders_async(order_ids))
            return (
                result
                if isinstance(result, list)
                else [(False, "Unknown error") for _ in order_ids]
            )
        except Exception as e:
            logger.error(f"Error in sync batch_cancel_orders: {e}")
            return [(False, str(e)) for _ in order_ids]

    def start_websocket(self) -> bool:
        """
        Start WebSocket connection synchronously.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self._run_async(self.async_service.start_websocket_async())
            return bool(result)
        except Exception as e:
            logger.error(f"Error in sync start_websocket: {e}")
            return False

    def stop_websocket(self) -> bool:
        """
        Stop WebSocket connection synchronously.

        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            result = self._run_async(self.async_service.stop_websocket_async())
            return bool(result)
        except Exception as e:
            logger.error(f"Error in sync stop_websocket: {e}")
            return False

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self.async_service.is_websocket_connected()

    def validate_order_parameters(
        self, symbol: Symbol, side: str, amount: Amount, price: Price | None = None
    ) -> tuple[bool, str]:
        """
        Validate order parameters synchronously.

        Args:
            symbol: Trading symbol
            side: Order side
            amount: Order amount
            price: Order price (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic validation
            if side not in ["buy", "sell"]:
                return False, f"Invalid side: {side}"

            if amount.value <= 0:
                return False, f"Amount must be positive: {amount}"

            if price and price.value <= 0:
                return False, f"Price must be positive: {price}"

            # Symbol format validation
            if not str(symbol).startswith("t"):
                return False, f"Symbol must start with 't': {symbol}"

            logger.debug("Order parameters validated successfully")
            return True, ""

        except Exception as e:
            logger.error(f"Error validating order parameters: {e}")
            return False, str(e)

    def get_order_statistics(self) -> dict[str, Any]:
        """
        Get statistics about current orders synchronously.

        Returns:
            Dictionary with order statistics
        """
        try:
            orders = self.get_orders()

            stats = {
                "total_orders": len(orders),
                "buy_orders": len([o for o in orders if float(o.amount) > 0]),
                "sell_orders": len([o for o in orders if float(o.amount) < 0]),
                "symbols": list({o.symbol for o in orders}),
            }

            logger.debug(f"Generated order statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error generating order statistics: {e}")
            return {"total_orders": 0, "buy_orders": 0, "sell_orders": 0, "symbols": []}

    def get_client(self) -> Any:
        """Get the underlying Bitfinex client."""
        return self.async_service.get_client()

    def get_config(self) -> dict[str, Any]:
        """Get the service configuration."""
        return self.async_service.get_config()

    def close(self) -> None:
        """Close the sync trading facade and clean up resources."""
        try:
            # Close async service
            self._run_async(self.async_service.close_async())

            # Close event loop if we created it
            if self._event_loop and not self._event_loop.is_closed():
                self._event_loop.close()

            logger.info("Sync trading facade closed")

        except Exception as e:
            logger.error(f"Error closing sync trading facade: {e}")

    def __enter__(self) -> "SyncTradingFacade":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit."""
        self.close()


def create_sync_facade_from_container(container: Any) -> SyncTradingFacade:
    """
    Create sync trading facade from service container.

    Args:
        container: Service container

    Returns:
        Configured SyncTradingFacade
    """
    # Get or create async service
    client = container.create_bitfinex_client()
    config = container.get_config()

    async_service = AsyncTradingService(client, config)

    return SyncTradingFacade(async_service)
