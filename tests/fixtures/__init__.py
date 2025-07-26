"""
Test fixtures package for Maker-Kit.

Provides comprehensive test data fixtures, mock objects,
and testing utilities organized by category.
"""

from .api_responses import (
    APIResponseFixture,
    APIResponseFixtures,
    ErrorResponseFixture,
    ResponseStatus,
    SuccessResponseFixture,
    WebSocketMessageFixture,
)
from .market_data import (
    MarketDataFixtures,
    OrderBookFixture,
    TickerDataFixture,
    TradeHistoryFixture,
)
from .performance_data import (
    BenchmarkFixture,
    MetricsFixture,
    PerformanceFixtures,
    ProfileDataFixture,
)
from .trading_data import (
    BalanceFixture,
    OrderFixture,
    OrderSide,
    OrderStatus,
    PortfolioFixture,
    TradingFixtures,
)

__all__ = [
    # API response fixtures
    "APIResponseFixture",
    "APIResponseFixtures",
    "BalanceFixture",
    "BenchmarkFixture",
    "ErrorResponseFixture",
    # Market data fixtures
    "MarketDataFixtures",
    "MetricsFixture",
    "OrderBookFixture",
    "OrderFixture",
    "OrderSide",
    "OrderStatus",
    # Performance data fixtures
    "PerformanceFixtures",
    "PortfolioFixture",
    "ProfileDataFixture",
    "ResponseStatus",
    "SuccessResponseFixture",
    "TickerDataFixture",
    "TradeHistoryFixture",
    # Trading data fixtures
    "TradingFixtures",
    "WebSocketMessageFixture",
]
