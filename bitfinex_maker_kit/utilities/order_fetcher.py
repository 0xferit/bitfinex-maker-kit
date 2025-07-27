"""
Order fetching utilities to eliminate duplication in order retrieval logic.

This module provides reusable functions for fetching and filtering orders,
replacing duplicated patterns found across command modules.
"""

from collections.abc import Callable
from typing import Any

from .client_factory import get_client
from .console import print_operation_error


def fetch_all_orders() -> list | None:
    """
    Fetch all active orders with error handling.

    Returns:
        List of orders or None if fetch fails
    """
    try:
        client = get_client()
        return client.get_orders()
    except Exception as e:
        print_operation_error("get orders", e)
        return None


def fetch_orders_by_symbol(symbol: str) -> list | None:
    """
    Fetch all orders for a specific symbol.

    Args:
        symbol: Trading symbol to filter by

    Returns:
        List of orders for the symbol or None if fetch fails
    """
    all_orders = fetch_all_orders()
    if all_orders is None:
        return None

    return [order for order in all_orders if order.symbol == symbol]


def fetch_orders_by_criteria(
    symbol: str | None = None,
    size: float | None = None,
    direction: str | None = None,
    price_below: float | None = None,
    price_above: float | None = None,
    filter_func: Callable | None = None,
) -> list | None:
    """
    Fetch orders matching multiple criteria.

    Args:
        symbol: Filter by trading symbol
        size: Filter by order size (absolute value)
        direction: Filter by direction ("buy" or "sell")
        price_below: Filter orders with price below this value
        price_above: Filter orders with price above this value
        filter_func: Custom filter function taking an order and returning bool

    Returns:
        List of matching orders or None if fetch fails
    """
    all_orders = fetch_all_orders()
    if all_orders is None:
        return None

    filtered_orders = all_orders

    # Apply symbol filter
    if symbol:
        filtered_orders = [o for o in filtered_orders if o.symbol == symbol]

    # Apply size filter
    if size is not None:
        filtered_orders = [o for o in filtered_orders if abs(float(o.amount)) == size]

    # Apply direction filter
    if direction:
        if direction.lower() == "buy":
            filtered_orders = [o for o in filtered_orders if float(o.amount) > 0]
        elif direction.lower() == "sell":
            filtered_orders = [o for o in filtered_orders if float(o.amount) < 0]

    # Apply price filters
    if price_below is not None:
        filtered_orders = [o for o in filtered_orders if o.price and float(o.price) < price_below]

    if price_above is not None:
        filtered_orders = [o for o in filtered_orders if o.price and float(o.price) > price_above]

    # Apply custom filter function
    if filter_func:
        filtered_orders = [o for o in filtered_orders if filter_func(o)]

    return filtered_orders


def get_order_ids(orders: list) -> list[int]:
    """
    Extract order IDs from a list of orders.

    Args:
        orders: List of order objects

    Returns:
        List of order IDs
    """
    return [order.id for order in orders]


def group_orders_by_symbol(orders: list) -> dict:
    """
    Group orders by trading symbol.

    Args:
        orders: List of order objects

    Returns:
        Dictionary mapping symbols to lists of orders
    """
    grouped: dict[str, list[Any]] = {}
    for order in orders:
        symbol = order.symbol
        if symbol not in grouped:
            grouped[symbol] = []
        grouped[symbol].append(order)
    return grouped


def separate_buy_sell_orders(orders: list) -> tuple:
    """
    Separate orders into buy and sell lists.

    Args:
        orders: List of order objects

    Returns:
        Tuple of (buy_orders, sell_orders)
    """
    buy_orders = [o for o in orders if float(o.amount) > 0]
    sell_orders = [o for o in orders if float(o.amount) < 0]
    return buy_orders, sell_orders


def count_orders_by_type(orders: list) -> dict:
    """
    Count orders by their type.

    Args:
        orders: List of order objects

    Returns:
        Dictionary mapping order types to counts
    """
    counts: dict[str, int] = {}
    for order in orders:
        order_type = order.order_type
        counts[order_type] = counts.get(order_type, 0) + 1
    return counts
