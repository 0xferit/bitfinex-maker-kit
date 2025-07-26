"""
Utilities package for the Bitfinex CLI tool.

This package contains all utility modules including authentication,
market data, constants, API client wrapper, and general utilities.
"""

from ..bitfinex_client import Notification, Order, create_wrapper_client
from .auth import (
    create_client,
    get_credentials,
    test_api_connection,
    test_comprehensive,
    test_websocket_connection,
)
from .console import (
    confirm_action,
    print_error,
    print_info,
    print_section_header,
    print_success,
    print_table_separator,
    print_warning,
)
from .constants import (
    DEFAULT_LEVELS,
    DEFAULT_ORDER_SIZE,
    DEFAULT_SPREAD_PCT,
    DEFAULT_SYMBOL,
    OrderSide,
    OrderSubmissionError,
    OrderType,
    ValidationError,
)
from .formatters import format_amount, format_percentage, format_price, format_timestamp
from .market_data import (
    get_ticker_data,
    resolve_center_price,
    suggest_price_centers,
    validate_center_price,
)
from .orders import _extract_order_id, cancel_order, submit_order, update_order
from .trading_helpers import calculate_distance_from_center, get_side_from_amount, normalize_side
from .validators import safe_float_convert, validate_non_empty_string, validate_positive_number

__all__ = [
    "DEFAULT_LEVELS",
    "DEFAULT_ORDER_SIZE",
    "DEFAULT_SPREAD_PCT",
    # Constants
    "DEFAULT_SYMBOL",
    "Notification",
    "Order",
    "OrderSide",
    "OrderSubmissionError",
    "OrderType",
    "ValidationError",
    "_extract_order_id",
    "calculate_distance_from_center",
    "cancel_order",
    "confirm_action",
    # Auth utilities
    "create_client",
    # Client utilities
    "create_wrapper_client",
    "format_amount",
    "format_percentage",
    # Formatting utilities
    "format_price",
    "format_timestamp",
    "get_credentials",
    "get_side_from_amount",
    # Market data utilities
    "get_ticker_data",
    # Trading helpers
    "normalize_side",
    "print_error",
    "print_info",
    "print_section_header",
    # Console utilities
    "print_success",
    "print_table_separator",
    "print_warning",
    "resolve_center_price",
    "safe_float_convert",
    # Order utilities
    "submit_order",
    "suggest_price_centers",
    "test_api_connection",
    "test_comprehensive",
    "test_websocket_connection",
    "update_order",
    "validate_center_price",
    "validate_non_empty_string",
    # Validation utilities
    "validate_positive_number",
]
