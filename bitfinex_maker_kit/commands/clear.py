"""
Clear command - Clear all orders for a specific symbol.
"""

from ..utilities.client_factory import get_client
from ..utilities.console import print_success
from ..utilities.constants import DEFAULT_SYMBOL
from ..utilities.display_helpers import display_preparation_list
from ..utilities.order_fetcher import fetch_orders_by_symbol, get_order_ids


def clear_command(symbol: str = DEFAULT_SYMBOL) -> None:
    """Clear all orders for a specific symbol"""
    print(f"Getting active orders for {symbol}...")

    # Fetch orders using centralized utility
    orders = fetch_orders_by_symbol(symbol)
    if orders is None:
        return

    if not orders:
        print(f"No active orders found for {symbol}")
        return

    print(f"Found {len(orders)} active orders for {symbol}")

    # Extract order IDs for bulk cancellation using utility
    order_ids = get_order_ids(orders)

    # Display orders being cancelled using helper
    display_preparation_list(orders, "cancel")

    # Use cancel_order_multi for efficient bulk cancellation

    try:
        client = get_client()
        client.cancel_order_multi(order_ids)
        print_success(
            f"Successfully submitted bulk cancellation request for {len(order_ids)} orders"
        )
    except Exception as e:
        from ..utilities.console import print_operation_error

        print_operation_error("cancel orders in bulk", e)
