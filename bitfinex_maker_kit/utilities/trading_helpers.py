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


def calculate_mid_price(bid: float, ask: float) -> float:
    """Calculate mid price from bid and ask."""
    return (bid + ask) / 2.0


def calculate_spread(bid: float, ask: float, as_percentage: bool = False) -> float:
    """Calculate spread between bid and ask."""
    spread = ask - bid
    if as_percentage:
        mid_price = calculate_mid_price(bid, ask)
        return (spread / mid_price) * 100 if mid_price > 0 else 0.0

    # Round to avoid floating point precision issues
    return round(spread, 8)


def generate_levels(
    center_price: float, spread_pct: float, levels: int
) -> tuple[list[float], list[float]]:
    """Generate bid and ask levels for market making."""
    half_spread = (spread_pct / 100) * center_price / 2
    step_size = half_spread / levels

    bid_levels = []
    ask_levels = []

    for i in range(1, levels + 1):
        bid_price = center_price - (step_size * i)
        ask_price = center_price + (step_size * i)
        bid_levels.append(bid_price)
        ask_levels.append(ask_price)

    return bid_levels, ask_levels


def calculate_order_total(price: float, amount: float, fee_rate: float = 0.0) -> float:
    """Calculate total value of an order including fees."""
    base_total = price * amount
    fee = abs(base_total) * fee_rate
    return base_total + (fee if amount > 0 else -fee)
