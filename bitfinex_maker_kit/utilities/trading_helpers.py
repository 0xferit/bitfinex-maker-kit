"""
Trading-specific helper utilities.

This module provides utility functions for order management, price calculations,
and trading logic used across various trading commands.
"""

from .constants import OrderSide


def normalize_side(side: str | OrderSide) -> OrderSide:
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


def calculate_distance_from_center(price: float, center: float) -> float:
    """Calculate percentage distance from center price."""
    if center == 0:
        return 0.0
    return ((price - center) / center) * 100
