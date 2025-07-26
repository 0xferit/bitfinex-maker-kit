"""
List command - List active orders with detailed analysis.
"""

from ..utilities.console import print_operation_error
from ..utilities.constants import DEFAULT_SYMBOL
from ..utilities.display_helpers import (
    display_orders_by_symbol,
)
from ..utilities.market_data import get_ticker_data
from ..utilities.order_fetcher import fetch_all_orders, fetch_orders_by_symbol


def list_orders(symbol: str | None = None, summary: bool = False) -> list:
    """List all active orders or orders for a specific symbol"""
    if symbol is None:
        print("Fetching all active orders...")
        filtered_orders = fetch_all_orders()
        header = "\n📋 All Active Orders:"
    else:
        print("Fetching active orders...")
        filtered_orders = fetch_orders_by_symbol(symbol)
        header = f"\n📋 Active Orders for {symbol}:"

    if filtered_orders is None:
        return []

    print(header)

    if not filtered_orders:
        if symbol:
            print(f"No active orders found for {symbol}")
        else:
            print("No active orders found")
        return []

    if summary:
        return _show_order_summary(filtered_orders)

    return _show_detailed_orders(filtered_orders)


def list_command(symbol: str = DEFAULT_SYMBOL, summary: bool = False) -> list:
    """List active orders command wrapper"""
    return list_orders(symbol, summary)


