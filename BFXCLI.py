#!/usr/bin/env python3

import argparse
import asyncio
import os
import sys
import signal
from datetime import datetime
from typing import Optional, Dict, Any, List

from bfxapi import Client, WSS_HOST
from bfxapi.types import Order, Notification

def get_credentials():
    """Get API credentials from environment variables or .env file"""
    # First try environment variables
    api_key = os.getenv("BFX_API_KEY")
    api_secret = os.getenv("BFX_API_SECRET")
    
    # If not found in env vars, try loading from .env file
    if not api_key or not api_secret:
        env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == "BFX_API_KEY":
                                api_key = value
                            elif key == "BFX_API_SECRET":
                                api_secret = value
                
                if api_key and api_secret:
                    # Only show this message once per session
                    if not hasattr(get_credentials, '_shown_env_message'):
                        print("📁 Loaded API credentials from .env file")
                        get_credentials._shown_env_message = True
            except Exception as e:
                print(f"⚠️  Error reading .env file: {e}")
    
    if not api_key or not api_secret:
        print("❌ Error: Missing required API credentials!")
        print()
        print("📋 Set credentials using one of these methods:")
        print()
        print("Method 1: Environment Variables")
        print("  export BFX_API_KEY='your_api_key_here'")
        print("  export BFX_API_SECRET='your_api_secret_here'")
        print()
        print("Method 2: Create a .env file in the same directory as this script:")
        print("  echo 'BFX_API_KEY=your_api_key_here' > .env")
        print("  echo 'BFX_API_SECRET=your_api_secret_here' >> .env")
        print()
        print("📖 To get API keys:")
        print("  1. Log into Bitfinex")
        print("  2. Go to Settings → API")
        print("  3. Create new key with trading permissions")
        print("  4. Save the API key and secret")
        sys.exit(1)
    
    return api_key, api_secret

def create_client():
    """Create and return a Bitfinex client instance"""
    api_key, api_secret = get_credentials()
    return Client(
        wss_host=WSS_HOST,
        api_key=api_key,
        api_secret=api_secret
    )

def test_api_connection():
    """Test API connection by calling wallets endpoint"""
    print("Testing API connection...")
    
    try:
        client = create_client()
    except SystemExit:
        return False
    
    try:
        wallets = client.rest.auth.get_wallets()
        print("✅ API connection successful!")
        print(f"Found {len(wallets)} wallets")
        return True
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def get_wallets():
    """Get and display wallet balances"""
    client = create_client()
    
    try:
        wallets = client.rest.auth.get_wallets()
        
        print(f"\n💰 Wallet Balances:")
        print("─" * 60)
        print(f"{'Type':<15} {'Currency':<10} {'Balance':<15} {'Available':<15}")
        print("─" * 60)
        
        for wallet in wallets:
            wallet_type = wallet.wallet_type
            currency = wallet.currency
            balance = float(wallet.balance)
            available = float(wallet.available_balance)
            
            # Only show non-zero balances
            if balance != 0 or available != 0:
                print(f"{wallet_type:<15} {currency:<10} {balance:<15.6f} {available:<15.6f}")
        
        print("─" * 60)
        return wallets
    except Exception as e:
        print(f"❌ Failed to get wallet data: {e}")
        return []

def get_ticker_data(symbol: str):
    """Get ticker data for a symbol"""
    client = create_client()
    
    try:
        ticker = client.rest.public.get_t_ticker(symbol)
        return {
            'bid': float(ticker.bid),
            'ask': float(ticker.ask),
            'last_price': float(ticker.last_price),
            'bid_size': float(ticker.bid_size),
            'ask_size': float(ticker.ask_size)
        }
    except Exception as e:
        print(f"❌ Failed to get ticker data: {e}")
        return None

def get_last_trade(symbol: str):
    """Get the most recent trade for a symbol"""
    client = create_client()
    
    try:
        trades = client.rest.public.get_t_trades(symbol, limit=1)
        if trades:
            return float(trades[0].price)
        else:
            print("No recent trades found")
            return None
    except Exception as e:
        print(f"❌ Failed to get trade data: {e}")
        return None

def suggest_price_centers(symbol: str):
    """Suggest appropriate price centers based on market data"""
    print(f"Analyzing market data for {symbol}...")
    
    ticker = get_ticker_data(symbol)
    if not ticker:
        return None
    
    last_trade = get_last_trade(symbol)
    
    print(f"\n📊 Market Data for {symbol}:")
    print(f"   Best Bid: ${ticker['bid']:.6f} (Size: {ticker['bid_size']:.2f})")
    print(f"   Best Ask: ${ticker['ask']:.6f} (Size: {ticker['ask_size']:.2f})")
    print(f"   Last Price: ${ticker['last_price']:.6f}")
    if last_trade:
        print(f"   Latest Trade: ${last_trade:.6f}")
    
    mid_price = (ticker['bid'] + ticker['ask']) / 2
    spread = ticker['ask'] - ticker['bid']
    spread_pct = (spread / mid_price) * 100
    
    print(f"\n💡 Suggested Price Centers:")
    print(f"   1. Mid Price: ${mid_price:.6f} (between bid/ask)")
    print(f"   2. Last Price: ${ticker['last_price']:.6f}")
    if last_trade and abs(last_trade - ticker['last_price']) > 0.000001:
        print(f"   3. Latest Trade: ${last_trade:.6f}")
    
    print(f"\n📈 Market Info:")
    print(f"   Spread: ${spread:.6f} ({spread_pct:.3f}%)")
    
    return {
        'mid_price': mid_price,
        'last_price': ticker['last_price'],
        'latest_trade': last_trade,
        'bid': ticker['bid'],
        'ask': ticker['ask'],
        'spread': spread,
        'spread_pct': spread_pct
    }

