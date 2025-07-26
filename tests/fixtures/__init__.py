"""
Test fixtures package for Maker-Kit.

Provides comprehensive test data fixtures, mock objects,
and testing utilities organized by category.
"""

from .api_responses import *
from .market_data import *
from .performance_data import *
from .trading_data import *

__all__ = [
    # API response fixtures
    "APIResponseFixtures",
    "BalanceFixture",
    "BenchmarkFixture",
    "ErrorResponseFixture",
    # Market data fixtures
    "MarketDataFixtures",
    "MetricsFixture",
    "OrderBookFixture",
    "OrderFixture",
    # Performance data fixtures
    "PerformanceFixtures",
    "PortfolioFixture",
    "ProfileDataFixture",
    "SuccessResponseFixture",
    "TickerDataFixture",
    "TradeHistoryFixture",
    # Trading data fixtures
    "TradingFixtures",
    "WebSocketMessageFixture",
]