def _show_order_summary(filtered_orders: list) -> list:
    """Generate and display enhanced summary statistics with liquidity analysis"""
    print(f"Found {len(filtered_orders)} active order(s)")
    print()

    # Group orders by symbol for analysis
    orders_by_symbol = {}
    total_buy_amount = 0.0
    total_sell_amount = 0.0
    total_buy_value = 0.0  # amount * price for buy orders
    total_sell_value = 0.0  # amount * price for sell orders
    order_types: dict[str, int] = {}
    oldest_order = None
    newest_order = None
    buy_orders = []
    sell_orders = []

    for order in filtered_orders:
        order_symbol = order.symbol
        amount = float(order.amount)
        is_buy = amount > 0
        amount_abs = abs(amount)
        price = float(order.price) if order.price else 0
        order_type = order.order_type
        created_timestamp = order.mts_create

        # Group by symbol
        if order_symbol not in orders_by_symbol:
            orders_by_symbol[order_symbol] = {
                "count": 0,
                "buy_count": 0,
                "sell_count": 0,
                "buy_amount": 0.0,
                "sell_amount": 0.0,
            }
        orders_by_symbol[order_symbol]["count"] += 1

        # Track buy vs sell statistics
        if is_buy:
            total_buy_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_buy_value += amount_abs * price
            orders_by_symbol[order_symbol]["buy_count"] += 1
            orders_by_symbol[order_symbol]["buy_amount"] += amount_abs
            buy_orders.append(order)
        else:
            total_sell_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_sell_value += amount_abs * price
            orders_by_symbol[order_symbol]["sell_count"] += 1
            orders_by_symbol[order_symbol]["sell_amount"] += amount_abs
            sell_orders.append(order)

        # Track order types
        order_types[order_type] = order_types.get(order_type, 0) + 1

        # Track oldest/newest orders
        if created_timestamp:
            if oldest_order is None or created_timestamp < oldest_order.mts_create:
                oldest_order = order
            if newest_order is None or created_timestamp > newest_order.mts_create:
                newest_order = order

    # Display enhanced summary statistics
    print("📊 ENHANCED SUMMARY STATISTICS")
    print("═" * 80)

    # Market data and liquidity analysis per symbol
    for order_symbol in sorted(orders_by_symbol.keys()):
        print(f"\n🎯 LIQUIDITY ANALYSIS - {order_symbol}")
        print("─" * 50)

        # Get current market data
        ticker = get_ticker_data(order_symbol)
        if ticker:
            current_bid = ticker["bid"]
            current_ask = ticker["ask"]
            current_mid = (current_bid + current_ask) / 2
            market_spread = current_ask - current_bid
            market_spread_pct = (market_spread / current_mid) * 100

            print("📈 Current Market Data:")
            print(f"   Bid: ${current_bid:.6f} | Ask: ${current_ask:.6f}")
            print(f"   Mid Price: ${current_mid:.6f}")
            print(f"   Market Spread: ${market_spread:.6f} ({market_spread_pct:.3f}%)")
            print()

            # Calculate ±2% range around mid price
            lower_bound = current_mid * 0.98  # -2%
            upper_bound = current_mid * 1.02  # +2%

            print("🎯 Liquidity Analysis (±2% around mid price):")
            print(f"   Price Range: ${lower_bound:.6f} - ${upper_bound:.6f}")

            # Get orders for this symbol
            symbol_orders = [o for o in filtered_orders if o.symbol == order_symbol and o.price]

            # Filter orders within ±2% range
            orders_in_range = []
            buy_liquidity_in_range = 0.0
            sell_liquidity_in_range = 0.0
            buy_value_in_range = 0.0
            sell_value_in_range = 0.0

            for order in symbol_orders:
                order_price = float(order.price)
                if lower_bound <= order_price <= upper_bound:
                    orders_in_range.append(order)
                    amount = float(order.amount)
                    amount_abs = abs(amount)

                    if amount > 0:  # Buy order
                        buy_liquidity_in_range += amount_abs
                        buy_value_in_range += amount_abs * order_price
                    else:  # Sell order
                        sell_liquidity_in_range += amount_abs
                        sell_value_in_range += amount_abs * order_price

            print(
                f"   Orders in Range: {len(orders_in_range)}/{len(symbol_orders)} ({len(orders_in_range) / max(len(symbol_orders), 1) * 100:.1f}%)"
            )
            print(f"   Buy Liquidity: {buy_liquidity_in_range:,.4f} (${buy_value_in_range:,.2f})")
            print(
                f"   Sell Liquidity: {sell_liquidity_in_range:,.4f} (${sell_value_in_range:,.2f})"
            )
            print(f"   Total Liquidity: {buy_liquidity_in_range + sell_liquidity_in_range:,.4f}")
            print()

            # Display order book visualization
            _display_order_book_visualization(symbol_orders, current_mid, lower_bound, upper_bound)

        else:
            print_operation_error(f"fetch market data for {order_symbol}", Exception("API error"))

        # Your spread analysis
        symbol_buy_orders = [
            o
            for o in filtered_orders
            if o.symbol == order_symbol and float(o.amount) > 0 and o.price
        ]
        symbol_sell_orders = [
            o
            for o in filtered_orders
            if o.symbol == order_symbol and float(o.amount) < 0 and o.price
        ]

        if symbol_buy_orders and symbol_sell_orders:
            buy_prices = [float(o.price) for o in symbol_buy_orders]
            sell_prices = [float(o.price) for o in symbol_sell_orders]
            highest_buy = max(buy_prices)
            lowest_sell = min(sell_prices)
            your_spread = lowest_sell - highest_buy
            your_mid = (highest_buy + lowest_sell) / 2
            your_spread_pct = (your_spread / your_mid) * 100 if your_mid > 0 else 0

            print("📊 Your Order Spread Analysis:")
            print(f"   Highest Buy: ${highest_buy:.6f}")
            print(f"   Lowest Sell: ${lowest_sell:.6f}")
            print(f"   Your Spread: ${your_spread:.6f} ({your_spread_pct:.3f}%)")

            # Compare with market spread
            if ticker:
                spread_efficiency = (
                    your_spread / market_spread if market_spread > 0 else float("inf")
                )
                if spread_efficiency < 1.5:
                    print(f"   ✅ Tight spread ({spread_efficiency:.1f}x market spread)")
                elif spread_efficiency < 3:
                    print(f"   ⚠️  Moderate spread ({spread_efficiency:.1f}x market spread)")
                else:
                    print(f"   ❌ Wide spread ({spread_efficiency:.1f}x market spread)")
        print()

    # Overall statistics
    print("📋 OVERALL STATISTICS")
    print("─" * 50)
    print("🔢 Order Counts:")
    print(f"   Total Orders: {len(filtered_orders)}")
    print(f"   Buy Orders: {len(buy_orders)} ({len(buy_orders) / len(filtered_orders) * 100:.1f}%)")
    print(
        f"   Sell Orders: {len(sell_orders)} ({len(sell_orders) / len(filtered_orders) * 100:.1f}%)"
    )
    print()

    print("💰 Amount Summary:")
    print(f"   Total Buy Amount: {total_buy_amount:,.4f}")
    print(f"   Total Sell Amount: {total_sell_amount:,.4f}")
    if total_buy_value > 0:
        print(f"   Total Buy Value: ${total_buy_value:,.2f}")
    if total_sell_value > 0:
        print(f"   Total Sell Value: ${total_sell_value:,.2f}")
    print()

    # Risk assessment
    print("⚠️  Risk Assessment:")
    if total_buy_value > 0 and total_sell_value > 0:
        net_exposure = total_buy_value - total_sell_value
        print(f"   Net Exposure: ${net_exposure:+,.2f}")
        exposure_ratio = abs(net_exposure) / max(total_buy_value, total_sell_value)
        if exposure_ratio > 0.2:
            print(f"   ❌ High imbalance ({exposure_ratio * 100:.1f}%)")
        elif exposure_ratio > 0.1:
            print(f"   ⚠️  Moderate imbalance ({exposure_ratio * 100:.1f}%)")
        else:
            print(f"   ✅ Well balanced ({exposure_ratio * 100:.1f}%)")

    balance_ratio = len(buy_orders) / len(sell_orders) if sell_orders else float("inf")
    if 0.5 <= balance_ratio <= 2:
        print(f"   ✅ Good order count balance ({len(buy_orders)}:{len(sell_orders)})")
    else:
        print(f"   ⚠️  Order count imbalance ({len(buy_orders)}:{len(sell_orders)})")

    print("═" * 80)
    return filtered_orders


