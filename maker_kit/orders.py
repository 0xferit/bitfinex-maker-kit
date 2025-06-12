"""
Order management operations for Bitfinex CLI.
"""

from datetime import datetime
from typing import Optional, List, Union
from .auth import create_client
from .constants import (
    DEFAULT_SYMBOL, OrderSide, ValidationError, OrderSubmissionError
)
from .utils import (
    format_price, format_amount, format_timestamp, get_side_from_amount,
    print_success, print_error, print_warning, print_info, 
    print_table_separator, confirm_action
)


def _extract_order_id(response) -> Optional[str]:
    """Extract order ID from API response."""
    try:
        if hasattr(response, 'data') and response.data:
            order_data = response.data
            if isinstance(order_data, list) and len(order_data) > 0:
                return order_data[0].id if hasattr(order_data[0], 'id') else order_data[0][0]
            elif hasattr(order_data, 'id'):
                return order_data.id
        elif hasattr(response, 'id'):
            return response.id
        elif isinstance(response, list) and len(response) > 0:
            if hasattr(response[0], 'id'):
                return response[0].id
            elif isinstance(response[0], (int, str)):
                return response[0]
    except Exception:
        pass
    return None


def submit_order(symbol: str, side: Union[str, OrderSide], amount: float, 
                 price: Optional[float] = None):
    """
    Centralized order submission function that ENFORCES POST_ONLY for all limit orders.
    
    This function uses the BitfinexClientWrapper which enforces POST_ONLY
    at the API boundary level, making it architecturally impossible to bypass.
    
    Args:
        symbol: Trading symbol (e.g., "tPNKUSD")
        side: Order side ("buy"/"sell" or OrderSide enum)
        amount: Order amount (positive number)
        price: Order price (None for market orders, float for limit orders)
    
    Returns:
        Order response from exchange
        
    Raises:
        ValidationError: If parameters are invalid
        OrderSubmissionError: If order submission fails
    """
    try:
        # Get wrapper client (enforces POST_ONLY at API boundary)
        client = create_client()
        
        # Submit order through wrapper (POST_ONLY automatically enforced)
        return client.submit_order(symbol, side, amount, price)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        # Re-raise OrderSubmissionError as-is, wrap others
        if isinstance(e, OrderSubmissionError):
            raise
        raise OrderSubmissionError(f"Order submission failed: {e}") from e


def list_orders(symbol: Optional[str] = None, summary: bool = False):
    """List all active orders or orders for a specific symbol"""
    print("Fetching active orders...")
    
    client = create_client()
    
    try:
        orders = client.get_orders()
        
        # Filter by symbol if specified
        if symbol:
            filtered_orders = [order for order in orders if order.symbol == symbol]
            print(f"\n📋 Active Orders for {symbol}:")
        else:
            filtered_orders = orders
            print(f"\n📋 All Active Orders:")
        
        if not filtered_orders:
            if symbol:
                print(f"No active orders found for {symbol}")
            else:
                print("No active orders found")
            return
        
        if summary:
            return _show_order_summary(filtered_orders)
        
        return _show_detailed_orders(filtered_orders)
        
    except Exception as e:
        print(f"❌ Failed to get orders: {e}")
        return []


