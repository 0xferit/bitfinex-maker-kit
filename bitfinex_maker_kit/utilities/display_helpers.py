"""
Display helper utilities to eliminate duplication in formatting and display logic.

This module provides reusable functions for displaying orders, tables, and
other common output patterns used across command modules.
"""

from typing import Any

from .formatters import format_price, format_timestamp


def format_order_table_row(order: Any, show_created: bool = True) -> str:
    """
    Format a single order as a table row.

    Args:
        order: Order object to format
        show_created: Whether to include created timestamp

    Returns:
        Formatted string for table row
    """
    order_id = order.id
    amount = float(order.amount)
    side = "BUY" if amount > 0 else "SELL"
    amount_abs = abs(amount)
    order_type = order.order_type
    price = order.price if order.price else "MARKET"

    # Format price
    price_str = format_price(price) if price != "MARKET" else "MARKET"

    if show_created:
        created_timestamp = order.mts_create
        created_date = format_timestamp(created_timestamp)
        return f"{order_id:<12} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15} {created_date:<20}"
    else:
        return f"{order_id:<12} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15}"


def display_order_table(orders: list, title: str = "Orders", show_created: bool = True) -> None:
    """
    Display orders in a formatted table.

    Args:
        orders: List of order objects
        title: Table title
        show_created: Whether to show created timestamp column
    """
    if not orders:
        print(f"No {title.lower()} found")
        return

    print(f"\n🔹 {title}:")
    print("─" * 80)

    # Table header
    if show_created:
        print(f"{'ID':<12} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15} {'Created':<20}")
    else:
        print(f"{'ID':<12} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15}")

    print("─" * 80)

    # Sort orders by price (lowest to highest), with market orders at the end
    def sort_key(order: Any) -> float:
        if order.price is None:
            return float("inf")  # Market orders go to the end
        return float(order.price)

    sorted_orders = sorted(orders, key=sort_key)

    # Display rows
    for order in sorted_orders:
        print(format_order_table_row(order, show_created))

    print()


def display_orders_by_symbol(orders: list, show_created: bool = True) -> None:
    """
    Display orders grouped by symbol in formatted tables.

    Args:
        orders: List of order objects
        show_created: Whether to show created timestamp column
    """
    if not orders:
        print("No orders found")
        return

    # Group orders by symbol
    orders_by_symbol: dict[str, list[Any]] = {}
    for order in orders:
        symbol = order.symbol
        if symbol not in orders_by_symbol:
            orders_by_symbol[symbol] = []
        orders_by_symbol[symbol].append(order)

    # Display each symbol group
    for symbol, symbol_orders in orders_by_symbol.items():
        display_order_table(symbol_orders, f"{symbol} Orders", show_created)


def format_summary_stats(orders: list) -> dict[str, Any]:
    """
    Calculate summary statistics for a list of orders.

    Args:
        orders: List of order objects

    Returns:
        Dictionary containing summary statistics
    """
    if not orders:
        return {
            "total_count": 0,
            "buy_count": 0,
            "sell_count": 0,
            "total_buy_amount": 0,
            "total_sell_amount": 0,
            "total_buy_value": 0,
            "total_sell_value": 0,
            "order_types": {},
            "symbols": set(),
        }

    buy_orders = []
    sell_orders = []
    total_buy_amount = 0.0
    total_sell_amount = 0.0
    total_buy_value = 0.0
    total_sell_value = 0.0
    order_types: dict[str, int] = {}
    symbols = set()

    for order in orders:
        amount = float(order.amount)
        amount_abs = abs(amount)
        price = float(order.price) if order.price else 0
        order_type = order.order_type

        symbols.add(order.symbol)
        order_types[order_type] = order_types.get(order_type, 0) + 1

        if amount > 0:  # Buy order
            buy_orders.append(order)
            total_buy_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_buy_value += amount_abs * price
        else:  # Sell order
            sell_orders.append(order)
            total_sell_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_sell_value += amount_abs * price

    return {
        "total_count": len(orders),
        "buy_count": len(buy_orders),
        "sell_count": len(sell_orders),
        "total_buy_amount": total_buy_amount,
        "total_sell_amount": total_sell_amount,
        "total_buy_value": total_buy_value,
        "total_sell_value": total_sell_value,
        "order_types": order_types,
        "symbols": symbols,
        "buy_orders": buy_orders,
        "sell_orders": sell_orders,
    }


