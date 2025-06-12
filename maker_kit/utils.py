"""
Utility functions for Bitfinex CLI Tool.

This module contains common formatting, display, and helper functions
used across multiple modules to reduce code duplication.
"""

from datetime import datetime
from typing import Union, List, Optional
from .constants import (
    PRICE_PRECISION, AMOUNT_PRECISION, EMOJI_SUCCESS, EMOJI_ERROR, 
    EMOJI_WARNING, EMOJI_INFO, OrderSide
)


def format_price(price: Union[float, str, None]) -> str:
    """Format price for display."""
    if price is None or price == "MARKET":
        return "MARKET"
    
    try:
        price_float = float(price)
        return f"${price_float:.{PRICE_PRECISION}f}"
    except (ValueError, TypeError):
        return str(price)


def format_amount(amount: Union[float, str]) -> str:
    """Format amount for display."""
    try:
        amount_float = float(amount)
        return f"{abs(amount_float):.{AMOUNT_PRECISION}f}"
    except (ValueError, TypeError):
        return str(amount)


def format_percentage(value: float, precision: int = 3) -> str:
    """Format percentage for display."""
    return f"{value:+.{precision}f}%"


def format_timestamp(timestamp: Union[int, float, None]) -> str:
    """Format timestamp to readable date."""
    if timestamp is None:
        return "Unknown"
    
    try:
        # Convert from milliseconds to seconds if needed
        if timestamp > 1e12:  # Likely milliseconds
            timestamp = timestamp / 1000
        
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return "Invalid Date"


def normalize_side(side: Union[str, OrderSide]) -> OrderSide:
    """Normalize order side to OrderSide enum."""
    if isinstance(side, OrderSide):
        return side
    
    side_str = side.lower().strip()
    if side_str == "buy":
        return OrderSide.BUY
    elif side_str == "sell":
        return OrderSide.SELL
    else:
        raise ValueError(f"Invalid order side: {side}. Must be 'buy' or 'sell'")


def get_side_from_amount(amount: float) -> OrderSide:
    """Determine order side from amount (positive=buy, negative=sell)."""
    return OrderSide.BUY if amount > 0 else OrderSide.SELL


def print_success(message: str) -> None:
    """Print success message with emoji."""
    print(f"{EMOJI_SUCCESS} {message}")


def print_error(message: str) -> None:
    """Print error message with emoji."""
    print(f"{EMOJI_ERROR} {message}")


def print_warning(message: str) -> None:
    """Print warning message with emoji."""
    print(f"{EMOJI_WARNING} {message}")


def print_info(message: str) -> None:
    """Print info message with emoji."""
    print(f"{EMOJI_INFO} {message}")


def print_section_header(title: str, width: int = 60) -> None:
    """Print formatted section header."""
    print(f"\n{title}")
    print("=" * width)


def print_table_separator(width: int = 80) -> None:
    """Print table separator line."""
    print("─" * width)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        prompt: The question to ask
        default: Default value if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    suffix = " (y/N)" if not default else " (Y/n)"
    response = input(f"{prompt}{suffix}: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def calculate_distance_from_center(price: float, center: float) -> float:
    """Calculate percentage distance from center price."""
    if center == 0:
        return 0.0
    return ((price - center) / center) * 100


def validate_positive_number(value: Union[int, float], name: str) -> None:
    """Validate that a number is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_empty_string(value: str, name: str) -> None:
    """Validate that a string is not empty."""
    if not value or not value.strip():
        raise ValueError(f"{name} cannot be empty")


def safe_float_convert(value: Union[str, int, float], default: float = 0.0) -> float:
    """Safely convert value to float with fallback."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default 