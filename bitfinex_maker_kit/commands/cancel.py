"""
Cancel command - Cancel orders by ID or by criteria.
"""

from ..domain.order_id import OrderId
from ..services.container import get_container


def cancel_single_order(order_id: int) -> bool:
    """Cancel a single order by ID using dependency injection"""
    print(f"🗑️  Cancelling order {order_id}...")

    try:
        # Get trading service through container
        container = get_container()
        trading_service = container.create_trading_service()

        # Create order ID domain object
        order_id_obj = OrderId(order_id)

        # Cancel using trading service
        success, result = trading_service.cancel_order(order_id_obj)

        if success:
            print(f"✅ Successfully cancelled order {order_id}")
        else:
            if "not found" in str(result).lower():
                print(f"❌ Order {order_id} not found (may have already been filled or cancelled)")
            else:
                print(f"❌ Failed to cancel order {order_id}: {result}")

        return success

    except Exception as e:
        print(f"❌ Error cancelling order {order_id}: {e}")
        return False


def cancel_orders_by_criteria(
    size: float | None = None,
    direction: str | None = None,
    symbol: str | None = None,
    price_below: float | None = None,
    price_above: float | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> None:
    """Cancel orders matching specific criteria (size, direction, symbol, price thresholds)"""

    # Build description of what we're looking for
    criteria_parts = []
    if size is not None:
        criteria_parts.append(f"size {size}")
    if direction:
        criteria_parts.append(f"direction {direction.upper()}")
    if symbol:
        criteria_parts.append(f"symbol {symbol}")
    if price_below is not None:
        criteria_parts.append(f"price below ${price_below:.6f}")
    if price_above is not None:
        criteria_parts.append(f"price above ${price_above:.6f}")

    criteria_desc = " and ".join(criteria_parts) if criteria_parts else "all criteria"

    # Get orders using trading service
    try:
        container = get_container()
        trading_service = container.create_trading_service()
        all_orders = trading_service.get_orders()
        if symbol:
            print(f"Getting active orders for {symbol}...")
            orders = [order for order in all_orders if order.symbol == symbol]
        else:
            print("Getting all active orders...")
            orders = all_orders
    except Exception as e:
        print(f"❌ Failed to get orders: {e}")
        return

    if not orders:
        print("No active orders found")
        return

    # Filter orders by criteria
    matching_orders = []
    for order in orders:
        matches = True

        # Check size criteria
        if size is not None:
            order_size = abs(float(order.amount))
            if order_size != size:
                matches = False

        # Check direction criteria
        if direction and matches:
            amount = float(order.amount)
            order_direction = "buy" if amount > 0 else "sell"
            if order_direction != direction.lower():
                matches = False

        # Check price criteria (skip market orders that have no price)
        if matches and (price_below is not None or price_above is not None):
            if order.price is None:
                # This is a market order - skip price filtering
                print(f"   Skipping market order {order.id} (no price to compare)")
                matches = False
            else:
                order_price = float(order.price)

                # Check price below threshold
                if price_below is not None and order_price >= price_below:
                    matches = False

                # Check price above threshold
                if price_above is not None and order_price <= price_above:
                    matches = False

        if matches:
            matching_orders.append(order)

    if not matching_orders:
        print(f"No orders found matching criteria: {criteria_desc}")
        return

    print(f"\n📋 Found {len(matching_orders)} orders matching criteria ({criteria_desc}):")
    print("─" * 80)
    print(f"{'ID':<12} {'Symbol':<10} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15}")
    print("─" * 80)

    for order in matching_orders:
        order_id = order.id
        order_symbol = order.symbol
        order_type = order.order_type
        amount = float(order.amount)
        side = "BUY" if amount > 0 else "SELL"
        amount_abs = abs(amount)
        price = order.price if order.price else "MARKET"
        price_str = f"${float(price):.6f}" if price != "MARKET" else "MARKET"

        print(
            f"{order_id:<12} {order_symbol:<10} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15}"
        )

    if dry_run:
        print(f"\n🔍 DRY RUN - Found {len(matching_orders)} orders that would be cancelled")
        return

    print()
    if not yes:
        response = input(f"Do you want to cancel these {len(matching_orders)} orders? (y/N): ")
        if response.lower() != "y":
            print("❌ Cancellation cancelled")
            return

    print(f"\n🗑️  Cancelling {len(matching_orders)} orders matching criteria...")

    # Extract order IDs for bulk cancellation
    order_ids = [order.id for order in matching_orders]

    # Display orders being cancelled
    for order in matching_orders:
        order_symbol = order.symbol
        amount = order.amount
        price = order.price if order.price else "MARKET"
        print(f"Preparing to cancel {order_symbol} order {order.id}: {amount} @ {price}")

    # Use cancel_order_multi for efficient bulk cancellation
    container = get_container()
    client = container.create_bitfinex_client()

    try:
        client.cancel_order_multi(order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
        print(f"📊 Summary: {len(order_ids)} orders cancelled")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}")
        print(f"📊 Summary: 0 cancelled, {len(order_ids)} failed")


def cancel_command(
    order_id: int | None = None,
    size: float | None = None,
    direction: str | None = None,
    symbol: str | None = None,
    price_below: float | None = None,
    price_above: float | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> bool | None:
    """Cancel orders by ID or by criteria"""
    if order_id:
        # Cancel by order ID
        return cancel_single_order(order_id)
    elif (
        size is not None
        or direction
        or symbol
        or price_below is not None
        or price_above is not None
    ):
        # Cancel by criteria
        cancel_orders_by_criteria(size, direction, symbol, price_below, price_above, dry_run, yes)
        return None
    else:
        from ..utilities.console import print_error

        print_error(
            "Must provide either order_id or criteria (--size, --direction, --symbol, --price-below, --price-above)"
        )
        print("Use 'maker-kit cancel --help' for usage information")
        return None


def _cancel_order(order_id: int) -> tuple[bool, str]:
    """Cancel a specific order by ID"""
    container = get_container()
    client = container.create_bitfinex_client()

    try:
        client.cancel_order(order_id)
        return True, "Order cancelled successfully"
    except Exception as e:
        return False, str(e)