def _display_order_book_visualization(
    orders: list, mid_price: float, lower_bound: float, upper_bound: float
) -> None:
    """Display ASCII visualization of order book within specified range"""
    print("📊 Order Book Visualization (±2% range):")

    # Filter and sort orders by price
    valid_orders = [o for o in orders if o.price and lower_bound <= float(o.price) <= upper_bound]
    if not valid_orders:
        print("   No orders in the ±2% range")
        return

    # Group orders by price level and side
    price_levels = {}
    for order in valid_orders:
        price = float(order.price)
        amount = float(order.amount)

        if price not in price_levels:
            price_levels[price] = {"buy": 0.0, "sell": 0.0}

        if amount > 0:
            price_levels[price]["buy"] += float(abs(amount))
        else:
            price_levels[price]["sell"] += float(abs(amount))

    # Sort prices
    sorted_prices = sorted(price_levels.keys(), reverse=True)

    # Find max amount for scaling
    max_amount = 0.0
    for price_data in price_levels.values():
        max_amount = max(max_amount, price_data["buy"], price_data["sell"])

    if max_amount == 0:
        print("   No liquidity in range")
        return

    # Display the visualization
    print("   " + "─" * 60)
    print(f"   {'Price':<12} {'Sell':<15} {'|':<3} {'Buy':<15}")
    print("   " + "─" * 60)

    for price in sorted_prices:
        buy_amount = price_levels[price]["buy"]
        sell_amount = price_levels[price]["sell"]

        # Create bar visualization (max 15 chars each side)
        buy_bar_length = int((buy_amount / max_amount) * 15) if buy_amount > 0 else 0
        sell_bar_length = int((sell_amount / max_amount) * 15) if sell_amount > 0 else 0

        buy_bar = "█" * buy_bar_length + " " * (15 - buy_bar_length)
        sell_bar = " " * (15 - sell_bar_length) + "█" * sell_bar_length

        # Mark mid price
        price_marker = "★" if abs(price - mid_price) < (upper_bound - lower_bound) * 0.05 else " "

        print(f"   ${price:<11.6f} {sell_bar} {price_marker} {buy_bar}")

    print("   " + "─" * 60)
    print(f"   Legend: ★ ≈ Mid Price (${mid_price:.6f}) | Buy Orders (right) | Sell Orders (left)")
    print()


def _show_detailed_orders(filtered_orders: list) -> list:
    """Display detailed order information using display helpers"""
    print(f"Found {len(filtered_orders)} active order(s)")

    # Use centralized display helper
    display_orders_by_symbol(filtered_orders, show_created=True)

    return filtered_orders
