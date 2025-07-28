"""
Constants and configuration values for Bitfinex CLI Tool.

This module centralizes all magic numbers, default values, and configuration
constants to improve maintainability and reduce duplication.
"""

from enum import Enum
from typing import Final

# API Constants
POST_ONLY_FLAG: Final[int] = 4096
DEFAULT_SYMBOL: Final[str] = "tBTCUSD"

# Default Trading Parameters
DEFAULT_LEVELS: Final[int] = 3
DEFAULT_SPREAD_PCT: Final[float] = 1.0
DEFAULT_ORDER_SIZE: Final[float] = 10.0

# Market Data and Validation
MIN_ORDER_SPACING_PCT: Final[float] = 0.05  # 0.05% minimum spacing between orders
REPLENISH_INTERVAL_SECONDS: Final[int] = 30

# Display Constants
EMOJI_SUCCESS: Final[str] = "✅"
EMOJI_ERROR: Final[str] = "❌"
EMOJI_WARNING: Final[str] = "⚠️"
EMOJI_INFO: Final[str] = "📋"
EMOJI_MONEY: Final[str] = "💰"
EMOJI_ROCKET: Final[str] = "🚀"
EMOJI_STOP: Final[str] = "🛑"
EMOJI_ROBOT: Final[str] = "🤖"


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"

    def __str__(self) -> str:
        return self.value.upper()


class OrderType(Enum):
    """Order type enumeration."""

    LIMIT = "EXCHANGE LIMIT"
    MARKET = "EXCHANGE MARKET"


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class OrderSubmissionError(Exception):
    """Custom exception for order submission errors."""

    pass


# Price formatting configuration
PRICE_PRECISION: Final[int] = 6
AMOUNT_PRECISION: Final[int] = 6
