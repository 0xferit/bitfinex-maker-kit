"""
Clear command - Clear all orders for a specific symbol.
"""

from ..utilities.auth import create_client
from ..utilities.constants import DEFAULT_SYMBOL


def clear_command(symbol: str = DEFAULT_SYMBOL):
    """Clear all orders for a specific symbol"""
    print(f"Getting active orders for {symbol}...")
    
    # Get orders directly using client instead of importing from list command
    client = create_client()
    try:
        all_orders = client.get_orders()
        orders = [order for order in all_orders if order.symbol == symbol]
    except Exception as e:
        print(f"❌ Failed to get orders: {e}")
        return
    
    if not orders:
        print(f"No active orders found for {symbol}")
        return
    
    print(f"Found {len(orders)} active orders for {symbol}")
    
    # Extract order IDs for bulk cancellation
    order_ids = [order.id for order in orders]
    
    # Display orders being cancelled
    for order in orders:
        order_type = order.order_type
        amount = order.amount
        price = order.price if order.price else "MARKET"
        print(f"Preparing to cancel order {order.id}: {order_type} {amount} @ {price}")
    
    # Use cancel_order_multi for efficient bulk cancellation
    
    try:
        result = client.cancel_order_multi(order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}") 