def validate_center_price(symbol: str, center_price: float, ignore_validation: bool = False):
    """Validate that center price is within the current bid-ask spread"""
    ticker = get_ticker_data(symbol)
    if not ticker:
        print("❌ Failed to get market data for validation")
        return False, None

    bid = ticker['bid']
    ask = ticker['ask']

    if ignore_validation:
        print(f"⚠️  Price validation IGNORED - using center price ${center_price:.6f}")
        print(f"   Current spread: ${bid:.6f} - ${ask:.6f}")
        return True, {'bid': bid, 'ask': ask}

    if center_price <= bid:
        print(f"❌ Invalid center price: ${center_price:.6f} is at or below current best bid (${bid:.6f})")
        print(f"   Center price must be above the best bid for meaningful market making")
        print(f"   💡 Valid range: ${bid:.6f} < center price < ${ask:.6f}")
        print(f"   💡 Use --ignore-validation flag to bypass this check")
        return False, {'bid': bid, 'ask': ask}

    if center_price >= ask:
        print(f"❌ Invalid center price: ${center_price:.6f} is at or above current best ask (${ask:.6f})")
        print(f"   Center price must be below the best ask for meaningful market making")
        print(f"   💡 Valid range: ${bid:.6f} < center price < ${ask:.6f}")
        print(f"   💡 Use --ignore-validation flag to bypass this check")
        return False, {'bid': bid, 'ask': ask}

    print(f"✅ Center price ${center_price:.6f} is valid (within spread: ${bid:.6f} - ${ask:.6f})")
    return True, {'bid': bid, 'ask': ask}

def resolve_center_price(symbol: str, center_input: str):
    """Resolve center price from string input (numeric value or 'mid-range')"""
    if center_input.lower() == "mid-range":
        ticker = get_ticker_data(symbol)
        if not ticker:
            print("❌ Failed to get market data for mid-range calculation")
            return None
        
        mid_price = (ticker['bid'] + ticker['ask']) / 2
        print(f"📍 Using mid-range center: ${mid_price:.6f}")
        return mid_price
    else:
        try:
            center_price = float(center_input)
            print(f"📍 Using custom center: ${center_price:.6f}")
            return center_price
        except ValueError:
            print(f"❌ Invalid center value: '{center_input}'. Use a number or 'mid-range'")
            return None

def list_orders(symbol: Optional[str] = None):
    """List all active orders or orders for a specific symbol"""
    print("Fetching active orders...")
    
    client = create_client()
    
    try:
        orders = client.rest.auth.get_orders()
        
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
            print(f"🔹 {order_symbol}:")
            print("─" * 80)
            print(f"{'ID':<12} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15} {'Created':<20}")
            print("─" * 80)
            
            for order in orders:
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
    except Exception as e:
        print(f"❌ Failed to get orders: {e}")
        return []

def cancel_order(order_id: int):
    """Cancel a specific order by ID"""
    client = create_client()
    
    try:
        # Try different parameter formats for cancel_order
        # Maybe it expects keyword arguments or different data structure
        result = client.rest.auth.cancel_order(id=order_id)
        return True, "Order cancelled successfully"
    except Exception as e:
        # If that fails, let's explore what methods are available
        try:
            methods = [method for method in dir(client.rest.auth) if 'cancel' in method.lower()]
            return False, f"cancel_order failed: {e}. Available cancel methods: {methods}"
        except:
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
        result = client.rest.auth.cancel_order_multi(id=order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}")

def cancel_orders_by_criteria(size: Optional[float] = None, direction: Optional[str] = None, 
                             symbol: Optional[str] = None, dry_run: bool = False):
    """Cancel orders matching specific criteria (size, direction, symbol)"""
    
    # Build description of what we're looking for
    criteria_parts = []
    if size is not None:
        criteria_parts.append(f"size {size}")
    if direction:
        criteria_parts.append(f"direction {direction.upper()}")
    if symbol:
        criteria_parts.append(f"symbol {symbol}")
    
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
        result = client.rest.auth.cancel_order_multi(id=order_ids)
        print(f"\n✅ Successfully submitted bulk cancellation request for {len(order_ids)} orders")
        print(f"📊 Summary: {len(order_ids)} orders cancelled")
    except Exception as e:
        print(f"\n❌ Failed to cancel orders in bulk: {e}")
        print(f"📊 Summary: 0 cancelled, {len(order_ids)} failed")

