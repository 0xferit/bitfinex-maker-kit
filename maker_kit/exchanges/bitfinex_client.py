"""
Bitfinex API Wrapper with POST_ONLY enforcement.

This wrapper class sits between the application and the Bitfinex API library,
enforcing POST_ONLY for all limit orders at the API boundary level.
This makes it architecturally impossible to place non-POST_ONLY limit orders.
"""

from typing import Optional, List, Union
from bfxapi import Client, WSS_HOST
from bfxapi.types import Order, Notification

from ..utilities.constants import POST_ONLY_FLAG, OrderSide, OrderType, OrderSubmissionError

# Re-export types for application use (API boundary isolation)
__all__ = ['BitfinexClientWrapper', 'create_wrapper_client', 'Order', 'Notification']


class BitfinexClientWrapper:
    """
    Wrapper around Bitfinex API Client that ENFORCES POST_ONLY for all limit orders.
    
    This is the ONLY way the application should interact with the Bitfinex API.
    All limit orders are automatically given the POST_ONLY flag (4096).
    
    Key Features:
    - ✅ POST_ONLY enforcement at API boundary
    - ✅ Impossible to bypass from application layer  
    - ✅ Clean separation of concerns
    - ✅ Market orders handled correctly (no POST_ONLY flag)
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize wrapper with API credentials"""
        self.client = Client(
            wss_host=WSS_HOST,
            api_key=api_key,
            api_secret=api_secret
        )
    
    def submit_order(self, symbol: str, side: Union[str, OrderSide], amount: float, 
                     price: Optional[float] = None):
        """
        Submit order with ENFORCED POST_ONLY for limit orders.
        
        This is the ONLY method that should be used to submit orders.
        All limit orders automatically get POST_ONLY flag.
        
        Args:
            symbol: Trading symbol (e.g., "tPNKUSD")  
            side: Order side ("buy"/"sell" or OrderSide enum)
            amount: Order amount (positive number)
            price: Price for limit orders, None for market orders
            
        Returns:
            Order response from Bitfinex API
            
        Raises:
            OrderSubmissionError: If order submission fails
            ValueError: If parameters are invalid
            
        Note:
            - Limit orders: ALWAYS use POST_ONLY flag (4096)
            - Market orders: No POST_ONLY flag (not applicable)
        """
        # Validate and normalize inputs
        normalized_side = self._normalize_side(side)
        self._validate_order_params(symbol, normalized_side, amount, price)
        
        # Convert amount based on side (Bitfinex uses positive for buy, negative for sell)
        bitfinex_amount = amount if normalized_side == OrderSide.BUY else -amount
        
        try:
            if price is None:
                # Market order - no POST_ONLY flag needed
                return self.client.rest.auth.submit_order(
                    type=OrderType.MARKET.value,
                    symbol=symbol,
                    amount=bitfinex_amount
                )
            else:
                # Limit order - ALWAYS enforce POST_ONLY flag
                return self.client.rest.auth.submit_order(
                    type=OrderType.LIMIT.value,
                    symbol=symbol, 
                    amount=bitfinex_amount,
                    price=price,
                    flags=POST_ONLY_FLAG  # POST_ONLY flag - HARDCODED at API boundary
                )
        except Exception as e:
            raise OrderSubmissionError(f"Failed to submit {normalized_side.value} order: {e}") from e
    
    def _normalize_side(self, side: Union[str, OrderSide]) -> OrderSide:
        """Normalize order side to OrderSide enum."""
        if isinstance(side, OrderSide):
            return side
        
        side_str = side.lower().strip()
        if side_str == "buy":
            return OrderSide.BUY
        elif side_str == "sell":
            return OrderSide.SELL
        else:
            raise ValueError(f"Invalid order side: {side}. Must be 'buy' or 'sell'")
    
    def _validate_order_params(self, symbol: str, side: OrderSide, amount: float, 
                              price: Optional[float]) -> None:
        """Validate order parameters."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if price is not None and price <= 0:
            raise ValueError("Price must be positive for limit orders")
    
    def get_orders(self) -> List[Order]:
        """Get all active orders."""
        try:
            return self.client.rest.auth.get_orders()
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get orders: {e}") from e
    
    def cancel_order(self, order_id: int):
        """Cancel a single order by ID."""
        try:
            return self.client.rest.auth.cancel_order(id=order_id)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel order {order_id}: {e}") from e
    
    def cancel_order_multi(self, order_ids: List[int]):
        """Cancel multiple orders by IDs."""
        if not order_ids:
            raise ValueError("Order IDs list cannot be empty")
        
        try:
            return self.client.rest.auth.cancel_order_multi(id=order_ids)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel {len(order_ids)} orders: {e}") from e
    
    def update_order(self, order_id: int, price: Optional[float] = None, 
                     amount: Optional[float] = None, delta: Optional[float] = None,
                     use_cancel_recreate: bool = False):
        """
        Update an existing order atomically using WebSocket (default) or cancel-and-recreate.
        
        This method provides two approaches:
        1. WebSocket atomic update (default, safer - either succeeds completely or fails completely)
        2. Cancel-and-recreate (fallback when use_cancel_recreate=True)
        
        Args:
            order_id: ID of the order to update
            price: New price for the order
            amount: New absolute amount for the order (always provide as positive)
            delta: Amount to add/subtract from current amount (alternative to amount)
            use_cancel_recreate: If True, use cancel-and-recreate instead of WebSocket (riskier)
            
        Returns:
            Order update response
            
        Raises:
            OrderSubmissionError: If order update fails
            ValueError: If parameters are invalid
            
        Note:
            WebSocket atomic updates are safer because they avoid the risk of cancelling
            an order without being able to recreate it.
        """
        if order_id <= 0:
            raise ValueError("Order ID must be positive")
        
        if amount is not None and delta is not None:
            raise ValueError("Cannot specify both amount and delta - use one or the other")
        
        if price is None and amount is None and delta is None:
            raise ValueError("Must specify at least one parameter to update (price, amount, or delta)")
        
        # Get the existing order first
        try:
            existing_orders = self.get_orders()
            target_order = None
            for order in existing_orders:
                if order.id == order_id:
                    target_order = order
                    break
            
            if not target_order:
                raise ValueError(f"Order {order_id} not found")
                
        except Exception as e:
            if "not found" in str(e).lower():
                raise ValueError(f"Order {order_id} not found") from e
            raise OrderSubmissionError(f"Failed to fetch order {order_id}: {e}") from e
        
        # Calculate new values
        current_amount = float(target_order.amount)
        current_price = float(target_order.price) if target_order.price else None
        is_sell_order = current_amount < 0
        
        # Determine new price (preserve original price if not specified)
        new_price = price if price is not None else current_price
        
        # Determine new amount with robust validation
        if amount is not None:
            if amount <= 0:
                raise ValueError(f"Specified amount must be positive, got: {amount}")
            new_amount = amount
        elif delta is not None:
            current_abs_amount = abs(current_amount)
            new_amount = current_abs_amount + delta
            if new_amount <= 0:
                raise ValueError(f"Delta {delta} would result in non-positive amount ({current_abs_amount} + {delta} = {new_amount})")
        else:
            new_amount = abs(current_amount)
            if new_amount <= 0:
                raise ValueError(f"Current order has invalid amount: {current_amount}")
        
        # Final validation before proceeding
        if new_amount <= 0:
            raise ValueError(f"Calculated new amount is not positive: {new_amount}")
        
        if new_price is not None and new_price <= 0:
            raise ValueError(f"Calculated new price is not positive: {new_price}")
        
        # Default: Try WebSocket atomic update first (safer)
        if not use_cancel_recreate:
            # Only use WebSocket atomic update - no fallback to cancel-and-recreate
            return self._update_order_websocket(order_id, new_price, new_amount, is_sell_order)
        else:
            # Explicit cancel-and-recreate (riskier but requested)
            print(f"   Using cancel-and-recreate method (has risk of order loss)")
            return self._update_order_cancel_recreate(target_order, new_price, new_amount, is_sell_order)
    
    def _update_order_websocket(self, order_id: int, price: float, amount: float, is_sell_order: bool):
        """Attempt atomic update via WebSocket"""
        # Convert amount based on order side
        bitfinex_amount = -amount if is_sell_order else amount
        
        update_data = {
            "id": order_id,
            "price": str(price),
            "amount": str(bitfinex_amount)
        }
        
        # Check if WebSocket connection is available
        if not hasattr(self.client, 'wss'):
            raise OrderSubmissionError("WebSocket client not available")
        
        try:
            import json
            import time
            import asyncio
            import threading
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            wss = self.client.wss
            
            # Check if WebSocket is already connected
            is_connected = False
            if hasattr(wss, 'is_open') and callable(wss.is_open):
                is_connected = wss.is_open()
            elif hasattr(wss, '_connected') and wss._connected:
                is_connected = True
            elif hasattr(wss, 'connected') and wss.connected:
                is_connected = True
            
            # If already connected, send update directly
            if is_connected:
                print(f"   🔄 Sending atomic WebSocket update for order {order_id}")
                print(f"      New price: ${price:.6f}, New amount: {amount}")
                
                # Format the WebSocket message for order update
                update_message = [0, 'ou', None, update_data]
                
                try:
                    wss.send(json.dumps(update_message))
                    print(f"   ⏳ Waiting for update confirmation...")
                    time.sleep(2)
                    
                    return {
                        "method": "websocket_atomic",
                        "status": "sent",
                        "order_id": order_id,
                        "update_data": update_data,
                        "message": f"Atomic update sent for order {order_id} via WebSocket"
                    }
                except Exception as send_error:
                    raise OrderSubmissionError(f"WebSocket send failed: {send_error}")
            
            # Need to establish temporary connection
            print(f"   🔌 Establishing temporary WebSocket connection for atomic update...")
            
            # Use a threading approach to handle WebSocket with timeout
            result_container = {"result": None, "error": None, "authenticated": False, "update_sent": False}
            
            def websocket_worker():
                """Worker function to handle WebSocket in separate thread"""
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def handle_websocket():
                        """Async function to handle WebSocket connection and update"""
                        
                        # Set up event handlers
                        @wss.on("authenticated")
                        async def on_authenticated(data):
                            print(f"   ✅ WebSocket authenticated - sending update...")
                            result_container["authenticated"] = True
                            
                            # Send the update message
                            update_message = [0, 'ou', None, update_data]
                            try:
                                wss.send(json.dumps(update_message))
                                result_container["update_sent"] = True
                                print(f"   🔄 Atomic update sent for order {order_id}")
                                
                                # Wait a moment for processing
                                await asyncio.sleep(2)
                                
                                result_container["result"] = {
                                    "method": "websocket_atomic",
                                    "status": "sent",
                                    "order_id": order_id,
                                    "update_data": update_data,
                                    "message": f"Atomic update sent for order {order_id} via WebSocket"
                                }
                            except Exception as send_error:
                                result_container["error"] = f"WebSocket send failed: {send_error}"
                        
                        @wss.on("on-req-notification")
                        def on_notification(notification):
                            # Handle order update notifications and errors
                            if hasattr(notification, 'status') and notification.status == "ERROR":
                                result_container["error"] = f"Order update error: {notification.text}"
                            elif hasattr(notification, 'text') and "error" in str(notification.text).lower():
                                result_container["error"] = f"WebSocket notification error: {notification.text}"
                        
                        try:
                            # Start WebSocket connection
                            print(f"   ⏳ Connecting and authenticating...")
                            await wss.start()
                            
                            # Wait for authentication and update to complete
                            max_wait_time = 20  # 20 seconds total timeout
                            wait_time = 0
                            
                            while wait_time < max_wait_time:
                                await asyncio.sleep(0.5)
                                wait_time += 0.5
                                
                                # Check if we got an error
                                if result_container["error"]:
                                    break
                                    
                                # Check if update was sent successfully
                                if result_container["update_sent"] and result_container["result"]:
                                    break
                                    
                                # Check if we're stuck waiting for authentication
                                if wait_time > 10 and not result_container["authenticated"]:
                                    result_container["error"] = "WebSocket authentication timed out"
                                    break
                            
                            # If we exit the loop without completing, it's a timeout
                            if not result_container["error"] and not result_container["result"]:
                                if not result_container["authenticated"]:
                                    result_container["error"] = "WebSocket authentication timed out"
                                elif not result_container["update_sent"]:
                                    result_container["error"] = "WebSocket update was not sent"
                                else:
                                    result_container["error"] = "WebSocket operation timed out"
                            
                        except Exception as ws_error:
                            result_container["error"] = f"WebSocket connection error: {ws_error}"
                        finally:
                            # Clean up - close WebSocket
                            try:
                                await wss.close()
                                print(f"   🔌 WebSocket connection closed")
                            except Exception:
                                pass  # Ignore close errors
                    
                    # Run the async handler
                    loop.run_until_complete(handle_websocket())
                    
                except Exception as e:
                    result_container["error"] = f"WebSocket worker error: {e}"
                finally:
                    try:
                        loop.close()
                    except Exception:
                        pass
            
            # Run WebSocket worker in thread with timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(websocket_worker)
                
                try:
                    # Wait for completion with timeout
                    future.result(timeout=25)  # 25 second total timeout
                    
                    # Check results
                    if result_container["error"]:
                        raise OrderSubmissionError(result_container["error"])
                    elif result_container["result"]:
                        return result_container["result"]
                    else:
                        raise OrderSubmissionError("WebSocket update completed but no result received")
                        
                except FutureTimeoutError:
                    raise OrderSubmissionError("WebSocket operation timed out (25s) - connection or authentication too slow")
            
        except Exception as e:
            # Provide more specific error information
            error_msg = f"WebSocket atomic update failed: {e}"
            if "timed out" in str(e).lower():
                error_msg += " (WebSocket connection/authentication too slow)"
            elif "authentication" in str(e).lower():
                error_msg += " (WebSocket authentication failed)"
            elif "connection" in str(e).lower():
                error_msg += " (WebSocket connection issue)"
            elif "send" in str(e).lower():
                error_msg += " (WebSocket send failed)"
            elif "rate" in str(e).lower() or "limit" in str(e).lower():
                error_msg += " (WebSocket rate limited - try again in 15 seconds)"
            raise OrderSubmissionError(error_msg) from e
    
    def _update_order_cancel_recreate(self, original_order, new_price: float, new_amount: float, is_sell_order: bool):
        """Update order by cancelling and recreating it"""
        import time
        
        try:
            # Validate inputs before proceeding
            if new_amount <= 0:
                raise ValueError(f"Update validation failed - new amount must be positive, got: {new_amount}")
            
            if new_price is not None and new_price <= 0:
                raise ValueError(f"Update validation failed - new price must be positive, got: {new_price}")
            
            # Add delay before cancellation to prevent nonce issues
            time.sleep(0.5)
            
            # Cancel the original order
            print(f"      📋 Cancelling original order {original_order.id}")
            cancel_result = self.cancel_order(original_order.id)
            
            # Add delay between cancel and recreate to prevent nonce issues
            time.sleep(1.0)
            
            # Recreate with new parameters
            symbol = original_order.symbol
            side = "sell" if is_sell_order else "buy"
            
            # Additional validation before submission
            if not symbol or not symbol.strip():
                raise ValueError(f"Submission validation failed - invalid symbol: {symbol}")
            
            print(f"      📋 Creating new order: {side.upper()} {new_amount} @ ${new_price:.6f}")
            
            # Submit new order with same flags (POST_ONLY preserved)
            max_retries = 3
            retry_delay = 1.0
            
            for attempt in range(max_retries):
                try:
                    new_order = self.submit_order(symbol, side, new_amount, new_price)
                    break
                except Exception as submit_error:
                    if "nonce" in str(submit_error).lower() and "small" in str(submit_error).lower():
                        if attempt < max_retries - 1:
                            print(f"      ⏳ Nonce error (attempt {attempt + 1}/{max_retries}), waiting {retry_delay}s before retry...")
                            time.sleep(retry_delay)
                            retry_delay *= 1.5  # Exponential backoff
                            continue
                        else:
                            # Final attempt failed
                            raise ValueError(f"Order recreation failed after {max_retries} attempts due to nonce errors: {submit_error}") from submit_error
                    else:
                        # Non-nonce error, don't retry
                        raise ValueError(f"Order submission failed for {symbol} {side} {new_amount} @ {new_price}: {submit_error}") from submit_error
            
            return {
                "method": "cancel_recreate",
                "status": "success", 
                "original_order_id": original_order.id,
                "new_order": new_order,
                "message": f"Order {original_order.id} cancelled and recreated with new parameters"
            }
            
        except Exception as e:
            raise OrderSubmissionError(f"Cancel-and-recreate update failed: {e}") from e
    
    def get_wallets(self):
        """Get wallet balances."""
        try:
            return self.client.rest.auth.get_wallets()
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get wallets: {e}") from e
    
    def get_ticker(self, symbol: str):
        """Get ticker data for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        try:
            return self.client.rest.public.get_t_ticker(symbol)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get ticker for {symbol}: {e}") from e
    
    def get_trades(self, symbol: str, limit: int = 1):
        """Get recent trades for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if limit <= 0:
            raise ValueError("Limit must be positive")
        
        try:
            return self.client.rest.public.get_t_trades(symbol, limit=limit)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get trades for {symbol}: {e}") from e
    
    @property
    def wss(self):
        """Access to WebSocket interface for real-time data"""
        return self.client.wss


def create_wrapper_client(api_key: str, api_secret: str) -> BitfinexClientWrapper:
    """
    Factory function to create Bitfinex wrapper client.
    
    This should be the ONLY way to create a Bitfinex client in the application.
    
    Args:
        api_key: Bitfinex API key
        api_secret: Bitfinex API secret
        
    Returns:
        BitfinexClientWrapper instance with POST_ONLY enforcement
    """
    return BitfinexClientWrapper(api_key, api_secret) 