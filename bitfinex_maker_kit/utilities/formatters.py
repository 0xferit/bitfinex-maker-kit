"""
Formatting utilities for displaying prices, amounts, timestamps, and percentages.

This module provides consistent formatting functions used across the CLI for
displaying trading data in a user-friendly format.
"""

from datetime import datetime

from .constants import AMOUNT_PRECISION, PRICE_PRECISION


def format_price(price: float | str | None) -> str:
    """Format price for display."""
    if price is None or price == "MARKET":
        return "MARKET"

    try:
        price_float = float(price)
        return f"${price_float:.{PRICE_PRECISION}f}"
    except (ValueError, TypeError):
        return str(price)


def format_amount(amount: float | str) -> str:
    """Format amount for display."""
    try:
        amount_float = float(amount)
        return f"{abs(amount_float):.{AMOUNT_PRECISION}f}"
    except (ValueError, TypeError):
        return str(amount)


def format_percentage(value: float, precision: int = 3) -> str:
    """Format percentage for display."""
    return f"{value:+.{precision}f}%"


def format_timestamp(timestamp: int | float | None) -> str:
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
