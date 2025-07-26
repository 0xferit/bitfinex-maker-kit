"""
Update command - Update existing orders.
"""

from ..utilities.console import (
    confirm_action,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from ..utilities.constants import OrderSubmissionError, ValidationError
from ..utilities.formatters import format_amount, format_price
from ..utilities.orders import update_order


def update_single_order(
    order_id: int,
    price: float | None = None,
    amount: float | None = None,
    delta: float | None = None,
    dry_run: bool = False,
    yes: bool = False,
    use_cancel_recreate: bool = False,
) -> None:
    """Update a single order by ID."""

    # Build description of changes
    changes = []
    if price is not None:
        changes.append(f"price to {format_price(price)}")
    if amount is not None:
        changes.append(f"amount to {format_amount(amount)}")
    if delta is not None:
        if delta > 0:
            changes.append(f"increase amount by {format_amount(delta)}")
        else:
            changes.append(f"decrease amount by {format_amount(abs(delta))}")

    changes_desc = " and ".join(changes)

    # Show update details
    print_info("Order Update Details:")
    print(f"   Order ID: {order_id}")
    print(f"   Changes: {changes_desc}")
    if use_cancel_recreate:
        print("   Method: Cancel-and-recreate (riskier - may lose order if recreation fails)")
    else:
        print("   Method: WebSocket atomic update (safer - preserves POST_ONLY)")

    if dry_run:
        print("\n🔍 DRY RUN - Update details shown above, no order will be updated")
        return

    # Confirm before updating order
    if not yes and not confirm_action(f"Do you want to update order {order_id} ({changes_desc})?"):
        print_error("Order update cancelled")
        return

    print(f"\n🔄 Updating order {order_id}...")

    try:
        # Use centralized order update function
        success, result = update_order(order_id, price, amount, delta, use_cancel_recreate)

        if success:
            print_success(f"Order {order_id} updated successfully: {changes_desc}")

            # Show additional details from the response
            if isinstance(result, dict):
                if result.get("method") == "cancel_recreate":
                    print_info(f"Original order {result.get('original_order_id')} cancelled")
                    if "new_order" in result and hasattr(result["new_order"], "id"):
                        print_info(f"New order created with ID: {result['new_order'].id}")
                elif result.get("method") in ["websocket", "websocket_atomic"]:
                    print_info("Order updated via WebSocket (atomic update)")
        else:
            print_error(f"Failed to update order {order_id}: {result}")

    except ValidationError as e:
        print_error(str(e))
    except OrderSubmissionError as e:
        if "not found" in str(e).lower():
            print_warning(f"Order {order_id} not found (may have been filled or cancelled)")
        else:
            print_error(f"Failed to update order: {e}")
    except Exception as e:
        print_error(f"Unexpected error updating order: {e}")


def update_orders_by_criteria(
    filter_size: float | None = None,
    filter_direction: str | None = None,
    filter_symbol: str | None = None,
    price: float | None = None,
    amount: float | None = None,
    delta: float | None = None,
    dry_run: bool = False,
    yes: bool = False,
    use_cancel_recreate: bool = False,
) -> None:
    """Update orders matching specific criteria (size, direction, symbol)."""

    # Build description of criteria
    criteria_parts = []
    if filter_size is not None:
        criteria_parts.append(f"size {filter_size}")
    if filter_direction:
        criteria_parts.append(f"direction {filter_direction.upper()}")
    if filter_symbol:
        criteria_parts.append(f"symbol {filter_symbol}")

    criteria_desc = " and ".join(criteria_parts) if criteria_parts else "all criteria"

    # Build description of changes
    changes = []
    if price is not None:
        changes.append(f"price to {format_price(price)}")
    if amount is not None:
        changes.append(f"amount to {format_amount(amount)}")
    if delta is not None:
        if delta > 0:
            changes.append(f"increase amount by {format_amount(delta)}")
        else:
            changes.append(f"decrease amount by {format_amount(abs(delta))}")

    changes_desc = " and ".join(changes)

    # Get orders directly using client
    from ..services.container import get_container

    container = get_container()
    client = container.create_bitfinex_client()
    try:
        all_orders = client.get_orders()
        if filter_symbol:
            print(f"Getting active orders for {filter_symbol}...")
            orders = [order for order in all_orders if order.symbol == filter_symbol]
        else:
            print("Getting all active orders...")
            orders = all_orders
    except Exception as e:
        print_error(f"Failed to get orders: {e}")
        return

    if not orders:
        print("No active orders found")
        return

    # Filter orders by criteria
    matching_orders = []
    for order in orders:
        matches = True

        # Check size criteria
        if filter_size is not None:
            order_size = abs(float(order.amount))
            if order_size != filter_size:
                matches = False

        # Check direction criteria
        if filter_direction and matches:
            current_amount = float(
                order.amount
            )  # Renamed to avoid shadowing the function parameter
            order_direction = "buy" if current_amount > 0 else "sell"
            if order_direction != filter_direction.lower():
                matches = False

        if matches:
            matching_orders.append(order)

    if not matching_orders:
        print(f"No orders found matching criteria: {criteria_desc}")
        return

    print(f"\n📋 Found {len(matching_orders)} orders matching criteria ({criteria_desc}):")
    print("─" * 90)
    print(f"{'ID':<12} {'Symbol':<10} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15}")
    print("─" * 90)

    for order in matching_orders:
        order_id = order.id
        order_symbol = order.symbol
        order_type = order.order_type
        current_amount = float(order.amount)  # Renamed to avoid shadowing the function parameter
        side = "BUY" if current_amount > 0 else "SELL"
        amount_abs = abs(current_amount)
        price_val = order.price if order.price else None
        price_str = f"${float(price_val):.6f}" if price_val is not None else "MARKET"

        print(
            f"{order_id:<12} {order_symbol:<10} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15}"
        )

    print(f"\nWill update these {len(matching_orders)} orders: {changes_desc}")
    if use_cancel_recreate:
        print("Method: Cancel-and-recreate (riskier - may lose orders if recreation fails)")
    else:
        print("Method: WebSocket atomic update (safer - preserves POST_ONLY)")

    if dry_run:
        print(f"\n🔍 DRY RUN - Found {len(matching_orders)} orders that would be updated")
        return

    print()
    if not yes and not confirm_action(
        f"Do you want to update these {len(matching_orders)} orders ({changes_desc})?"
    ):
        print_error("Bulk update cancelled")
        return

    print(f"\n🔄 Updating {len(matching_orders)} orders matching criteria...")

    # Update each matching order
    successful_updates = 0
    failed_updates = 0

    for i, order in enumerate(matching_orders):
        order_id = order.id
        order_symbol = order.symbol
        order_amount = abs(float(order.amount))
        order_price = order.price if order.price else "MARKET"

        print(f"Updating {order_symbol} order {order_id}: {order_amount} @ {order_price}")

        # Add delay between updates to prevent nonce issues (except for first order)
        if i > 0:
            import time

            delay = 0.2  # 0.2 seconds between orders
            print(f"   ⏳ Waiting {delay}s before next update to prevent nonce issues...")
            time.sleep(delay)

        try:
            # Use the function parameters, not the current order values
            success, result = update_order(order_id, price, amount, delta, use_cancel_recreate)

            if success:
                successful_updates += 1
                print(f"   ✅ Successfully updated order {order_id}")

                # Show new order ID if available
                if (
                    isinstance(result, dict)
                    and result.get("method") == "cancel_recreate"
                    and "new_order" in result
                    and hasattr(result["new_order"], "id")
                ):
                    print(f"   📋 New order ID: {result['new_order'].id}")
            else:
                failed_updates += 1
                print(f"   ❌ Failed to update order {order_id}: {result}")

        except Exception as e:
            failed_updates += 1
            if "not found" in str(e).lower():
                print(f"   ⚠️  Order {order_id} not found (may have been filled or cancelled)")
            else:
                print(f"   ❌ Failed to update order {order_id}: {e}")

    # Show summary
    print("\n📊 Bulk Update Summary:")
    print(f"   ✅ Successfully updated: {successful_updates} orders")
    if failed_updates > 0:
        print(f"   ❌ Failed to update: {failed_updates} orders")
    print(f"   📈 Total processed: {len(matching_orders)} orders")


def update_command(
    order_id: int | None = None,
    price: float | None = None,
    amount: float | None = None,
    delta: float | None = None,
    filter_size: float | None = None,
    filter_direction: str | None = None,
    filter_symbol: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
    use_cancel_recreate: bool = False,
) -> None:
    """Update existing orders - either single order by ID or multiple orders by criteria."""

    # Show information about update methods if not using cancel-recreate
    if not use_cancel_recreate:
        print_info("📡 Using atomic updates (safer - preserves POST_ONLY)")
        print("   Uses REST API or WebSocket for reliable atomic updates")
        print("   For cancel-and-recreate method (riskier), use --use-cancel-recreate flag")
        print()
    else:
        print_info("⚠️  Using cancel-and-recreate method (riskier - may lose orders)")
        print("   This method cancels existing orders and creates new ones")
        print()

    # Validate parameters
    if price is None and amount is None and delta is None:
        print_error("Must specify at least one update parameter: --price, --amount, or --delta")
        return

    if amount is not None and delta is not None:
        print_error("Cannot specify both --amount and --delta - use one or the other")
        return

    # Validate numeric parameters
    if price is not None and price <= 0:
        print_error(f"Price must be positive, got: {price}")
        return

    if amount is not None and amount <= 0:
        print_error(f"Amount must be positive, got: {amount}")
        return

    if delta is not None and delta == 0:
        print_error("Delta cannot be zero - specify a positive or negative value to add/subtract")
        return

    if filter_size is not None and filter_size <= 0:
        print_error(f"Filter size must be positive, got: {filter_size}")
        return

    # Determine update mode
    has_criteria = filter_size is not None or filter_direction or filter_symbol

    if order_id and has_criteria:
        print_error("Cannot specify both order_id and filter criteria - use one or the other")
        return

    if not order_id and not has_criteria:
        print_error(
            "Must specify either order_id or filter criteria (--filter-size, --filter-direction, --filter-symbol)"
        )
        return

    # Route to appropriate function
    if order_id:
        # Single order update
        update_single_order(order_id, price, amount, delta, dry_run, yes, use_cancel_recreate)
    else:
        # Bulk update by criteria
        update_orders_by_criteria(
            filter_size,
            filter_direction,
            filter_symbol,
            price,
            amount,
            delta,
            dry_run,
            yes,
            use_cancel_recreate,
        )
