"""
Market data caching utilities for Maker-Kit.

Provides specialized caching for market data with intelligent cache strategies,
real-time data handling, and performance optimizations.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from ..domain.symbol import Symbol
from ..services.cache_service import CacheService, create_cache_service

logger = logging.getLogger(__name__)


class MarketDataType(Enum):
    """Types of market data for caching."""

    TICKER = "ticker"
    ORDER_BOOK = "orderbook"
    TRADES = "trades"
    CANDLES = "candles"
    ACCOUNT_BALANCE = "balance"


@dataclass
class MarketDataCacheConfig:
    """Configuration for market data caching."""

    ticker_ttl: float = 10.0  # 10 seconds for ticker data
    orderbook_ttl: float = 5.0  # 5 seconds for order book
    trades_ttl: float = 30.0  # 30 seconds for trade history
    candles_ttl: float = 60.0  # 1 minute for candle data
    balance_ttl: float = 30.0  # 30 seconds for account balance

    # Cache warming settings
    enable_warming: bool = True
    warming_symbols: list[str] | None = None
    warming_interval: float = 300.0  # 5 minutes

    # Performance settings
    max_cache_size: int = 5000
    batch_fetch_size: int = 10

    def __post_init__(self) -> None:
        """Initialize default warming symbols."""
        if self.warming_symbols is None:
            self.warming_symbols = ["tBTCUSD", "tETHUSD", "tPNKUSD"]


class MarketDataCache:
    """
    Specialized cache for market data with intelligent strategies.

    Provides optimized caching for different types of market data
    with appropriate TTLs and cache warming strategies.
    """

    def __init__(
        self,
        cache_service: CacheService | None = None,
        config: MarketDataCacheConfig | None = None,
    ):
        """
        Initialize market data cache.

        Args:
            cache_service: Cache service instance
            config: Cache configuration
        """
        self.config = config or MarketDataCacheConfig()
        self.cache_service = cache_service or create_cache_service(
            max_size=self.config.max_cache_size, default_ttl=self.config.ticker_ttl
        )

        # Data providers (will be injected)
        self._data_providers: dict[MarketDataType, Callable[..., Any]] = {}

        # Setup cache warming if enabled
        if self.config.enable_warming:
            self._setup_cache_warming()

    def register_data_provider(
        self, data_type: MarketDataType, provider: Callable[..., Any]
    ) -> None:
        """
        Register a data provider for a specific market data type.

        Args:
            data_type: Type of market data
            provider: Async function to fetch the data
        """
        self._data_providers[data_type] = provider
        logger.info(f"Registered data provider for {data_type.value}")

    def _get_ttl_for_type(self, data_type: MarketDataType) -> float:
        """Get appropriate TTL for market data type."""
        ttl_map = {
            MarketDataType.TICKER: self.config.ticker_ttl,
            MarketDataType.ORDER_BOOK: self.config.orderbook_ttl,
            MarketDataType.TRADES: self.config.trades_ttl,
            MarketDataType.CANDLES: self.config.candles_ttl,
            MarketDataType.ACCOUNT_BALANCE: self.config.balance_ttl,
        }
        return ttl_map.get(data_type, self.config.ticker_ttl)

    def _make_cache_key(
        self, data_type: MarketDataType, symbol: str | None = None, **params: Any
    ) -> str:
        """
        Create cache key for market data.

        Args:
            data_type: Type of market data
            symbol: Trading symbol (if applicable)
            **params: Additional parameters for the key

        Returns:
            Cache key string
        """
        key_parts = [data_type.value]

        if symbol:
            key_parts.append(symbol)

        # Add sorted parameters
        if params:
            param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_parts.append(param_str)

        return ":".join(key_parts)

    async def get_ticker(
        self, symbol: Symbol, force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """
        Get ticker data with caching.

        Args:
            symbol: Trading symbol
            force_refresh: Force fetch from provider (bypass cache)

        Returns:
            Ticker data or None if not available
        """
        symbol_str = str(symbol)
        cache_key = self._make_cache_key(MarketDataType.TICKER, symbol_str)

        if force_refresh:
            await self.cache_service.delete("market_data", cache_key)

        async def fetch_ticker() -> dict[str, Any]:
            if MarketDataType.TICKER not in self._data_providers:
                raise ValueError("No ticker data provider registered")

            provider = self._data_providers[MarketDataType.TICKER]
            return await provider(symbol_str)  # type: ignore[no-any-return]

        ttl = self._get_ttl_for_type(MarketDataType.TICKER)
        result = await self.cache_service.get_or_set("market_data", cache_key, fetch_ticker, ttl)
        return cast(dict[str, Any] | None, result)

    async def get_order_book(
        self, symbol: Symbol, precision: str = "P0", force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """
        Get order book data with caching.

        Args:
            symbol: Trading symbol
            precision: Order book precision
            force_refresh: Force fetch from provider

        Returns:
            Order book data or None if not available
        """
        symbol_str = str(symbol)
        cache_key = self._make_cache_key(MarketDataType.ORDER_BOOK, symbol_str, precision=precision)

        if force_refresh:
            await self.cache_service.delete("market_data", cache_key)

        async def fetch_orderbook() -> dict[str, Any]:
            if MarketDataType.ORDER_BOOK not in self._data_providers:
                raise ValueError("No order book data provider registered")

            provider = self._data_providers[MarketDataType.ORDER_BOOK]
            return await provider(symbol_str, precision)  # type: ignore[no-any-return]

        ttl = self._get_ttl_for_type(MarketDataType.ORDER_BOOK)
        result = await self.cache_service.get_or_set("market_data", cache_key, fetch_orderbook, ttl)
        return cast(dict[str, Any] | None, result)

    async def get_account_balance(self, force_refresh: bool = False) -> list[dict[str, Any]] | None:
        """
        Get account balance with caching.

        Args:
            force_refresh: Force fetch from provider

        Returns:
            Account balance data or None if not available
        """
        cache_key = self._make_cache_key(MarketDataType.ACCOUNT_BALANCE)

        if force_refresh:
            await self.cache_service.delete("market_data", cache_key)

        async def fetch_balance() -> list[dict[str, Any]]:
            if MarketDataType.ACCOUNT_BALANCE not in self._data_providers:
                raise ValueError("No account balance data provider registered")

            provider = self._data_providers[MarketDataType.ACCOUNT_BALANCE]
            return await provider()  # type: ignore[no-any-return]

        ttl = self._get_ttl_for_type(MarketDataType.ACCOUNT_BALANCE)
        result = await self.cache_service.get_or_set("market_data", cache_key, fetch_balance, ttl)
        return cast(list[dict[str, Any]] | None, result)

    async def get_recent_trades(
        self, symbol: Symbol, limit: int = 50, force_refresh: bool = False
    ) -> list[dict[str, Any]] | None:
        """
        Get recent trades with caching.

        Args:
            symbol: Trading symbol
            limit: Number of trades to fetch
            force_refresh: Force fetch from provider

        Returns:
            Recent trades data or None if not available
        """
        symbol_str = str(symbol)
        cache_key = self._make_cache_key(MarketDataType.TRADES, symbol_str, limit=limit)

        if force_refresh:
            await self.cache_service.delete("market_data", cache_key)

        async def fetch_trades() -> list[dict[str, Any]]:
            if MarketDataType.TRADES not in self._data_providers:
                raise ValueError("No trades data provider registered")

            provider = self._data_providers[MarketDataType.TRADES]
            return await provider(symbol_str, limit)  # type: ignore[no-any-return]

        ttl = self._get_ttl_for_type(MarketDataType.TRADES)
        result = await self.cache_service.get_or_set("market_data", cache_key, fetch_trades, ttl)
        return cast(list[dict[str, Any]] | None, result)

    async def batch_get_tickers(
        self, symbols: list[Symbol], force_refresh: bool = False
    ) -> dict[str, dict[str, Any] | None]:
        """
        Get multiple tickers efficiently.

        Args:
            symbols: List of trading symbols
            force_refresh: Force fetch from provider

        Returns:
            Dictionary mapping symbol strings to ticker data
        """
        results: dict[str, dict[str, Any] | None] = {}

        # Process in batches for better performance
        batch_size = self.config.batch_fetch_size
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]

            # Fetch batch concurrently
            tasks = [self.get_ticker(symbol, force_refresh) for symbol in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch results
            for symbol, result in zip(batch, batch_results, strict=False):
                symbol_str = str(symbol)
                if isinstance(result, BaseException):
                    logger.error(f"Error fetching ticker for {symbol_str}: {result}")
                    results[symbol_str] = None
                else:
                    results[symbol_str] = result

        return results

    async def invalidate_symbol_data(self, symbol: Symbol) -> int:
        """
        Invalidate all cached data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Number of cache entries invalidated
        """
        symbol_str = str(symbol)
        invalidated = 0

        # Invalidate all data types for this symbol
        for data_type in MarketDataType:
            if data_type == MarketDataType.ACCOUNT_BALANCE:
                continue  # Not symbol-specific

            cache_key = self._make_cache_key(data_type, symbol_str)
            if await self.cache_service.delete("market_data", cache_key):
                invalidated += 1

        logger.info(f"Invalidated {invalidated} cache entries for {symbol_str}")
        return invalidated

    async def warm_cache_for_symbols(self, symbols: list[Symbol]) -> None:
        """
        Warm cache for specified symbols.

        Args:
            symbols: List of symbols to warm
        """
        logger.info(f"Warming cache for {len(symbols)} symbols")

        # Warm ticker data for all symbols
        await self.batch_get_tickers(symbols)

        # Warm order book data for high-priority symbols
        priority_symbols = symbols[:5]  # Limit to first 5
        orderbook_tasks = [self.get_order_book(symbol) for symbol in priority_symbols]

        await asyncio.gather(*orderbook_tasks, return_exceptions=True)

        logger.info(f"Cache warming completed for {len(symbols)} symbols")

    def _setup_cache_warming(self) -> None:
        """Setup cache warming for configured symbols."""
        if not self.config.warming_symbols:
            return

        async def warming_callback(key: str) -> dict[str, Any] | None:
            """Callback for cache warming."""
            # Parse key to determine data type and symbol
            parts = key.split(":")
            if len(parts) < 2:
                return None

            data_type_str, symbol_str = parts[0], parts[1]

            try:
                data_type = MarketDataType(data_type_str)
                symbol = Symbol(symbol_str)

                if data_type == MarketDataType.TICKER:
                    return await self.get_ticker(symbol, force_refresh=True)
                elif data_type == MarketDataType.ORDER_BOOK:
                    return await self.get_order_book(symbol, force_refresh=True)

            except (ValueError, Exception) as e:
                logger.error(f"Error in warming callback for {key}: {e}")

            return None

        # Register warming callback
        self.cache_service.register_warming_callback("market_data", warming_callback)

        # Start background warming
        warming_keys = []
        for symbol_str in self.config.warming_symbols:
            warming_keys.append(f"ticker:{symbol_str}")
            warming_keys.append(f"orderbook:{symbol_str}")

        # This would be called in an async context
        logger.info(f"Cache warming configured for {len(self.config.warming_symbols)} symbols")

    async def start_background_warming(self) -> None:
        """Start background cache warming."""
        if not self.config.enable_warming or not self.config.warming_symbols:
            return

        warming_keys = []
        for symbol_str in self.config.warming_symbols:
            warming_keys.append(f"ticker:{symbol_str}")
            warming_keys.append(f"orderbook:{symbol_str}")

        await self.cache_service.start_background_warming(
            "market_data", warming_keys, self.config.warming_interval
        )

        logger.info("Background cache warming started")

    async def stop_background_warming(self) -> None:
        """Stop background cache warming."""
        await self.cache_service.stop_background_warming("market_data")
        logger.info("Background cache warming stopped")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        base_stats = self.cache_service.get_stats()

        return {
            "hit_ratio": base_stats.hit_ratio,
            "hits": base_stats.hits,
            "misses": base_stats.misses,
            "evictions": base_stats.evictions,
            "size": base_stats.size,
            "config": {
                "ticker_ttl": self.config.ticker_ttl,
                "orderbook_ttl": self.config.orderbook_ttl,
                "warming_enabled": self.config.enable_warming,
                "warming_symbols": len(self.config.warming_symbols)
                if self.config.warming_symbols
                else 0,
            },
        }

    async def cleanup(self) -> None:
        """Clean up market data cache resources."""
        await self.stop_background_warming()
        await self.cache_service.cleanup()
        logger.info("Market data cache cleaned up")


def create_market_data_cache(config: MarketDataCacheConfig | None = None) -> MarketDataCache:
    """
    Create market data cache with default configuration.

    Args:
        config: Optional cache configuration

    Returns:
        Configured MarketDataCache instance
    """
    if config is None:
        config = MarketDataCacheConfig()

    cache_service = create_cache_service(
        max_size=config.max_cache_size, default_ttl=config.ticker_ttl
    )

    return MarketDataCache(cache_service, config)
