"""
Formatting utilities for displaying prices, amounts, timestamps, and percentages.

This module provides consistent formatting functions used across the CLI for
displaying trading data in a user-friendly format.
"""

from datetime import datetime

from .constants import AMOUNT_PRECISION


def format_price(price: float | str | None, decimals: int | None = None) -> str:
    """Format price for display."""
    if price is None or price == "MARKET":
        return "MARKET"

    try:
        price_float = float(price)

        # If decimals is specified, use it; otherwise use appropriate default
        precision = decimals if decimals is not None else 2

        return f"{price_float:,.{precision}f}"
    except (ValueError, TypeError):
        return str(price)


def format_amount(amount: float | str, decimals: int | None = None) -> str:
    """Format amount for display."""
    try:
        amount_float = float(amount)
        precision = decimals if decimals is not None else AMOUNT_PRECISION
        return f"{amount_float:.{precision}f}"
    except (ValueError, TypeError):
        return str(amount)


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage for display."""
    percentage = value * 100
    return f"{percentage:.{decimals}f}%"


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount for display."""
    try:
        symbol = "$" if currency == "USD" else "€" if currency == "EUR" else currency
        formatted = f"{abs(amount):,.2f}"
        sign = "-" if amount < 0 else ""
        return f"{sign}{symbol}{formatted}"
    except (ValueError, TypeError):
        return str(amount)


def format_order_summary(order: dict) -> str:
    """Format order information for display."""
    try:
        order_id = order.get("id", "N/A")
        symbol = order.get("symbol", "N/A")
        side = order.get("side", "N/A")
        amount = order.get("amount", 0)
        price = order.get("price", "MARKET")
        status = order.get("status", "N/A")

        formatted_amount = format_amount(amount)
        formatted_price = format_price(price)

        return (
            f"Order {order_id}: {side} {formatted_amount} {symbol} @ {formatted_price} [{status}]"
        )
    except (KeyError, TypeError, ValueError):
        return f"Order {order.get('id', 'N/A')}: Invalid order data"


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
