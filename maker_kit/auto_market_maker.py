"""
Auto market maker implementation for Bitfinex CLI.
"""

import asyncio
import signal
import sys
from typing import Optional
from .bitfinex_client import Order, Notification
from .auth import create_client
from .market_data import validate_center_price
from .orders import list_orders, submit_order


class AutoMarketMaker:
    """Auto market maker using the official Bitfinex library"""
    
    def __init__(self, symbol: str, center_price: float, levels: int, spread_pct: float, 
                 size: float, side_filter: Optional[str] = None, test_only: bool = False,
                 ignore_validation: bool = False):
        self.symbol = symbol
        self.initial_center = center_price
        self.current_center = center_price
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter
        self.test_only = test_only
        self.ignore_validation = ignore_validation
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
                # Use centralized order submission function
                response = submit_order(self.symbol, side, amount, price)
                
                order_status = "POST-ONLY"
                print(f"✅ {side.upper()} {order_status} order placed: {amount} @ ${price:.6f}")
                
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
                if "would have matched" in str(e).lower():
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
                result = self.client.cancel_order_multi(order_ids)
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
                        # Use centralized order submission function
                        response = submit_order(self.symbol, side, amount, price)
                        
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
                        order_status = "POST-ONLY"
                        print(f"   ✅ Replenished: {side.upper()} {order_status} {amount} @ ${price:.6f} (ID: {new_order_id})")
                        
                    except Exception as e:
                        if "would have matched" in str(e).lower():
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
        print(f"   Order Type: POST-ONLY LIMIT (Maker)")
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
        print(f"   • Place these {len(initial_orders)} {order_type} (POST-ONLY)")
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
                          ignore_validation: bool = False):
    """Start auto market maker with dynamic center adjustment"""
    
    try:
        amm = AutoMarketMaker(symbol, center_price, levels, spread_pct, size, side_filter, test_only, ignore_validation)
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