def _show_order_summary(filtered_orders):
    """Generate and display summary statistics for orders"""
    print(f"Found {len(filtered_orders)} active order(s)")
    print()
    
    # Group orders by symbol for analysis
    orders_by_symbol = {}
    total_buy_amount = 0
    total_sell_amount = 0
    total_buy_value = 0  # amount * price for buy orders
    total_sell_value = 0  # amount * price for sell orders
    order_types = {}
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
            orders_by_symbol[order_symbol] = {'count': 0, 'buy_count': 0, 'sell_count': 0, 'buy_amount': 0, 'sell_amount': 0}
        orders_by_symbol[order_symbol]['count'] += 1
        
        # Track buy vs sell statistics
        if is_buy:
            total_buy_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_buy_value += amount_abs * price
            orders_by_symbol[order_symbol]['buy_count'] += 1
            orders_by_symbol[order_symbol]['buy_amount'] += amount_abs
            buy_orders.append(order)
        else:
            total_sell_amount += amount_abs
            if price > 0:  # Skip market orders for value calculation
                total_sell_value += amount_abs * price
            orders_by_symbol[order_symbol]['sell_count'] += 1
            orders_by_symbol[order_symbol]['sell_amount'] += amount_abs
            sell_orders.append(order)
        
        # Track order types
        order_types[order_type] = order_types.get(order_type, 0) + 1
        
        # Track oldest/newest orders
        if created_timestamp:
            if oldest_order is None or created_timestamp < oldest_order.mts_create:
                oldest_order = order
            if newest_order is None or created_timestamp > newest_order.mts_create:
                newest_order = order
    
    # Display summary statistics
    print("📊 SUMMARY STATISTICS")
    print("═" * 60)
    
    # Overall counts
    print(f"🔢 Overall:")
    print(f"   Total Orders: {len(filtered_orders)}")
    print(f"   Buy Orders: {len(buy_orders)} ({len(buy_orders)/len(filtered_orders)*100:.1f}%)")
    print(f"   Sell Orders: {len(sell_orders)} ({len(sell_orders)/len(filtered_orders)*100:.1f}%)")
    print()
    
    # Amount summary
    print(f"💰 Amount Summary:")
    print(f"   Total Buy Amount: {total_buy_amount:,.2f}")
    print(f"   Total Sell Amount: {total_sell_amount:,.2f}")
    if total_buy_value > 0:
        print(f"   Total Buy Value: ${total_buy_value:,.2f}")
    if total_sell_value > 0:
        print(f"   Total Sell Value: ${total_sell_value:,.2f}")
    print()
    
    # Symbol breakdown
    print(f"🔹 By Symbol:")
    for order_symbol, stats in sorted(orders_by_symbol.items()):
        print(f"   {order_symbol}: {stats['count']} orders ({stats['buy_count']} buy, {stats['sell_count']} sell)")
        print(f"      Buy Amount: {stats['buy_amount']:,.2f}, Sell Amount: {stats['sell_amount']:,.2f}")
    print()
    
    # Order type breakdown
    print(f"📋 By Order Type:")
    for order_type, count in sorted(order_types.items()):
        percentage = (count / len(filtered_orders)) * 100
        print(f"   {order_type}: {count} orders ({percentage:.1f}%)")
    print()
    
    # Price analysis for each symbol
    print(f"💹 Price Analysis:")
    for order_symbol in sorted(orders_by_symbol.keys()):
        symbol_orders = [o for o in filtered_orders if o.symbol == order_symbol]
        symbol_buy_orders = [o for o in symbol_orders if float(o.amount) > 0 and o.price]
        symbol_sell_orders = [o for o in symbol_orders if float(o.amount) < 0 and o.price]
        
        print(f"   {order_symbol}:")
        
        if symbol_buy_orders:
            buy_prices = [float(o.price) for o in symbol_buy_orders]
            avg_buy_price = sum(buy_prices) / len(buy_prices)
            highest_buy = max(buy_prices)
            lowest_buy = min(buy_prices)
            print(f"      Buy Orders: Avg ${avg_buy_price:.6f}, Range ${lowest_buy:.6f} - ${highest_buy:.6f}")
        
        if symbol_sell_orders:
            sell_prices = [float(o.price) for o in symbol_sell_orders]
            avg_sell_price = sum(sell_prices) / len(sell_prices)
            highest_sell = max(sell_prices)
            lowest_sell = min(sell_prices)
            print(f"      Sell Orders: Avg ${avg_sell_price:.6f}, Range ${lowest_sell:.6f} - ${highest_sell:.6f}")
        
        # Calculate spread between highest buy and lowest sell
        if symbol_buy_orders and symbol_sell_orders:
            buy_prices = [float(o.price) for o in symbol_buy_orders]
            sell_prices = [float(o.price) for o in symbol_sell_orders]
            highest_buy = max(buy_prices)
            lowest_sell = min(sell_prices)
            spread = lowest_sell - highest_buy
            mid_price = (highest_buy + lowest_sell) / 2
            spread_pct = (spread / mid_price) * 100 if mid_price > 0 else 0
            print(f"      Your Spread: ${spread:.6f} ({spread_pct:.3f}%)")
    print()
    
    # Time analysis
    if oldest_order and newest_order:
        oldest_date = datetime.fromtimestamp(oldest_order.mts_create / 1000).strftime("%Y-%m-%d %H:%M:%S")
        newest_date = datetime.fromtimestamp(newest_order.mts_create / 1000).strftime("%Y-%m-%d %H:%M:%S")
        age_hours = (newest_order.mts_create - oldest_order.mts_create) / (1000 * 3600)
        
        print(f"⏰ Time Analysis:")
        print(f"   Oldest Order: {oldest_date} (ID: {oldest_order.id})")
        print(f"   Newest Order: {newest_date} (ID: {newest_order.id})")
        print(f"   Age Range: {age_hours:.1f} hours")
        print()
    
    # Risk summary
    print(f"⚠️  Risk Summary:")
    if total_buy_value > 0 and total_sell_value > 0:
        net_exposure = total_buy_value - total_sell_value
        print(f"   Net Exposure: ${net_exposure:+,.2f}")
        if abs(net_exposure) > max(total_buy_value, total_sell_value) * 0.1:
            print(f"   ⚠️  Imbalanced exposure - consider adjusting order sizes")
        else:
            print(f"   ✅ Relatively balanced exposure")
    
    balance_ratio = len(buy_orders) / len(sell_orders) if sell_orders else float('inf')
    if balance_ratio > 2:
        print(f"   ⚠️  Heavy buy-side bias ({len(buy_orders)} buy vs {len(sell_orders)} sell)")
    elif balance_ratio < 0.5:
        print(f"   ⚠️  Heavy sell-side bias ({len(buy_orders)} buy vs {len(sell_orders)} sell)")
    else:
        print(f"   ✅ Reasonable buy/sell balance ({len(buy_orders)} buy vs {len(sell_orders)} sell)")
    
    print("═" * 60)
    return filtered_orders


