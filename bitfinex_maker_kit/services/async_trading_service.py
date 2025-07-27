"""
Async trading service for Maker-Kit.

Provides clean async/await interface for all trading operations,
replacing complex threading patterns with proper async architecture.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from ..bitfinex_client import BitfinexClientWrapper
from ..domain.amount import Amount
from ..domain.order_id import OrderId
from ..domain.price import Price
from ..domain.symbol import Symbol

logger = logging.getLogger(__name__)


class AsyncTradingService:
    """
    Async service for all trading operations.

    Provides clean async/await interface for trading operations while
    maintaining all safety guarantees and POST_ONLY enforcement.
    """

    def __init__(self, client: BitfinexClientWrapper, config: dict[str, Any]):
        """
        Initialize async trading service.

        Args:
            client: Configured Bitfinex client wrapper
            config: Application configuration
        """
        self.client = client
        self.config = config
        self._connection_lock = asyncio.Lock()
        self._websocket_connected = False
        self._event_handlers: dict[str, list[Callable]] = {}
        logger.info("Async trading service initialized")

    async def place_order_async(
        self, symbol: Symbol, side: str, amount: Amount, price: Price | None = None
    ) -> tuple[bool, Any]:
        """
        Place a single order asynchronously with POST_ONLY enforcement.

        Args:
            symbol: Trading symbol
            side: Order side ('buy' or 'sell')
            amount: Order amount
            price: Order price (None for market order)

        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            logger.info(f"Placing {side} order async: {amount} {symbol} @ {price}")

            # Convert domain objects to client format
            symbol_str = str(symbol)
            amount_float = float(amount.value)
            price_float = float(price.value) if price else None

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._place_order_sync, symbol_str, side, amount_float, price_float
            )

            return result

        except Exception as e:
            logger.error(f"Error placing order async: {e}")
            return False, str(e)

    def _place_order_sync(
        self, symbol: str, side: str, amount: float, price: float | None
    ) -> tuple[bool, Any]:
        """Synchronous order placement wrapper."""
        from ..utilities.orders import submit_order

        try:
            # Fixed parameter order: (symbol, side, amount, price)
            result = submit_order(symbol=symbol, side=side, amount=amount, price=price)
            return True, result
        except Exception as e:
            logger.error(f"Error in synchronous order placement: {e}")
            return False, str(e)

    async def cancel_order_async(self, order_id: OrderId) -> tuple[bool, Any]:
        """
        Cancel an order by ID asynchronously.

        Args:
            order_id: Order ID to cancel

        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            logger.info(f"Cancelling order async: {order_id}")

            # Handle placeholder orders
            if order_id.is_placeholder_id():
                logger.warning(f"Cannot cancel placeholder order: {order_id}")
                return False, "Cannot cancel placeholder order"

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def cancel_order_wrapper() -> Any:
                order_id_int = order_id.to_int()
                return self.client.cancel_order(order_id_int)

            result = await loop.run_in_executor(None, cancel_order_wrapper)

            logger.info(f"Order cancellation result: {result}")
            return True, result

        except Exception as e:
            logger.error(f"Error cancelling order async {order_id}: {e}")
            return False, str(e)

    async def get_orders_async(self, symbol: Symbol | None = None) -> list[Any]:
        """
        Get active orders asynchronously, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of active orders
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def get_orders_wrapper() -> list[Any]:
                return self.client.get_orders()

            orders = await loop.run_in_executor(None, get_orders_wrapper)

            logger.debug(f"Retrieved {len(orders)} orders async")
            return list(orders)

        except Exception as e:
            logger.error(f"Error retrieving orders async: {e}")
            return []

    async def get_wallet_balances_async(self) -> list[Any]:
        """
        Get wallet balances asynchronously.

        Returns:
            List of wallet balance entries
        """
        try:
            loop = asyncio.get_event_loop()

            def get_wallets_wrapper() -> list[Any]:
                result = self.client.get_wallets()
                return list(result) if result is not None else []

            balances = await loop.run_in_executor(None, get_wallets_wrapper)

            logger.debug(f"Retrieved {len(balances)} wallet entries async")
            return list(balances)

        except Exception as e:
            logger.error(f"Error retrieving wallet balances async: {e}")
            return []

    async def get_ticker_async(self, symbol: Symbol) -> dict[str, float] | None:
        """
        Get ticker data for a symbol asynchronously.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data or None if error
        """
        try:
            from ..utilities.market_data import get_ticker_data

            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, get_ticker_data, str(symbol))

            if ticker:
                logger.debug(f"Retrieved ticker async for {symbol}")
            else:
                logger.warning(f"No ticker data async for {symbol}")

            if ticker:
                # Return the ticker data directly since get_ticker_data returns appropriate type
                return ticker
            return None

        except Exception as e:
            logger.error(f"Error retrieving ticker async for {symbol}: {e}")
            return None

    async def update_order_async(
        self,
        order_id: OrderId,
        price: Price | None = None,
        amount: Amount | None = None,
        delta: Amount | None = None,
        use_cancel_recreate: bool = False,
    ) -> tuple[bool, Any]:
        """
        Update an existing order asynchronously.

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
            logger.info(f"Updating order async: {order_id}")

            # Handle placeholder orders
            if order_id.is_placeholder_id():
                logger.warning(f"Cannot update placeholder order: {order_id}")
                return False, "Cannot update placeholder order"

            # Convert domain objects to client format
            price_float = float(price.value) if price else None
            amount_float = float(amount.value) if amount else None
            delta_float = float(delta.value) if delta else None

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()

            def update_order_wrapper() -> Any:
                order_id_int = order_id.to_int()
                return self.client.update_order(
                    order_id=order_id_int,
                    price=price_float,
                    amount=amount_float,
                    delta=delta_float,
                    use_cancel_recreate=use_cancel_recreate,
                )

            result = await loop.run_in_executor(None, update_order_wrapper)

            # Client returns dict result, convert to tuple format
            if result and "status" in result and result["status"] == "SUCCESS":
                logger.info(f"Order updated successfully async: {result}")
                return True, result
            else:
                logger.error(f"Order update failed async: {result}")
                return False, result

        except Exception as e:
            logger.error(f"Error updating order async {order_id}: {e}")
            return False, str(e)

    async def start_websocket_async(self) -> bool:
        """
        Start WebSocket connection asynchronously.

        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self._websocket_connected:
                logger.warning("WebSocket already connected")
                return True

            try:
                logger.info("Starting WebSocket connection async")

                # Start WebSocket in background task
                await self.client.wss.start()
                self._websocket_connected = True

                logger.info("WebSocket connection established async")
                return True

            except Exception as e:
                logger.error(f"Error starting WebSocket async: {e}")
                return False

    async def stop_websocket_async(self) -> bool:
        """
        Stop WebSocket connection asynchronously.

        Returns:
            True if disconnection successful, False otherwise
        """
        async with self._connection_lock:
            if not self._websocket_connected:
                logger.warning("WebSocket not connected")
                return True

            try:
                logger.info("Stopping WebSocket connection async")

                await self.client.wss.close()
                self._websocket_connected = False

                logger.info("WebSocket connection closed async")
                return True

            except Exception as e:
                logger.error(f"Error stopping WebSocket async: {e}")
                return False

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Register an async event handler.

        Args:
            event_type: Type of event to handle
            handler: Async handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        self._event_handlers[event_type].append(handler)
        logger.debug(f"Registered async event handler for {event_type}")

    def unregister_event_handler(self, event_type: str, handler: Callable) -> None:
        """
        Unregister an async event handler.

        Args:
            event_type: Type of event
            handler: Handler function to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.debug(f"Unregistered async event handler for {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type {event_type}")

    async def emit_event(self, event_type: str, event_data: Any) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        if event_type not in self._event_handlers:
            return

        handlers = self._event_handlers[event_type]
        if not handlers:
            return

        # Run all handlers concurrently
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(event_data))
            else:
                # Wrap sync handlers in async task
                tasks.append(asyncio.create_task(self._run_sync_handler(handler, event_data)))

        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error in async event handlers for {event_type}: {e}")

    async def _run_sync_handler(self, handler: Callable, event_data: Any) -> None:
        """Run synchronous handler in executor."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, handler, event_data)

    async def batch_place_orders_async(
        self, orders: list[tuple[Symbol, str, Amount, Price | None]]
    ) -> list[tuple[bool, Any]]:
        """
        Place multiple orders concurrently.

        Args:
            orders: List of (symbol, side, amount, price) tuples

        Returns:
            List of (success, result) tuples
        """
        if not orders:
            return []

        logger.info(f"Placing {len(orders)} orders async concurrently")

        # Create tasks for concurrent execution
        tasks = []
        for symbol, side, amount, price in orders:
            task = self.place_order_async(symbol, side, amount, price)
            tasks.append(task)

        # Execute all orders concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results: list[tuple[bool, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Order {i + 1} failed with exception: {result}")
                processed_results.append((False, str(result)))
            elif isinstance(result, tuple) and len(result) == 2:
                processed_results.append(result)
            else:
                processed_results.append((False, str(result)))

        successful_orders = sum(1 for success, _ in processed_results if success)
        logger.info(f"Batch order placement complete: {successful_orders}/{len(orders)} successful")

        return processed_results

    async def batch_cancel_orders_async(self, order_ids: list[OrderId]) -> list[tuple[bool, Any]]:
        """
        Cancel multiple orders concurrently.

        Args:
            order_ids: List of order IDs to cancel

        Returns:
            List of (success, result) tuples
        """
        if not order_ids:
            return []

        logger.info(f"Cancelling {len(order_ids)} orders async concurrently")

        # Create tasks for concurrent execution
        tasks = []
        for order_id in order_ids:
            task = self.cancel_order_async(order_id)
            tasks.append(task)

        # Execute all cancellations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results: list[tuple[bool, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Cancellation {i + 1} failed with exception: {result}")
                processed_results.append((False, str(result)))
            elif isinstance(result, tuple) and len(result) == 2:
                processed_results.append(result)
            else:
                processed_results.append((False, str(result)))

        successful_cancellations = sum(1 for success, _ in processed_results if success)
        logger.info(
            f"Batch cancellation complete: {successful_cancellations}/{len(order_ids)} successful"
        )

        return processed_results

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._websocket_connected

    def get_client(self) -> BitfinexClientWrapper:
        """Get the underlying Bitfinex client."""
        return self.client

    def get_config(self) -> dict[str, Any]:
        """Get the service configuration."""
        return self.config

    async def close_async(self) -> None:
        """Close the async trading service and clean up resources."""
        try:
            # Stop WebSocket if connected
            if self._websocket_connected:
                await self.stop_websocket_async()

            # Clear event handlers
            self._event_handlers.clear()

            logger.info("Async trading service closed")

        except Exception as e:
            logger.error(f"Error closing async trading service: {e}")
