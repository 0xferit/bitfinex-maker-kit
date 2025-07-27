"""
Real-time market data service - NO CACHING for trading safety.

SAFETY FIRST: Always fetches live data from API to prevent stale data
trading losses. Never caches market data, prices, or order states.
ALL ORDERS ARE POST_ONLY for predictable execution and market making.
"""

import logging
from typing import Any

from ..domain.symbol import Symbol
from ..services.container import ServiceContainer

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Real-time market data service - SAFETY FIRST: NO CACHING.

    CRITICAL: Always fetches live data to prevent stale data trading losses.
    Every market data request goes directly to API for maximum data freshness.
    Performance cost is acceptable for trading safety and accuracy.

    TRADING SAFETY PRINCIPLES:
    - Never cache market data (stale prices cause losses)
    - Always fetch live ticker/orderbook/balances
    - All orders are POST_ONLY (architecturally enforced)
    - Real-time data is paramount for safe trading
    """

    def __init__(self, container: ServiceContainer):
        """
        Initialize market data service.

        Args:
            container: Service container for dependency injection
        """
        self.container = container
        self._client: Any = None

        # Performance tracking (API calls only - no cache metrics)
        self._api_calls = 0

        logger.info("MarketDataService initialized - SAFETY MODE: No caching, live data only")

    def _get_client(self) -> Any:
        """Get trading client from container."""
        if self._client is None:
            trading_service = self.container.create_trading_service()
            self._client = trading_service.get_client()
        return self._client

    async def get_ticker(self, symbol: Symbol) -> dict[str, Any]:
        """
        Get LIVE ticker data - NO CACHING for trading safety.

        SAFETY: Always fetches fresh price data to prevent stale price trading.

        Args:
            symbol: Trading symbol

        Returns:
            Live ticker data from API

        Raises:
            Exception: If API call fails
        """
        client = self._get_client()
        try:
            logger.debug(f"Fetching LIVE ticker for {symbol} - no cache for safety")
            ticker = client.get_ticker(str(symbol))
            self._api_calls += 1

            return {
                "symbol": str(symbol),
                "bid": float(ticker.bid),
                "ask": float(ticker.ask),
                "last_price": float(ticker.last_price),
                "bid_size": float(ticker.bid_size),
                "ask_size": float(ticker.ask_size),
                "timestamp": ticker.timestamp if hasattr(ticker, "timestamp") else None,
            }
        except Exception as e:
            logger.error(f"Error fetching LIVE ticker for {symbol}: {e}")
            raise

    async def get_orderbook(self, symbol: Symbol, precision: str = "P0") -> dict[str, Any]:
        """
        Get LIVE orderbook data - NO CACHING for trading safety.

        SAFETY: Always fetches fresh orderbook to prevent stale depth trading.

        Args:
            symbol: Trading symbol
            precision: Orderbook precision level

        Returns:
            Live orderbook data from API

        Raises:
            Exception: If API call fails
        """
        client = self._get_client()
        try:
            logger.debug(f"Fetching LIVE orderbook for {symbol} - no cache for safety")
            orderbook = client.get_orderbook(str(symbol), precision=precision)
            self._api_calls += 1

            return {
                "symbol": str(symbol),
                "precision": precision,
                "bids": [[float(bid.price), float(bid.amount)] for bid in orderbook.bids[:20]],
                "asks": [[float(ask.price), float(ask.amount)] for ask in orderbook.asks[:20]],
                "timestamp": orderbook.timestamp if hasattr(orderbook, "timestamp") else None,
            }
        except Exception as e:
            logger.error(f"Error fetching LIVE orderbook for {symbol}: {e}")
            raise

    async def get_account_balance(self) -> list[dict[str, Any]]:
        """
        Get LIVE account balance - NO CACHING for trading safety.

        SAFETY: Always fetches fresh balance to prevent overdraft/insufficient funds.

        Returns:
            Live account balance from API

        Raises:
            Exception: If API call fails
        """
        client = self._get_client()
        try:
            logger.debug("Fetching LIVE account balance - no cache for safety")
            wallets = client.get_wallets()
            self._api_calls += 1

            return [
                {
                    "currency": wallet.currency,
                    "type": wallet.type,
                    "balance": float(wallet.balance),
                    "available": float(wallet.available),
                }
                for wallet in wallets
            ]
        except Exception as e:
            logger.error(f"Error fetching LIVE account balance: {e}")
            raise

    async def get_recent_trades(self, symbol: Symbol, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get LIVE recent trades - NO CACHING for trading safety.

        SAFETY: Always fetches fresh trade data for accurate market analysis.

        Args:
            symbol: Trading symbol
            limit: Number of recent trades to fetch

        Returns:
            Live recent trades from API

        Raises:
            Exception: If API call fails
        """
        client = self._get_client()
        try:
            logger.debug(f"Fetching LIVE trades for {symbol} - no cache for safety")
            trades = client.get_trades(str(symbol), limit=limit)
            self._api_calls += 1

            return [
                {
                    "price": float(trade.price),
                    "amount": float(trade.amount),
                    "timestamp": trade.timestamp if hasattr(trade, "timestamp") else None,
                    "side": "buy" if float(trade.amount) > 0 else "sell",
                }
                for trade in trades
            ]
        except Exception as e:
            logger.error(f"Error fetching LIVE trades for {symbol}: {e}")
            raise

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get service performance statistics.

        Note: Only tracks API calls - no cache metrics for safety compliance.
        """
        return {
            "api_calls_total": self._api_calls,
            "caching_disabled": True,  # Safety feature
            "data_freshness": "live_only",  # Safety guarantee
            "trading_safety_mode": "enabled",
        }

    async def cleanup(self) -> None:
        """Clean up service resources."""
        logger.info("MarketDataService cleanup complete - no cache to clear (safety mode)")


def create_market_data_service(container: ServiceContainer) -> MarketDataService:
    """
    Create market data service with SAFETY FIRST configuration.

    Args:
        container: Service container for dependency injection

    Returns:
        MarketDataService configured for maximum safety (no caching)
    """
    return MarketDataService(container)
