"""
Pure API client for Bitfinex with POST_ONLY enforcement.

This module provides a focused API client that handles only the core API 
communication with POST_ONLY enforcement, separated from business logic.
"""

from typing import Optional, List, Union
from bfxapi import Client, WSS_HOST
from bfxapi.types import Order

from ..utilities.constants import POST_ONLY_FLAG, OrderSide, OrderType, OrderSubmissionError


class BitfinexAPIClient:
    """
    Focused API client that handles only API communication with POST_ONLY enforcement.
    
    This class is responsible solely for:
    - Raw API communication
    - POST_ONLY flag enforcement
    - Basic parameter validation
    - Error handling and retries
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize API client with credentials."""
        self.client = Client(
            wss_host=WSS_HOST,
            api_key=api_key,
            api_secret=api_secret
        )
    
    def submit_order(self, symbol: str, side: Union[str, OrderSide], amount: float, 
                     price: Optional[float] = None) -> dict:
        """
        Submit order with enforced POST_ONLY for limit orders.
        
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
        """
        # Normalize side
        normalized_side = self._normalize_side(side)
        
        # Validate parameters
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
    
    def get_orders(self) -> List[Order]:
        """Get all active orders."""
        try:
            return self.client.rest.auth.get_orders()
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get orders: {e}") from e
    
    def cancel_order(self, order_id: int) -> dict:
        """Cancel a single order by ID."""
        try:
            return self.client.rest.auth.cancel_order(id=order_id)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel order {order_id}: {e}") from e
    
    def cancel_order_multi(self, order_ids: List[int]) -> dict:
        """Cancel multiple orders by IDs."""
        if not order_ids:
            raise ValueError("Order IDs list cannot be empty")
        
        try:
            return self.client.rest.auth.cancel_order_multi(id=order_ids)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel {len(order_ids)} orders: {e}") from e
    
    def get_wallets(self) -> List[dict]:
        """Get wallet balances."""
        try:
            return self.client.rest.auth.get_wallets()
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get wallets: {e}") from e
    
    def get_ticker(self, symbol: str) -> dict:
        """Get ticker data for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        try:
            return self.client.rest.public.get_t_ticker(symbol)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get ticker for {symbol}: {e}") from e
    
    def get_trades(self, symbol: str, limit: int = 1) -> List[dict]:
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
        """Access to WebSocket interface for real-time data."""
        return self.client.wss
    
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


def create_api_client(api_key: str, api_secret: str) -> BitfinexAPIClient:
    """
    Factory function to create Bitfinex API client.
    
    Args:
        api_key: Bitfinex API key
        api_secret: Bitfinex API secret
        
    Returns:
        BitfinexAPIClient instance with POST_ONLY enforcement
    """
    return BitfinexAPIClient(api_key, api_secret)