def display_basic_summary(stats: dict[str, Any]) -> None:
    """
    Display basic order summary statistics.

    Args:
        stats: Statistics dictionary from format_summary_stats()
    """
    print("📋 ORDER SUMMARY")
    print("─" * 50)
    print("🔢 Order Counts:")
    print(f"   Total Orders: {stats['total_count']}")

    if stats["total_count"] > 0:
        buy_pct = stats["buy_count"] / stats["total_count"] * 100
        sell_pct = stats["sell_count"] / stats["total_count"] * 100
        print(f"   Buy Orders: {stats['buy_count']} ({buy_pct:.1f}%)")
        print(f"   Sell Orders: {stats['sell_count']} ({sell_pct:.1f}%)")

    print()
    print("💰 Amount Summary:")
    print(f"   Total Buy Amount: {stats['total_buy_amount']:,.4f}")
    print(f"   Total Sell Amount: {stats['total_sell_amount']:,.4f}")

    if stats["total_buy_value"] > 0:
        print(f"   Total Buy Value: ${stats['total_buy_value']:,.2f}")
    if stats["total_sell_value"] > 0:
        print(f"   Total Sell Value: ${stats['total_sell_value']:,.2f}")

    print()
    print(f"📊 Symbols: {', '.join(sorted(stats['symbols']))}")
    print(f"🏷️  Order Types: {', '.join(f'{t}({c})' for t, c in stats['order_types'].items())}")


def display_risk_assessment(stats: dict[str, Any]) -> None:
    """
    Display risk assessment based on order statistics.

    Args:
        stats: Statistics dictionary from format_summary_stats()
    """
    if stats["total_count"] == 0:
        return

    print("⚠️  Risk Assessment:")

    # Value-based exposure analysis
    if stats["total_buy_value"] > 0 and stats["total_sell_value"] > 0:
        net_exposure = stats["total_buy_value"] - stats["total_sell_value"]
        print(f"   Net Exposure: ${net_exposure:+,.2f}")

        exposure_ratio = abs(net_exposure) / max(
            stats["total_buy_value"], stats["total_sell_value"]
        )
        if exposure_ratio > 0.2:
            print(f"   ❌ High imbalance ({exposure_ratio * 100:.1f}%)")
        elif exposure_ratio > 0.1:
            print(f"   ⚠️  Moderate imbalance ({exposure_ratio * 100:.1f}%)")
        else:
            print(f"   ✅ Well balanced ({exposure_ratio * 100:.1f}%)")

    # Count-based balance analysis
    if stats["sell_count"] > 0:
        balance_ratio = stats["buy_count"] / stats["sell_count"]
        if 0.5 <= balance_ratio <= 2:
            print(f"   ✅ Good order count balance ({stats['buy_count']}:{stats['sell_count']})")
        else:
            print(f"   ⚠️  Order count imbalance ({stats['buy_count']}:{stats['sell_count']})")
    elif stats["buy_count"] > 0:
        print(f"   ⚠️  Only buy orders present ({stats['buy_count']}:0)")


def display_preparation_list(orders: list, action: str = "process") -> None:
    """
    Display a list of orders being prepared for an action.

    Args:
        orders: List of order objects
        action: Action being performed (e.g., "cancel", "update")
    """
    print(f"Preparing to {action} the following orders:")
    for order in orders:
        order_type = order.order_type
        amount = order.amount
        price = format_price(order.price) if order.price else "MARKET"
        print(f"  - Order {order.id}: {order_type} {amount} @ {price}")
    print()