def _show_detailed_orders(filtered_orders):
    """Display detailed order information"""
    print(f"Found {len(filtered_orders)} active order(s)")
    print()
    
    # Group orders by symbol for better display
    orders_by_symbol = {}
    for order in filtered_orders:
        order_symbol = order.symbol
        if order_symbol not in orders_by_symbol:
            orders_by_symbol[order_symbol] = []
        orders_by_symbol[order_symbol].append(order)
    
    # Display orders grouped by symbol
    for order_symbol, orders in orders_by_symbol.items():
        # Sort orders by price (lowest to highest), with market orders at the end
        def sort_key(order):
            if order.price is None:
                return float('inf')  # Market orders go to the end
            return float(order.price)
        
        sorted_orders = sorted(orders, key=sort_key)
        
        print(f"🔹 {order_symbol}:")
        print("─" * 80)
        print(f"{'ID':<12} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15} {'Created':<20}")
        print("─" * 80)
        
        for order in sorted_orders:
            order_id = order.id
            amount = float(order.amount)
            side = "BUY" if amount > 0 else "SELL"
            amount_abs = abs(amount)
            order_type = order.order_type
            price = order.price if order.price else "MARKET"
            created_timestamp = order.mts_create
            
            # Convert timestamp to readable date
            if created_timestamp:
                created_date = datetime.fromtimestamp(created_timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            else:
                created_date = "Unknown"
            
            # Format price
            price_str = f"${float(price):.6f}" if price != "MARKET" else "MARKET"
            
            print(f"{order_id:<12} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15} {created_date:<20}")
        
        print()
    
    return filtered_orders


def cancel_order(order_id: int):
    """Cancel a specific order by ID"""
    client = create_client()
    
    try:
        result = client.cancel_order(order_id)
        return True, "Order cancelled successfully"
    except Exception as e:
        return False, str(e)


def cancel_single_order(order_id: int):
    """Cancel a single order by ID"""
    print(f"🗑️  Cancelling order {order_id}...")
    
    success, result = cancel_order(order_id)
    
    if success:
        print(f"✅ Successfully cancelled order {order_id}")
    else:
        if "not found" in str(result).lower():
            print(f"❌ Order {order_id} not found (may have already been filled or cancelled)")
        else:
            print(f"❌ Failed to cancel order {order_id}: {result}")
    
    return success


def clear_orders(symbol: str = "tPNKUSD"):
    """Clear all orders for a specific symbol"""
    print(f"Getting active orders for {symbol}...")
    
    orders = list_orders(symbol)
    
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
    client = create_client()
    
    try:
        result = client.cancel_order_multi(order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}")


def cancel_orders_by_criteria(size: Optional[float] = None, direction: Optional[str] = None, 
                             symbol: Optional[str] = None, price_below: Optional[float] = None,
                             price_above: Optional[float] = None, dry_run: bool = False):
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
    
    if symbol:
        print(f"Getting active orders for {symbol}...")
        orders = list_orders(symbol)
    else:
        print(f"Getting all active orders...")
        orders = list_orders()
    
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
        
        print(f"{order_id:<12} {order_symbol:<10} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15}")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Found {len(matching_orders)} orders that would be cancelled")
        return
    
    print()
    response = input(f"Do you want to cancel these {len(matching_orders)} orders? (y/N): ")
    if response.lower() != 'y':
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
    client = create_client()
    
    try:
        result = client.cancel_order_multi(order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
        print(f"📊 Summary: {len(order_ids)} orders cancelled")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}")
        print(f"📊 Summary: 0 cancelled, {len(order_ids)} failed")


def put_order(symbol: str, side: str, amount: float, price: Optional[str] = None, 
              dry_run: bool = False):
    """Place a single order (always POST_ONLY for limit orders)."""
    
    # Validate and parse price
    is_market_order = price is None
    if not is_market_order:
        try:
            price_float = float(price)
        except ValueError:
            print_error(f"Invalid price '{price}'. Use a number or omit for market order")
            return
    else:
        price_float = None
    
    # Show order details
    print_info("Order Details:")
    print(f"   Symbol: {symbol}")
    print(f"   Side: {side.upper()}")
    print(f"   Amount: {format_amount(amount)}")
    if is_market_order:
        print(f"   Type: MARKET ORDER")
    else:
        print(f"   Price: {format_price(price_float)}")
        print(f"   Type: POST-ONLY LIMIT (Maker)")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Order details shown above, no order will be placed")
        return
    
    # Confirm before placing order
    order_desc = f"{side.upper()} {format_amount(amount)} {symbol}"
    if is_market_order:
        order_desc += " at MARKET price"
    else:
        order_desc += f" at {format_price(price_float)}"
    
    if not confirm_action(f"Do you want to place this order: {order_desc}?"):
        print_error("Order cancelled")
        return
    
    print(f"\n🚀 Placing order...")
    
    try:
        # Use centralized order submission function
        response = submit_order(symbol, side, amount, price_float)
        
        # Try to extract order ID from response
        order_id = _extract_order_id(response)
        
        # Show success message
        order_status = "MARKET" if is_market_order else "POST-ONLY LIMIT"
        
        success_msg = f"{side.upper()} {order_status} order placed: {format_amount(amount)} {symbol}"
        if not is_market_order:
            success_msg += f" @ {format_price(price_float)}"
        if order_id:
            success_msg += f" (ID: {order_id})"
        
        print_success(success_msg)
        
    except ValidationError as e:
        print_error(str(e))
    except OrderSubmissionError as e:
        if not is_market_order and "would have matched" in str(e).lower():
            print_warning("POST-ONLY order cancelled (would have matched existing order)")
            print("   This is expected behavior - order was rejected to maintain maker status")
        else:
            print_error(f"Failed to place order: {e}")
    except Exception as e:
        print_error(f"Unexpected error placing order: {e}") 