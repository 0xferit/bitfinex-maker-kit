"""
Utilities package for the Bitfinex CLI tool.

This package contains all utility modules including authentication,
market data, constants, API client wrapper, and general utilities.
"""

from .auth import create_client, test_api_connection, test_websocket_connection, test_comprehensive, get_credentials
from ..bitfinex_client import create_wrapper_client, Order, Notification
from .constants import (
    DEFAULT_SYMBOL, DEFAULT_LEVELS, DEFAULT_SPREAD_PCT, DEFAULT_ORDER_SIZE,
    OrderSide, OrderType, ValidationError, OrderSubmissionError
)
from .market_data import (
    get_ticker_data, validate_center_price, resolve_center_price,
    suggest_price_centers
)
from .formatters import format_price, format_amount, format_timestamp, format_percentage
from .console import (
    print_success, print_error, print_warning, print_info, 
    print_section_header, print_table_separator, confirm_action
)
from .trading_helpers import (
    normalize_side, get_side_from_amount, calculate_distance_from_center
)
from .validators import validate_positive_number, validate_non_empty_string, safe_float_convert
from .orders import submit_order, cancel_order, update_order, _extract_order_id

__all__ = [
    # Auth utilities
    'create_client',
    'test_api_connection', 
    'test_websocket_connection',
    'test_comprehensive',
    'get_credentials',
    
    # Client utilities  
    'create_wrapper_client',
    'Order',
    'Notification',
    
    # Constants
    'DEFAULT_SYMBOL',
    'DEFAULT_LEVELS', 
    'DEFAULT_SPREAD_PCT',
    'DEFAULT_ORDER_SIZE',
    'OrderSide',
    'OrderType',
    'ValidationError',
    'OrderSubmissionError',
    
    # Market data utilities
    'get_ticker_data',
    'validate_center_price',
    'resolve_center_price',
    'suggest_price_centers',
    
    # Formatting utilities
    'format_price',
    'format_amount',
    'format_timestamp',
    'format_percentage',
    
    # Console utilities
    'print_success',
    'print_error',
    'print_warning',
    'print_info',
    'print_section_header',
    'print_table_separator',
    'confirm_action',
    
    # Trading helpers
    'normalize_side',
    'get_side_from_amount',
    'calculate_distance_from_center',
    
    # Validation utilities
    'validate_positive_number',
    'validate_non_empty_string',
    'safe_float_convert',
    
    # Order utilities
    'submit_order',
    'cancel_order',
    'update_order',
    '_extract_order_id',
] 