class AutoMarketMaker:
    """Auto market maker using the official Bitfinex library"""
    
    def __init__(self, symbol: str, center_price: float, levels: int, spread_pct: float, 
                 size: float, side_filter: Optional[str] = None, test_only: bool = False,
                 ignore_validation: bool = False, post_only: bool = True):
        self.symbol = symbol
        self.initial_center = center_price
        self.current_center = center_price
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter
        self.test_only = test_only
        self.ignore_validation = ignore_validation
        self.post_only = post_only
        self.active_orders = {}  # order_id -> order_info
        self.running = False
        self.replenish_task = None  # For the periodic replenishment task
        
        # Create client
        self.client = create_client()
        
    def validate_initial_price(self):
        """Validate initial center price"""
        is_valid, range_info = validate_center_price(self.symbol, self.initial_center, self.ignore_validation)
        if not is_valid:
            if range_info:
                error_msg = (f"Invalid center price: ${self.initial_center:.6f} is outside the current bid-ask spread. "
                           f"Valid range: ${range_info['bid']:.6f} < center price < ${range_info['ask']:.6f}")
            else:
                error_msg = f"Invalid center price: ${self.initial_center:.6f} (unable to get current market data)"
            raise ValueError(error_msg)
    
    def generate_orders(self, center_price: float):
        """Generate order list for current center price"""
        orders = []
        
        for i in range(1, self.levels + 1):
            if self.side_filter != "sell":
                buy_price = center_price * (1 - (self.spread_pct * i / 100))
                orders.append(("buy", self.size, buy_price))
            
            if self.side_filter != "buy":
                sell_price = center_price * (1 + (self.spread_pct * i / 100))
                orders.append(("sell", self.size, sell_price))
        
        return orders
    
    def place_initial_orders(self):
        """Place initial set of orders"""
        print(f"\n🚀 Placing initial orders around center price ${self.current_center:.6f}")
        
        orders_to_place = self.generate_orders(self.current_center)
        orders_to_place.sort(key=lambda x: x[2])  # Sort by price
        
        for side, amount, price in orders_to_place:
            try:
                # Prepare order parameters
                order_amount = amount if side == "buy" else -amount
                
                # Place order using official client
                # Set flags for POST_ONLY if enabled
                flags = 4096 if self.post_only else 0  # POST_ONLY flag = 4096
                
                response = self.client.rest.auth.submit_order(
                    type="EXCHANGE LIMIT",
                    symbol=self.symbol,
                    amount=order_amount,
                    price=price,
                    flags=flags
                )
                
                order_status = "POST-ONLY" if self.post_only else "LIMIT"
                print(f"✅ {side.upper()} {order_status} order placed: {abs(amount)} @ ${price:.6f}")
                
                # Extract order ID from response - the response format varies
                order_id = None
                try:
                    # Try different response formats from Bitfinex API
                    if hasattr(response, 'data') and response.data:
                        # Response is a Notification with data attribute
                        order_data = response.data
                        if isinstance(order_data, list) and len(order_data) > 0:
                            # Data is a list, get the first order
                            order_id = order_data[0].id if hasattr(order_data[0], 'id') else order_data[0][0]
                        elif hasattr(order_data, 'id'):
                            # Data is a single order object
                            order_id = order_data.id
                    elif hasattr(response, 'notify_info') and response.notify_info:
                        # Alternative response format
                        if isinstance(response.notify_info, list) and len(response.notify_info) > 0:
                            order_id = response.notify_info[0] if isinstance(response.notify_info[0], int) else None
                    elif hasattr(response, 'id'):
                        # Direct order response
                        order_id = response.id
                    elif isinstance(response, list) and len(response) > 0:
                        # Response is a list
                        if hasattr(response[0], 'id'):
                            order_id = response[0].id
                        elif isinstance(response[0], (int, str)):
                            order_id = response[0]
                    
                    # Debug: Print response structure to understand format
                    print(f"🔍 Debug - Response type: {type(response)}")
                    if hasattr(response, '__dict__'):
                        print(f"🔍 Debug - Response attributes: {list(response.__dict__.keys())}")
                    
                    if order_id:
                        # Track the order
                        self.active_orders[order_id] = {
                            'side': side,
                            'amount': abs(amount),
                            'price': price,
                            'id': order_id
                        }
                        print(f"📋 Tracking order ID: {order_id}")
                    else:
                        print(f"⚠️  Order placed but couldn't extract ID for tracking")
                        print(f"🔍 Debug - Full response: {response}")
                        # Still track with a placeholder ID based on price
                        placeholder_id = f"{side}_{price:.6f}_{abs(amount)}"
                        self.active_orders[placeholder_id] = {
                            'side': side,
                            'amount': abs(amount),
                            'price': price,
                            'id': placeholder_id
                        }
                        print(f"📋 Using placeholder ID: {placeholder_id}")
                        
                except Exception as id_error:
                    print(f"⚠️  Order placed but ID extraction failed: {id_error}")
                    print(f"🔍 Debug - Response during error: {response}")
                    # Use placeholder ID
                    placeholder_id = f"{side}_{price:.6f}_{abs(amount)}"
                    self.active_orders[placeholder_id] = {
                        'side': side,
                        'amount': abs(amount),
                        'price': price,
                        'id': placeholder_id
                    }
                    print(f"📋 Using placeholder ID: {placeholder_id}")
                
            except Exception as e:
                if self.post_only and "would have matched" in str(e).lower():
                    print(f"⚠️  {side.upper()} POST-ONLY order @ ${price:.6f} cancelled (would have matched existing order)")
                else:
                    print(f"❌ Failed to place {side.upper()} order: {e}")
    
    def cancel_all_orders(self):
        """Cancel all active orders"""
        if not self.active_orders:
            return
        
        print(f"🗑️  Cancelling {len(self.active_orders)} tracked orders...")
        
        # Extract order IDs for bulk cancellation (excluding placeholder IDs)
        order_ids = []
        placeholder_orders = []
        
        for order_id, order_info in self.active_orders.items():
            if isinstance(order_id, str) and '_' in str(order_id):
                # This looks like a placeholder ID
                placeholder_orders.append((order_id, order_info))
            else:
                # This is a real order ID
                order_ids.append(order_id)
        
        # Cancel real orders using bulk API
        if order_ids:
            try:
                result = self.client.rest.auth.cancel_order_multi(id=order_ids)
                print(f"✅ Successfully submitted bulk cancellation for {len(order_ids)} orders")
            except Exception as e:
                print(f"❌ Failed to cancel orders in bulk: {e}")
        
        # Handle placeholder orders (just remove from tracking)
        if placeholder_orders:
            print(f"🧹 Removing {len(placeholder_orders)} placeholder orders from tracking")
        
        # Clear all tracking
        self.active_orders.clear()
        print("🧹 Order tracking cleared")
    
    def check_and_replenish_orders(self):
        """Check for cancelled orders and replenish them"""
        if not self.active_orders:
            return
        
        try:
            # Get current active orders from exchange
            current_orders = list_orders(self.symbol)
            if current_orders is None:
                current_orders = []
            
            # Create set of currently active order IDs on exchange
            active_order_ids = {order.id for order in current_orders}
            
            # Find orders that we're tracking but are no longer active
            missing_orders = []
            for order_id, order_info in list(self.active_orders.items()):
                if order_id not in active_order_ids:
                    missing_orders.append((order_id, order_info))
                    # Remove from our tracking
                    self.active_orders.pop(order_id, None)
            
            if missing_orders:
                print(f"\n🔄 Found {len(missing_orders)} cancelled orders - replenishing...")
                
                # Replenish each missing order
                for order_id, order_info in missing_orders:
                    side = order_info['side']
                    amount = order_info['amount']
                    price = order_info['price']
                    
                    print(f"   Replenishing {side.upper()} order: {amount} @ ${price:.6f}")
                    
                    try:
                        # Place replacement order
                        order_amount = amount if side == "buy" else -amount
                        
                        # Set flags for POST_ONLY if enabled
                        flags = 4096 if self.post_only else 0  # POST_ONLY flag = 4096
                        
                        response = self.client.rest.auth.submit_order(
                            type="EXCHANGE LIMIT",
                            symbol=self.symbol,
                            amount=order_amount,
                            price=price,
                            flags=flags
                        )
                        
                        # Extract order ID from response
                        new_order_id = None
                        try:
                            # Try different response formats from Bitfinex API
                            if hasattr(response, 'data') and response.data:
                                # Response is a Notification with data attribute
                                order_data = response.data
                                if isinstance(order_data, list) and len(order_data) > 0:
                                    # Data is a list, get the first order
                                    new_order_id = order_data[0].id if hasattr(order_data[0], 'id') else order_data[0][0]
                                elif hasattr(order_data, 'id'):
                                    # Data is a single order object
                                    new_order_id = order_data.id
                            elif hasattr(response, 'notify_info') and response.notify_info:
                                # Alternative response format
                                if isinstance(response.notify_info, list) and len(response.notify_info) > 0:
                                    new_order_id = response.notify_info[0] if isinstance(response.notify_info[0], int) else None
                            elif hasattr(response, 'id'):
                                # Direct order response
                                new_order_id = response.id
                            elif isinstance(response, list) and len(response) > 0:
                                # Response is a list
                                if hasattr(response[0], 'id'):
                                    new_order_id = response[0].id
                                elif isinstance(response[0], (int, str)):
                                    new_order_id = response[0]
                        except:
                            pass
                        
                        if not new_order_id:
                            new_order_id = f"{side}_{price:.6f}_{amount}_replenish"
                        
                        # Track the new order
                        self.active_orders[new_order_id] = {
                            'side': side,
                            'amount': amount,
                            'price': price,
                            'id': new_order_id
                        }
                        order_status = "POST-ONLY" if self.post_only else "LIMIT"
                        print(f"   ✅ Replenished: {side.upper()} {order_status} {amount} @ ${price:.6f} (ID: {new_order_id})")
                        
                    except Exception as e:
                        if self.post_only and "would have matched" in str(e).lower():
                            print(f"   ⚠️  {side.upper()} POST-ONLY replenishment @ ${price:.6f} cancelled (would have matched existing order)")
                        else:
                            print(f"   ❌ Failed to replenish {side.upper()} order: {e}")
            else:
                # Only show status occasionally to avoid spam
                if not hasattr(self, '_check_count'):
                    self._check_count = 0
                self._check_count += 1
                if self._check_count % 10 == 0:  # Every 10th check (5 minutes)
                    print(f"\n✅ Order check #{self._check_count}: All {len(self.active_orders)} orders still active")
            
        except Exception as e:
            print(f"\n❌ Error during order replenishment: {e}")
    
    async def periodic_replenishment(self):
        """Periodic task to replenish cancelled orders every 30 seconds"""
        # Initial delay to let orders settle
        await asyncio.sleep(30)
        
        while self.running:
            try:
                if self.running:  # Check again in case we're shutting down
                    self.check_and_replenish_orders()
                await asyncio.sleep(30)  # Wait 30 seconds for next check
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n❌ Error in periodic replenishment: {e}")
    
    async def adjust_orders(self, new_center: float):
        """Cancel existing orders and place new ones around new center"""
        print(f"\n🎯 Adjusting orders to new center price ${new_center:.6f}")
        print(f"   Previous center: ${self.current_center:.6f}")
        
        self.cancel_all_orders()
        await asyncio.sleep(1)  # Brief pause to ensure cancellations process
        
        self.current_center = new_center
        
        # Show preview of new orders
        new_orders = self.generate_orders(self.current_center)
        new_orders.sort(key=lambda x: x[2])  # Sort by price
        
        print(f"\n📋 New orders to place (sorted by price):")
        print(f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Center':<20}")
        print("─" * 55)
        
        for side, amount, price in new_orders:
            distance_pct = ((price - self.current_center) / self.current_center) * 100
            distance_str = f"{distance_pct:+.3f}%"
            print(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")
        
        print()  # Add spacing before placement results
        self.place_initial_orders()
    
    def setup_websocket_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.client.wss.on("order_update")
        def on_order_update(order: Order):
            order_id = order.id
            
            if order_id in self.active_orders:
                original_order = self.active_orders[order_id]
                
                if "EXECUTED" in order.order_status:
                    fill_price = float(order.price)
                    print(f"\n🎉 Our order FULLY EXECUTED! {original_order['side'].upper()} {original_order['amount']} @ ${fill_price:.6f}")
                    self.active_orders.pop(order_id, None)
                    # Schedule order adjustment
                    asyncio.create_task(self.adjust_orders(fill_price))
                    
                elif "PARTIALLY FILLED" in order.order_status:
                    remaining = abs(float(order.amount))
                    filled_amount = original_order['amount'] - remaining
                    fill_price = float(order.price)
                    print(f"\n📊 Our order PARTIALLY FILLED! {original_order['side'].upper()} {filled_amount:.1f}/{original_order['amount']} @ ${fill_price:.6f}")
                    print(f"   Remaining: {remaining:.1f}")
                    
                    if filled_amount >= original_order['amount'] * 0.5:  # 50% or more filled
                        print(f"   🎯 Significant fill (≥50%) - adjusting center price")
                        asyncio.create_task(self.adjust_orders(fill_price))
                    else:
                        print(f"   ⏳ Waiting for more fills before adjusting")
                        
                elif "CANCELED" in order.order_status:
                    print(f"\n❌ Our order {order_id} was cancelled")
                    self.active_orders.pop(order_id, None)
        
        @self.client.wss.on("order_new")
        def on_order_new(order: Order):
            print(f"\n🆕 New order created: {order.id}")
        
        @self.client.wss.on("authenticated")
        async def on_authenticated(_):
            print("✅ WebSocket authenticated - monitoring order fills")
        
        @self.client.wss.on("on-req-notification")
        def on_notification(notification: Notification):
            if notification.status == "ERROR":
                print(f"\n❌ Order error: {notification.text}")
    
    async def start(self):
        """Start the auto market maker"""
        print(f"\n🤖 Starting Auto Market Maker")
        print(f"   Symbol: {self.symbol}")
        print(f"   Initial Center: ${self.initial_center:.6f}")
        print(f"   Levels: {self.levels}")
        print(f"   Spread: {self.spread_pct:.3f}%")
        print(f"   Size: {self.size}")
        print(f"   Post-Only (Maker): {'✅ Enabled' if self.post_only else '❌ Disabled'}")
        if not self.post_only:
            print(f"   ⚠️  WARNING: POST-ONLY disabled - orders may execute as takers!")
        if self.side_filter:
            print(f"   Side Filter: {self.side_filter.upper()}-ONLY")
        
        # Validate initial price
        self.validate_initial_price()
        
        # Generate and show preview of initial orders
        initial_orders = self.generate_orders(self.initial_center)
        initial_orders.sort(key=lambda x: x[2])  # Sort by price
        
        print(f"\n📋 Initial orders to place (sorted by price):")
        print(f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Center':<20}")
        print("─" * 55)
        
        for side, amount, price in initial_orders:
            distance_pct = ((price - self.initial_center) / self.initial_center) * 100
            distance_str = f"{distance_pct:+.3f}%"
            print(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")
        
        # Ask for confirmation
        order_type = "orders"
        if self.side_filter == "buy":
            order_type = "BUY orders"
        elif self.side_filter == "sell":
            order_type = "SELL orders"
        
        print(f"\n⚠️  Auto-market-maker will:")
        print(f"   • Place these {len(initial_orders)} {order_type}")
        print(f"   • Monitor for fills via WebSocket")
        print(f"   • Automatically adjust center price when orders fill")
        print(f"   • Replenish cancelled orders every 30 seconds")
        print(f"   • Continue running until Ctrl+C")
        
        if not self.test_only:
            response = input(f"\nDo you want to start auto-market-making? (y/N): ")
            if response.lower() != 'y':
                print("❌ Auto market maker cancelled")
                return
        
        # Place initial orders
        self.place_initial_orders()
        
        if not self.active_orders:
            print("❌ No orders were placed successfully. Exiting.")
            return
        
        print(f"\n📊 Successfully placed {len(self.active_orders)} orders")
        
        if self.test_only:
            print("🧪 Test mode - exiting without WebSocket monitoring")
            print("✅ Auto-market-make order placement test successful!")
            return
        
        print(f"\n👂 Listening for order fills... (Press Ctrl+C to stop)")
        
        # Setup WebSocket handlers
        self.setup_websocket_handlers()
        
        # Start WebSocket connection
        self.running = True
        try:
            await self.client.wss.start()
            
            # Start periodic replenishment task
            self.replenish_task = asyncio.create_task(self.periodic_replenishment())
            print(f"🔄 Started periodic order replenishment (every 30 seconds)")
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down auto market maker...")
            await self.stop()
    
    async def stop(self):
        """Stop the auto market maker and clean up"""
        self.running = False
        
        # Cancel periodic replenishment task
        if self.replenish_task:
            self.replenish_task.cancel()
            try:
                await self.replenish_task
            except asyncio.CancelledError:
                pass
            print("🔄 Stopped periodic replenishment")
        
        print("🗑️  Cancelling all remaining orders...")
        self.cancel_all_orders()
        
        await self.client.wss.close()
        print("✅ Auto market maker stopped successfully")

async def auto_market_make(symbol: str, center_price: float, levels: int, spread_pct: float, 
                          size: float, side_filter: Optional[str] = None, test_only: bool = False,
                          ignore_validation: bool = False, post_only: bool = True):
    """Start auto market maker with dynamic center adjustment"""
    
    try:
        amm = AutoMarketMaker(symbol, center_price, levels, spread_pct, size, side_filter, test_only, ignore_validation, post_only)
    except ValueError as e:
        print(f"❌ Failed to start auto market maker: {e}")
        return
    
    # Set up signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal...")
        asyncio.create_task(amm.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await amm.start()

def market_make(symbol: str, center_price: float, levels: int, spread_pct: float, 
                size: float, dry_run: bool = False, side_filter: Optional[str] = None, 
                ignore_validation: bool = False, post_only: bool = True):
    """Create staircase market making orders"""
    
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
    print(f"   Post-Only (Maker): {'✅ Enabled' if post_only else '❌ Disabled'}")
    if not post_only:
        print(f"   ⚠️  WARNING: POST-ONLY disabled - orders may execute as takers!")
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
    
    print(f"\n📋 Orders to place (sorted by price):")
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
    
    response = input(f"\nDo you want to place these {len(orders_to_place)} {order_type}? (y/N): ")
    if response.lower() != 'y':
        print("❌ Market making cancelled")
        return
    
    print("\n🚀 Placing orders...")
    
    client = create_client()
    success_count = 0
    
    for side, amount, price in orders_to_place:
        try:
            order_amount = amount if side == "buy" else -amount
            
            # Set flags for POST_ONLY if enabled
            flags = 4096 if post_only else 0  # POST_ONLY flag = 4096
            
            response = client.rest.auth.submit_order(
                type="EXCHANGE LIMIT",
                symbol=symbol,
                amount=order_amount,
                price=price,
                flags=flags
            )
            
            order_status = "POST-ONLY" if post_only else "LIMIT"
            print(f"✅ {side.upper()} {order_status} order placed: {amount} @ ${price:.6f}")
            success_count += 1
        except Exception as e:
            if post_only and "would have matched" in str(e).lower():
                print(f"⚠️  {side.upper()} POST-ONLY order @ ${price:.6f} cancelled (would have matched existing order)")
            else:
                print(f"❌ Failed to place {side.upper()} order: {e}")
    
    print(f"\n📊 Summary: {success_count}/{len(orders_to_place)} orders placed successfully")

def fill_spread(symbol: str, target_spread_pct: float, order_size: float, 
                center: float = None, dry_run: bool = False, post_only: bool = True):
    """Fill the spread gap with equally spaced orders to achieve spread less than target"""
    
    print(f"\n🎯 Fill Spread Setup:")
    print(f"   Symbol: {symbol}")
    print(f"   Target Max Spread: {target_spread_pct:.3f}%")
    print(f"   Order Size: {order_size}")
    if center:
        print(f"   Center: ${center:.6f}")
    print(f"   Post-Only (Maker): {'✅ Enabled' if post_only else '❌ Disabled'}")
    if not post_only:
        print(f"   ⚠️  WARNING: POST-ONLY disabled - orders may execute as takers!")
    print(f"   Dry Run: {dry_run}")
    
    # Get current market data
    print(f"\nGetting current market data for {symbol}...")
    ticker = get_ticker_data(symbol)
    if not ticker:
        print("❌ Failed to get market data")
        return
    
    current_bid = ticker['bid']
    current_ask = ticker['ask']
    mid_price = (current_bid + current_ask) / 2
    current_spread = current_ask - current_bid
    current_spread_pct = (current_spread / mid_price) * 100
    
    print(f"\n📊 Current Market State:")
    print(f"   Best Bid: ${current_bid:.6f}")
    print(f"   Best Ask: ${current_ask:.6f}")
    print(f"   Mid Price: ${mid_price:.6f}")
    print(f"   Current Spread: ${current_spread:.6f} ({current_spread_pct:.3f}%)")
    
    # Validate target spread
    if target_spread_pct >= current_spread_pct:
        print(f"\n❌ Target spread ({target_spread_pct:.3f}%) must be smaller than current spread ({current_spread_pct:.3f}%)")
        print(f"   💡 Current spread is already {current_spread_pct:.3f}% - target must be less than this")
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
        
        print(f"\n🎯 Target prices around center:")
        print(f"   Target Bid: ${target_bid:.6f}")
        print(f"   Target Ask: ${target_ask:.6f}")
        print(f"   Target Spread: ${target_spread_dollar:.6f} ({target_spread_pct:.3f}%)")
        
        # Place orders at target prices (if they improve the market)
        if target_bid > current_bid:
            orders_to_place.append(("buy", order_size, target_bid))
            print(f"\n📈 Buy order will improve bid: ${current_bid:.6f} → ${target_bid:.6f}")
        else:
            print(f"\n⚠️  Target bid ${target_bid:.6f} would not improve current bid ${current_bid:.6f}")
        
        if target_ask < current_ask:
            orders_to_place.append(("sell", order_size, target_ask))
            print(f"📉 Sell order will improve ask: ${current_ask:.6f} → ${target_ask:.6f}")
        else:
            print(f"\n⚠️  Target ask ${target_ask:.6f} would not improve current ask ${current_ask:.6f}")
            
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
            num_buy_levels = min(max_orders_per_side, max(1, int(tighten_per_side / min_order_spacing)))
            buy_spacing = tighten_per_side / num_buy_levels
            
            print(f"\n📈 Buy side orders ({num_buy_levels} levels):")
            for i in range(1, num_buy_levels + 1):
                buy_price = current_bid + (buy_spacing * i)
                orders_to_place.append(("buy", order_size, buy_price))
                distance_from_mid = ((buy_price - mid_price) / mid_price) * 100
                print(f"   Level {i}: ${buy_price:.6f} ({distance_from_mid:+.3f}% from mid)")
        
        # Place sell orders below current ask (moving toward mid price)  
        if tighten_per_side > min_order_spacing:
            num_sell_levels = min(max_orders_per_side, max(1, int(tighten_per_side / min_order_spacing)))
            sell_spacing = tighten_per_side / num_sell_levels
            
            print(f"\n📉 Sell side orders ({num_sell_levels} levels):")
            for i in range(1, num_sell_levels + 1):
                sell_price = current_ask - (sell_spacing * i)
                orders_to_place.append(("sell", order_size, sell_price))
                distance_from_mid = ((sell_price - mid_price) / mid_price) * 100
                print(f"   Level {i}: ${sell_price:.6f} ({distance_from_mid:+.3f}% from mid)")
    
    if not orders_to_place:
        print(f"\n❌ No orders needed - spread is already tight enough or gaps are too small")
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
        
        print(f"\n💡 Expected Result:")
        print(f"   New Best Bid: ${new_best_bid:.6f}")
        print(f"   New Best Ask: ${new_best_ask:.6f}")
        print(f"   New Spread: ${new_spread:.6f} ({new_spread_pct:.3f}%)")
        print(f"   Improvement: {current_spread_pct - new_spread_pct:.3f}% tighter")
        
        if new_spread_pct <= target_spread_pct:
            print(f"   ✅ Spread target achieved: {new_spread_pct:.3f}% ≤ {target_spread_pct:.3f}%")
        else:
            print(f"   ⚠️  Spread target not fully achieved: {new_spread_pct:.3f}% > {target_spread_pct:.3f}%")
    
    if dry_run:
        print("\n🔍 DRY RUN - No orders will be placed")
        return
    
    # Confirm before placing orders
    response = input(f"\nDo you want to place these {len(orders_to_place)} spread-filling orders? (y/N): ")
    if response.lower() != 'y':
        print("❌ Spread filling cancelled")
        return
    
    print("\n🚀 Placing orders...")
    
    client = create_client()
    success_count = 0
    
    for side, amount, price in orders_to_place:
        try:
            order_amount = amount if side == "buy" else -amount
            
            # Set flags for POST_ONLY if enabled
            flags = 4096 if post_only else 0  # POST_ONLY flag = 4096
            
            response = client.rest.auth.submit_order(
                type="EXCHANGE LIMIT",
                symbol=symbol,
                amount=order_amount,
                price=price,
                flags=flags
            )
            
            order_status = "POST-ONLY" if post_only else "LIMIT"
            print(f"✅ {side.upper()} {order_status} order placed: {amount} @ ${price:.6f}")
            success_count += 1
        except Exception as e:
            if post_only and "would have matched" in str(e).lower():
                print(f"⚠️  {side.upper()} POST-ONLY order @ ${price:.6f} cancelled (would have matched existing order)")
            else:
                print(f"❌ Failed to place {side.upper()} order: {e}")
    
    print(f"\n📊 Summary: {success_count}/{len(orders_to_place)} orders placed successfully")
    
    if success_count > 0:
        print(f"\n✨ Spread filling complete! Check the order book to see the improved liquidity.")

def main():
    parser = argparse.ArgumentParser(description="Bitfinex API CLI Tool (using official library)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Test subcommand
    parser_test = subparsers.add_parser("test", help="Test API connection")
    
    # Wallet subcommand
    parser_wallet = subparsers.add_parser("wallet", help="Show wallet balances")
    
    # Clear subcommand
    parser_clear = subparsers.add_parser("clear", help="Clear all orders on PNK-USD pair")
    
    # Cancel subcommand
    parser_cancel = subparsers.add_parser("cancel", help="Cancel orders by ID or by criteria (size, direction)")
    parser_cancel.add_argument("order_id", type=int, nargs='?', help="Order ID to cancel (required if not using --size)")
    parser_cancel.add_argument("--size", type=float, help="Cancel all orders with this size")
    parser_cancel.add_argument("--direction", choices=['buy', 'sell'], help="Filter by order direction (buy/sell)")
    parser_cancel.add_argument("--symbol", default="tPNKUSD", help="Filter by symbol (default: tPNKUSD)")
    parser_cancel.add_argument("--dry-run", action="store_true", help="Show matching orders without cancelling them")
    
    # List subcommand
    parser_list = subparsers.add_parser("list", help="List active orders")
    parser_list.add_argument("--symbol", default="tPNKUSD", help="Filter orders by symbol (default: tPNKUSD)")
    
    # Market-make subcommand
    parser_mm = subparsers.add_parser("market-make", help="Create staircase market making orders")
    parser_mm.add_argument("--symbol", default="tPNKUSD", help="Trading symbol (default: tPNKUSD)")
    parser_mm.add_argument("--center", help="Center price (numeric value, 'mid-range' for mid-price, or omit for suggestions)")
    parser_mm.add_argument("--levels", type=int, default=3, help="Number of price levels on each side (default: 3)")
    parser_mm.add_argument("--spread", type=float, default=1.0, help="Spread percentage per level (default: 1.0%%)")
    parser_mm.add_argument("--size", type=float, default=10.0, help="Order size for each level (default: 10.0)")
    parser_mm.add_argument("--dry-run", action="store_true", help="Show orders without placing them")
    parser_mm.add_argument("--ignore-validation", action="store_true", help="Ignore center price validation (allows orders outside bid-ask spread)")
    parser_mm.add_argument("--no-post-only", action="store_true", help="Disable POST-ONLY (maker) mode - allows taker orders (NOT RECOMMENDED)")
    
    # Mutually exclusive group for side selection
    side_group = parser_mm.add_mutually_exclusive_group()
    side_group.add_argument("--buy-only", action="store_true", help="Place only buy orders below center price")
    side_group.add_argument("--sell-only", action="store_true", help="Place only sell orders above center price")
    
    # Auto-market-make subcommand
    parser_amm = subparsers.add_parser("auto-market-make", help="Automated market making with dynamic center adjustment")
    parser_amm.add_argument("--symbol", default="tPNKUSD", help="Trading symbol (default: tPNKUSD)")
    parser_amm.add_argument("--center", required=True, help="Initial center price (numeric value or 'mid-range' for mid-price)")
    parser_amm.add_argument("--levels", type=int, default=3, help="Number of price levels on each side (default: 3)")
    parser_amm.add_argument("--spread", type=float, default=1.0, help="Spread percentage per level (default: 1.0%%)")
    parser_amm.add_argument("--size", type=float, default=10.0, help="Order size for each level (default: 10.0)")
    parser_amm.add_argument("--test-only", action="store_true", help="Place orders and exit without WebSocket monitoring (for testing)")
    parser_amm.add_argument("--ignore-validation", action="store_true", help="Ignore center price validation (allows orders outside bid-ask spread)")
    parser_amm.add_argument("--no-post-only", action="store_true", help="Disable POST-ONLY (maker) mode - allows taker orders (NOT RECOMMENDED)")
    
    # Mutually exclusive group for side selection in auto market maker
    auto_side_group = parser_amm.add_mutually_exclusive_group()
    auto_side_group.add_argument("--buy-only", action="store_true", help="Place only buy orders below center price")
    auto_side_group.add_argument("--sell-only", action="store_true", help="Place only sell orders above center price")
    
    # Fill-spread subcommand
    parser_fill = subparsers.add_parser("fill-spread", help="Fill the bid-ask spread gap with equally spaced orders")
    parser_fill.add_argument("--symbol", default="tPNKUSD", help="Trading symbol (default: tPNKUSD)")
    parser_fill.add_argument("--target-spread", type=float, required=True, help="Target maximum spread percentage (final spread will be less than this)")
    parser_fill.add_argument("--size", type=float, required=True, help="Order size for each fill order")
    parser_fill.add_argument("--center", help="Center price for orders (numeric price or 'mid-range' to use mid-price)")
    parser_fill.add_argument("--dry-run", action="store_true", help="Show orders without placing them")
    parser_fill.add_argument("--no-post-only", action="store_true", help="Disable POST-ONLY (maker) mode - allows taker orders (NOT RECOMMENDED)")
    
    args = parser.parse_args()
    
    # Most commands are now synchronous, only async ones need special handling
    def run_command():
        if args.command == "test":
            test_api_connection()
        elif args.command == "wallet":
            get_wallets()
        elif args.command == "clear":
            clear_orders()
        elif args.command == "cancel":
            if args.order_id:
                # Cancel by order ID
                cancel_single_order(args.order_id)
            elif args.size is not None or args.direction or args.symbol:
                # Cancel by criteria
                cancel_orders_by_criteria(args.size, args.direction, args.symbol, args.dry_run)
            else:
                print("❌ Error: Must provide either order_id or criteria (--size, --direction, --symbol)")
                print("Use 'python3 BFXCLI.py cancel --help' for usage information")
        elif args.command == "list":
            list_orders(args.symbol)
        elif args.command == "market-make":
            # Determine side filter
            side_filter = None
            if args.buy_only:
                side_filter = "buy"
            elif args.sell_only:
                side_filter = "sell"
            
            if args.center:
                # Resolve center price from string input
                center_price = resolve_center_price(args.symbol, args.center)
                if center_price is None:
                    return  # Error already printed by resolve_center_price
                
                post_only = not args.no_post_only  # Invert the flag (default is True unless --no-post-only is specified)
                market_make(args.symbol, center_price, args.levels, args.spread, args.size, args.dry_run, side_filter, args.ignore_validation, post_only)
            else:
                centers = suggest_price_centers(args.symbol)
                if centers:
                    side_suffix = ""
                    if side_filter == "buy":
                        side_suffix = " --buy-only"
                    elif side_filter == "sell":
                        side_suffix = " --sell-only"
                    
                    print(f"\nTo create market making orders, run:")
                    print(f"python3 BFXCLI.py market-make --symbol {args.symbol} --center PRICE --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
                    print(f"\nExample using mid price:")
                    print(f"python3 BFXCLI.py market-make --symbol {args.symbol} --center {centers['mid_price']:.6f} --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
                    print(f"\nExample using mid-range:")
                    print(f"python3 BFXCLI.py market-make --symbol {args.symbol} --center mid-range --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
        elif args.command == "auto-market-make":
            # Determine side filter
            side_filter = None
            if args.buy_only:
                side_filter = "buy"
            elif args.sell_only:
                side_filter = "sell"
            
            # Resolve center price from string input
            center_price = resolve_center_price(args.symbol, args.center)
            if center_price is None:
                return  # Error already printed by resolve_center_price
            
            post_only = not args.no_post_only  # Invert the flag (default is True unless --no-post-only is specified)
            asyncio.run(auto_market_make(args.symbol, center_price, args.levels, args.spread, args.size, side_filter, args.test_only, args.ignore_validation, post_only))
        elif args.command == "fill-spread":
            # Resolve center price if provided
            center_price = None
            if args.center:
                center_price = resolve_center_price(args.symbol, args.center)
                if center_price is None:
                    return  # Error already printed by resolve_center_price
            
            post_only = not args.no_post_only  # Invert the flag (default is True unless --no-post-only is specified)
            fill_spread(args.symbol, args.target_spread, args.size, center_price, args.dry_run, post_only)
        else:
            parser.print_help()
    
    # Run the command (only auto-market-make needs async)
    try:
        run_command()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()