"""
Bitfinex API Wrapper with POST_ONLY enforcement.

This wrapper class sits between the application and the Bitfinex API library,
enforcing POST_ONLY for all limit orders at the API boundary level.
This makes it architecturally impossible to place non-POST_ONLY limit orders.
"""

from typing import Optional, List, Union
from bfxapi import Client, WSS_HOST
from bfxapi.types import Order, Notification

from .constants import POST_ONLY_FLAG, OrderSide, OrderType, OrderSubmissionError

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