"""
Order fetching utilities.

Extracted from BitfinexClientWrapper to provide focused order retrieval
with proper error handling and caching capabilities.
"""

import logging
from typing import Any

from ..utilities.constants import OrderSubmissionError

logger = logging.getLogger(__name__)


class OrderFetcher:
    """
    Handles fetching and caching of orders from the exchange.

    Provides centralized order retrieval logic that was previously
    embedded in larger methods.
    """

    def __init__(self, client: Any):
        """
        Initialize with a client instance.

        Args:
            client: BitfinexClientWrapper instance
        """
        self.client = client
        self._cached_orders = None
        self._cache_timestamp = 0.0  # Store as float for precision
        self._cache_ttl = 30  # 30 seconds cache TTL

    def fetch_order_by_id(self, order_id: int, use_cache: bool = True) -> Any:
        """
        Fetch a specific order by its ID.

        Args:
            order_id: ID of the order to fetch
            use_cache: Whether to use cached orders if available

        Returns:
            Order object from API

        Raises:
            OrderSubmissionError: If fetching fails
            ValueError: If order is not found
        """
        logger.debug(f"Fetching order {order_id}")

        try:
            orders = self.fetch_all_orders(use_cache=use_cache)

            for order in orders:
                if order.id == order_id:
                    logger.debug(f"Found order {order_id}")
                    return order

            # Order not found
            logger.warning(f"Order {order_id} not found in {len(orders)} active orders")
            raise ValueError(f"Order {order_id} not found")

        except OrderSubmissionError:
            # Re-raise API errors
            raise
        except ValueError as e:
            if "not found" in str(e).lower():
                # Re-raise not found errors
                raise
            else:
                # Wrap other ValueError as API error
                raise OrderSubmissionError(f"Failed to fetch order {order_id}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching order {order_id}: {e}")
            raise OrderSubmissionError(f"Failed to fetch order {order_id}: {e}") from e

    def fetch_all_orders(self, use_cache: bool = True) -> list[Any]:
        """
        Fetch all active orders from the exchange.

        Args:
            use_cache: Whether to use cached orders if available and fresh

        Returns:
            List of order objects from API

        Raises:
            OrderSubmissionError: If fetching fails
        """
        import time

        current_time = time.time()

        # Check cache if requested and valid
        if (
            use_cache
            and self._cached_orders is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            logger.debug(f"Using cached orders ({len(self._cached_orders)} orders)")
            return self._cached_orders

        # Fetch fresh orders from API
        logger.debug("Fetching fresh orders from API")

        try:
            orders = self.client.get_orders()

            # Update cache
            self._cached_orders = orders
            self._cache_timestamp = current_time  # Store full precision timestamp

            logger.debug(f"Fetched {len(orders)} orders from API")
            return list(orders)  # Ensure return type matches annotation

        except Exception as e:
            logger.error(f"Failed to fetch orders from API: {e}")

            # Clear cache on error
            self._cached_orders = None
            self._cache_timestamp = 0.0  # Consistent with initialization

            raise OrderSubmissionError(f"Failed to fetch orders: {e}") from e

    def invalidate_cache(self) -> None:
        """Invalidate the order cache to force fresh fetch on next request."""
        logger.debug("Invalidating order cache")
        self._cached_orders = None
        self._cache_timestamp = 0.0  # Consistent with initialization

    def get_cache_info(self) -> dict[str, Any]:
        """
        Get information about the current cache state.

        Returns:
            Dict with cache information
        """
        import time

        current_time = time.time()
        age = current_time - self._cache_timestamp if self._cache_timestamp > 0 else None

        return {
            "has_cached_orders": self._cached_orders is not None,
            "cached_order_count": len(self._cached_orders) if self._cached_orders else 0,
            "cache_age_seconds": age,
            "cache_is_fresh": age is not None and age < self._cache_ttl,
            "cache_ttl_seconds": self._cache_ttl,
        }

    def set_cache_ttl(self, ttl_seconds: int) -> None:
        """
        Set the cache time-to-live.

        Args:
            ttl_seconds: Cache TTL in seconds
        """
        if ttl_seconds < 0:
            raise ValueError("Cache TTL must be non-negative")

        self._cache_ttl = ttl_seconds
        logger.debug(f"Cache TTL set to {ttl_seconds} seconds")

    def prefetch_orders(self) -> None:
        """Prefetch orders to warm up the cache."""
        logger.debug("Prefetching orders for cache")
        try:
            self.fetch_all_orders(use_cache=False)
            logger.debug("Orders prefetched successfully")
        except Exception as e:
            logger.warning(f"Failed to prefetch orders: {e}")

    def get_orders_by_symbol(self, symbol: str, use_cache: bool = True) -> list[Any]:
        """
        Get all orders for a specific symbol.

        Args:
            symbol: Trading symbol to filter by
            use_cache: Whether to use cached orders

        Returns:
            List of orders for the specified symbol
        """
        logger.debug(f"Fetching orders for symbol {symbol}")

        all_orders = self.fetch_all_orders(use_cache=use_cache)
        symbol_orders = [order for order in all_orders if order.symbol == symbol]

        logger.debug(f"Found {len(symbol_orders)} orders for symbol {symbol}")
        return symbol_orders
