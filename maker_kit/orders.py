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
from .market_data import get_ticker_data


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
    """Generate and display enhanced summary statistics with liquidity analysis"""
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
            current_bid = ticker['bid']
            current_ask = ticker['ask']
            current_mid = (current_bid + current_ask) / 2
            market_spread = current_ask - current_bid
            market_spread_pct = (market_spread / current_mid) * 100
            
            print(f"📈 Current Market Data:")
            print(f"   Bid: ${current_bid:.6f} | Ask: ${current_ask:.6f}")
            print(f"   Mid Price: ${current_mid:.6f}")
            print(f"   Market Spread: ${market_spread:.6f} ({market_spread_pct:.3f}%)")
            print()
            
            # Calculate ±2% range around mid price
            lower_bound = current_mid * 0.98  # -2%
            upper_bound = current_mid * 1.02  # +2%
            
            print(f"🎯 Liquidity Analysis (±2% around mid price):")
            print(f"   Price Range: ${lower_bound:.6f} - ${upper_bound:.6f}")
            
            # Get orders for this symbol
            symbol_orders = [o for o in filtered_orders if o.symbol == order_symbol and o.price]
            
            # Filter orders within ±2% range
            orders_in_range = []
            buy_liquidity_in_range = 0
            sell_liquidity_in_range = 0
            buy_value_in_range = 0
            sell_value_in_range = 0
            
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
            
            print(f"   Orders in Range: {len(orders_in_range)}/{len(symbol_orders)} ({len(orders_in_range)/max(len(symbol_orders), 1)*100:.1f}%)")
            print(f"   Buy Liquidity: {buy_liquidity_in_range:,.4f} (${buy_value_in_range:,.2f})")
            print(f"   Sell Liquidity: {sell_liquidity_in_range:,.4f} (${sell_value_in_range:,.2f})")
            print(f"   Total Liquidity: {buy_liquidity_in_range + sell_liquidity_in_range:,.4f}")
            print()
            
            # Display order book visualization
            _display_order_book_visualization(symbol_orders, current_mid, lower_bound, upper_bound)
            
        else:
            print(f"❌ Could not fetch market data for {order_symbol}")
        
        # Your spread analysis
        symbol_buy_orders = [o for o in filtered_orders if o.symbol == order_symbol and float(o.amount) > 0 and o.price]
        symbol_sell_orders = [o for o in filtered_orders if o.symbol == order_symbol and float(o.amount) < 0 and o.price]
        
        if symbol_buy_orders and symbol_sell_orders:
            buy_prices = [float(o.price) for o in symbol_buy_orders]
            sell_prices = [float(o.price) for o in symbol_sell_orders]
            highest_buy = max(buy_prices)
            lowest_sell = min(sell_prices)
            your_spread = lowest_sell - highest_buy
            your_mid = (highest_buy + lowest_sell) / 2
            your_spread_pct = (your_spread / your_mid) * 100 if your_mid > 0 else 0
            
            print(f"📊 Your Order Spread Analysis:")
            print(f"   Highest Buy: ${highest_buy:.6f}")
            print(f"   Lowest Sell: ${lowest_sell:.6f}")
            print(f"   Your Spread: ${your_spread:.6f} ({your_spread_pct:.3f}%)")
            
            # Compare with market spread
            if ticker:
                spread_efficiency = your_spread / market_spread if market_spread > 0 else float('inf')
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
    print(f"🔢 Order Counts:")
    print(f"   Total Orders: {len(filtered_orders)}")
    print(f"   Buy Orders: {len(buy_orders)} ({len(buy_orders)/len(filtered_orders)*100:.1f}%)")
    print(f"   Sell Orders: {len(sell_orders)} ({len(sell_orders)/len(filtered_orders)*100:.1f}%)")
    print()
    
    print(f"💰 Amount Summary:")
    print(f"   Total Buy Amount: {total_buy_amount:,.4f}")
    print(f"   Total Sell Amount: {total_sell_amount:,.4f}")
    if total_buy_value > 0:
        print(f"   Total Buy Value: ${total_buy_value:,.2f}")
    if total_sell_value > 0:
        print(f"   Total Sell Value: ${total_sell_value:,.2f}")
    print()
    
    # Risk assessment
    print(f"⚠️  Risk Assessment:")
    if total_buy_value > 0 and total_sell_value > 0:
        net_exposure = total_buy_value - total_sell_value
        print(f"   Net Exposure: ${net_exposure:+,.2f}")
        exposure_ratio = abs(net_exposure) / max(total_buy_value, total_sell_value)
        if exposure_ratio > 0.2:
            print(f"   ❌ High imbalance ({exposure_ratio*100:.1f}%)")
        elif exposure_ratio > 0.1:
            print(f"   ⚠️  Moderate imbalance ({exposure_ratio*100:.1f}%)")
        else:
            print(f"   ✅ Well balanced ({exposure_ratio*100:.1f}%)")
    
    balance_ratio = len(buy_orders) / len(sell_orders) if sell_orders else float('inf')
    if 0.5 <= balance_ratio <= 2:
        print(f"   ✅ Good order count balance ({len(buy_orders)}:{len(sell_orders)})")
    else:
        print(f"   ⚠️  Order count imbalance ({len(buy_orders)}:{len(sell_orders)})")
    
    print("═" * 80)
    return filtered_orders


def _display_order_book_visualization(orders, mid_price, lower_bound, upper_bound):
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
            price_levels[price] = {'buy': 0, 'sell': 0}
        
        if amount > 0:
            price_levels[price]['buy'] += abs(amount)
        else:
            price_levels[price]['sell'] += abs(amount)
    
    # Sort prices
    sorted_prices = sorted(price_levels.keys(), reverse=True)
    
    # Find max amount for scaling
    max_amount = 0
    for price_data in price_levels.values():
        max_amount = max(max_amount, price_data['buy'], price_data['sell'])
    
    if max_amount == 0:
        print("   No liquidity in range")
        return
    
    # Display the visualization
    print("   " + "─" * 60)
    print(f"   {'Price':<12} {'Sell':<15} {'|':<3} {'Buy':<15}")
    print("   " + "─" * 60)
    
    for price in sorted_prices:
        buy_amount = price_levels[price]['buy']
        sell_amount = price_levels[price]['sell']
        
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