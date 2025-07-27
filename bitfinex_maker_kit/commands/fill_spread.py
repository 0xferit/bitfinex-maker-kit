"""
Fill-spread command - Fill the bid-ask spread gap with equally spaced orders.
"""

from ..utilities.constants import DEFAULT_SYMBOL
from ..utilities.market_data import get_ticker_data, resolve_center_price
from ..utilities.orders import submit_order


def fill_spread_command(
    symbol: str = DEFAULT_SYMBOL,
    target_spread: float | None = None,
    size: float | None = None,
    center: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> None:
    """Fill the spread gap with equally spaced orders to achieve spread less than target (always POST_ONLY)"""

    # Validate required parameters
    if target_spread is None:
        print("❌ Error: target_spread is required")
        return
    if size is None:
        print("❌ Error: size is required")
        return

    # Resolve center price if provided
    center_price = None
    if center:
        center_price = resolve_center_price(symbol, center)
        if center_price is None:
            return  # Error already printed by resolve_center_price

    fill_spread(symbol, target_spread, size, center_price, dry_run, yes)


def fill_spread(
    symbol: str,
    target_spread_pct: float,
    order_size: float,
    center: float | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> None:
    """Fill the spread gap with equally spaced orders to achieve spread less than target (always POST_ONLY)"""

    print("\n🎯 Fill Spread Setup:")
    print(f"   Symbol: {symbol}")
    print(f"   Target Max Spread: {target_spread_pct:.3f}%")
    print(f"   Order Size: {order_size}")
    if center:
        print(f"   Center: ${center:.6f}")
    print("   Order Type: POST-ONLY LIMIT (Maker)")
    print(f"   Dry Run: {dry_run}")

    # Get current market data
    print(f"\nGetting current market data for {symbol}...")
    ticker = get_ticker_data(symbol)
    if not ticker:
        print("❌ Failed to get market data")
        return

    current_bid = ticker["bid"]
    current_ask = ticker["ask"]
    mid_price = (current_bid + current_ask) / 2
    current_spread = current_ask - current_bid
    current_spread_pct = (current_spread / mid_price) * 100

    print("\n📊 Current Market State:")
    print(f"   Best Bid: ${current_bid:.6f}")
    print(f"   Best Ask: ${current_ask:.6f}")
    print(f"   Mid Price: ${mid_price:.6f}")
    print(f"   Current Spread: ${current_spread:.6f} ({current_spread_pct:.3f}%)")

    # Validate target spread
    if target_spread_pct >= current_spread_pct:
        print(
            f"\n❌ Target spread ({target_spread_pct:.3f}%) must be smaller than current spread ({current_spread_pct:.3f}%)"
        )
        print(
            f"   💡 Current spread is already {current_spread_pct:.3f}% - target must be less than this"
        )
        return

    if target_spread_pct <= 0:
        print(f"\n❌ Target spread ({target_spread_pct:.3f}%) must be positive")
        return

    # Use the provided center price or default behavior
    center_price = center

    orders_to_place = []

    if center_price is not None:
        # Center-based order placement
        target_spread_dollar = center_price * (target_spread_pct / 100)
        target_half_spread = target_spread_dollar / 2

        # Calculate target bid/ask around the center
        target_bid = center_price - target_half_spread
        target_ask = center_price + target_half_spread

        print("\n🎯 Target prices around center:")
        print(f"   Target Bid: ${target_bid:.6f}")
        print(f"   Target Ask: ${target_ask:.6f}")
        print(f"   Target Spread: ${target_spread_dollar:.6f} ({target_spread_pct:.3f}%)")

        # Place orders at target prices (if they improve the market)
        if target_bid > current_bid:
            orders_to_place.append(("buy", order_size, target_bid))
            print(f"\n📈 Buy order will improve bid: ${current_bid:.6f} → ${target_bid:.6f}")
        else:
            print(
                f"\n⚠️  Target bid ${target_bid:.6f} would not improve current bid ${current_bid:.6f}"
            )

        if target_ask < current_ask:
            orders_to_place.append(("sell", order_size, target_ask))
            print(f"📉 Sell order will improve ask: ${current_ask:.6f} → ${target_ask:.6f}")
        else:
            print(
                f"\n⚠️  Target ask ${target_ask:.6f} would not improve current ask ${current_ask:.6f}"
            )

    else:
        # Default behavior: place orders within current spread to tighten it
        spread_gap = current_ask - current_bid
        min_order_spacing = mid_price * 0.0005  # 0.05% minimum spacing between orders

        # Calculate maximum number of orders we can place
        max_orders_per_side = max(1, int(spread_gap / (2 * min_order_spacing)))

        # Calculate optimal spacing to achieve target spread
        target_spread_dollar = mid_price * (target_spread_pct / 100)

        # How much we need to tighten each side
        tighten_per_side = (current_spread - target_spread_dollar) / 2

        # Place buy orders above current bid (moving toward mid price)
        if tighten_per_side > min_order_spacing:
            num_buy_levels = min(
                max_orders_per_side, max(1, int(tighten_per_side / min_order_spacing))
            )
            buy_spacing = tighten_per_side / num_buy_levels

            print(f"\n📈 Buy side orders ({num_buy_levels} levels):")
            for i in range(1, num_buy_levels + 1):
                buy_price = current_bid + (buy_spacing * i)
                orders_to_place.append(("buy", order_size, buy_price))
                distance_from_mid = ((buy_price - mid_price) / mid_price) * 100
                print(f"   Level {i}: ${buy_price:.6f} ({distance_from_mid:+.3f}% from mid)")

        # Place sell orders below current ask (moving toward mid price)
        if tighten_per_side > min_order_spacing:
            num_sell_levels = min(
                max_orders_per_side, max(1, int(tighten_per_side / min_order_spacing))
            )
            sell_spacing = tighten_per_side / num_sell_levels

            print(f"\n📉 Sell side orders ({num_sell_levels} levels):")
            for i in range(1, num_sell_levels + 1):
                sell_price = current_ask - (sell_spacing * i)
                orders_to_place.append(("sell", order_size, sell_price))
                distance_from_mid = ((sell_price - mid_price) / mid_price) * 100
                print(f"   Level {i}: ${sell_price:.6f} ({distance_from_mid:+.3f}% from mid)")

    if not orders_to_place:
        print("\n❌ No orders needed - spread is already tight enough or gaps are too small")
        print(f"   Current spread: {current_spread_pct:.3f}% vs target: {target_spread_pct:.3f}%")
        return

    # Sort orders by price for better visualization
    orders_to_place.sort(key=lambda x: x[2])

    print(f"\n📋 Orders to place ({len(orders_to_place)} total, sorted by price):")
    print(f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Mid':<20}")
    print("─" * 55)

    for side, amount, price in orders_to_place:
        distance_pct = ((price - mid_price) / mid_price) * 100
        distance_str = f"{distance_pct:+.3f}%"
        print(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")

    # Calculate expected improvement
    if orders_to_place:
        buy_orders = [order for order in orders_to_place if order[0] == "buy"]
        sell_orders = [order for order in orders_to_place if order[0] == "sell"]

        new_best_bid = max([order[2] for order in buy_orders]) if buy_orders else current_bid
        new_best_ask = min([order[2] for order in sell_orders]) if sell_orders else current_ask
        new_spread = new_best_ask - new_best_bid
        new_spread_pct = (new_spread / mid_price) * 100

        print("\n💡 Expected Result:")
        print(f"   New Best Bid: ${new_best_bid:.6f}")
        print(f"   New Best Ask: ${new_best_ask:.6f}")
        print(f"   New Spread: ${new_spread:.6f} ({new_spread_pct:.3f}%)")
        print(f"   Improvement: {current_spread_pct - new_spread_pct:.3f}% tighter")

        if new_spread_pct <= target_spread_pct:
            print(f"   ✅ Spread target achieved: {new_spread_pct:.3f}% ≤ {target_spread_pct:.3f}%")
        else:
            print(
                f"   ⚠️  Spread target not fully achieved: {new_spread_pct:.3f}% > {target_spread_pct:.3f}%"
            )

    if dry_run:
        print("\n🔍 DRY RUN - No orders will be placed")
        return

    # Confirm before placing orders
    if not yes:
        response = input(
            f"\nDo you want to place these {len(orders_to_place)} spread-filling orders? (y/N): "
        )
        if response.lower() != "y":
            print("❌ Spread filling cancelled")
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

    if success_count > 0:
        print("\n✨ Spread filling complete! Check the order book to see the improved liquidity.")
