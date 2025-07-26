"""
Market-make command - Create staircase market making orders.
"""

from ..utilities.constants import (
    DEFAULT_LEVELS,
    DEFAULT_ORDER_SIZE,
    DEFAULT_SPREAD_PCT,
    DEFAULT_SYMBOL,
)
from ..utilities.market_data import (
    resolve_center_price,
    suggest_price_centers,
    validate_center_price,
)
from ..utilities.orders import submit_order


def market_make_command(
    symbol: str = DEFAULT_SYMBOL,
    center: str | None = None,
    levels: int = DEFAULT_LEVELS,
    spread: float = DEFAULT_SPREAD_PCT,
    size: float = DEFAULT_ORDER_SIZE,
    dry_run: bool = False,
    buy_only: bool = False,
    sell_only: bool = False,
    ignore_validation: bool = False,
    yes: bool = False,
) -> None:
    """Create staircase market making orders (always POST_ONLY)"""

    # Determine side filter
    side_filter = None
    if buy_only:
        side_filter = "buy"
    elif sell_only:
        side_filter = "sell"

    if center:
        # Resolve center price from string input
        center_price = resolve_center_price(symbol, center)
        if center_price is None:
            return  # Error already printed by resolve_center_price

        market_make(
            symbol, center_price, levels, spread, size, dry_run, side_filter, ignore_validation, yes
        )
    else:
        centers = suggest_price_centers(symbol)
        if centers:
            side_suffix = ""
            if side_filter == "buy":
                side_suffix = " --buy-only"
            elif side_filter == "sell":
                side_suffix = " --sell-only"

            print("\nTo create market making orders, run:")
            print(
                f"maker-kit market-make --symbol {symbol} --center PRICE --levels {levels} --spread {spread} --size {size}{side_suffix}"
            )
            print("\nExample using mid price:")
            print(
                f"maker-kit market-make --symbol {symbol} --center {centers['mid_price']:.6f} --levels {levels} --spread {spread} --size {size}{side_suffix}"
            )
            print("\nExample using mid-range:")
            print(
                f"maker-kit market-make --symbol {symbol} --center mid-range --levels {levels} --spread {spread} --size {size}{side_suffix}"
            )


def market_make(
    symbol: str,
    center_price: float,
    levels: int,
    spread_pct: float,
    size: float,
    dry_run: bool = False,
    side_filter: str | None = None,
    ignore_validation: bool = False,
    yes: bool = False,
) -> None:
    """Create staircase market making orders (always POST_ONLY)"""

    # Validate center price before proceeding
    is_valid, range_info = validate_center_price(symbol, center_price, ignore_validation)
    if not is_valid:
        print("❌ Market making cancelled due to invalid center price")
        return

    side_info = ""
    if side_filter == "buy":
        side_info = " (BUY ORDERS ONLY)"
    elif side_filter == "sell":
        side_info = " (SELL ORDERS ONLY)"

    print(f"\n🎯 Market Making Setup{side_info}:")
    print(f"   Symbol: {symbol}")
    print(f"   Center Price: ${center_price:.6f}")
    print(f"   Levels: {levels}")
    print(f"   Spread per level: {spread_pct:.3f}%")
    print(f"   Order Size: {size}")
    print("   Order Type: POST-ONLY LIMIT (Maker)")
    print(f"   Dry Run: {dry_run}")

    orders_to_place = []

    # Calculate price levels
    for i in range(1, levels + 1):
        # Buy orders below center price
        if side_filter != "sell":
            buy_price = center_price * (1 - (spread_pct * i / 100))
            orders_to_place.append(("buy", size, buy_price))

        # Sell orders above center price
        if side_filter != "buy":
            sell_price = center_price * (1 + (spread_pct * i / 100))
            orders_to_place.append(("sell", size, sell_price))

    # Sort orders by price (lowest to highest) for better visualization
    orders_to_place.sort(key=lambda x: x[2])

    print("\n📋 Orders to place (sorted by price):")
    print(f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Center':<20}")
    print("─" * 55)

    for side, amount, price in orders_to_place:
        distance_pct = ((price - center_price) / center_price) * 100
        distance_str = f"{distance_pct:+.3f}%"
        print(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")

    if dry_run:
        print("\n🔍 DRY RUN - No orders will be placed")
        return

    # Confirm before placing orders
    order_type = "orders"
    if side_filter == "buy":
        order_type = "BUY orders"
    elif side_filter == "sell":
        order_type = "SELL orders"

    if not yes:
        response = input(
            f"\nDo you want to place these {len(orders_to_place)} {order_type}? (y/N): "
        )
        if response.lower() != "y":
            print("❌ Market making cancelled")
            return

    print("\n🚀 Placing orders...")

    success_count = 0

    for side, amount, price in orders_to_place:
        try:
            # Use centralized order submission function
            response = submit_order(symbol, side, amount, price)

            print(f"✅ {side.upper()} POST-ONLY order placed: {amount} @ ${price:.6f}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to place {side.upper()} order: {e}")

    print(f"\n📊 Summary: {success_count}/{len(orders_to_place)} orders placed successfully")
