"""
Trading facade that provides a clean interface to trading operations.

This facade coordinates the API client, order update service, and other 
components to provide a unified trading interface while maintaining 
separation of concerns.
"""

from typing import Optional, List, Union, Dict, Any
from bfxapi.types import Order

from .api_client import BitfinexAPIClient, create_api_client
from .order_update_service import OrderUpdateService, OrderUpdateResult
from ..utilities.constants import OrderSide, OrderSubmissionError


class TradingFacade:
    """
    Facade that provides a clean, unified interface to all trading operations.
    
    This class coordinates multiple focused components to provide the same
    interface as the original BitfinexClientWrapper but with better separation
    of concerns and maintainability.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize trading facade with API credentials."""
        self.api_client = create_api_client(api_key, api_secret)
        self.order_update_service = OrderUpdateService(self.api_client)
    
    def submit_order(self, symbol: str, side: Union[str, OrderSide], amount: float, 
                     price: Optional[float] = None) -> dict:
        """
        Submit order with ENFORCED POST_ONLY for limit orders.
        
        Delegates to the focused API client.
        """
        return self.api_client.submit_order(symbol, side, amount, price)
    
    def get_orders(self) -> List[Order]:
        """Get all active orders."""
        return self.api_client.get_orders()
    
    def cancel_order(self, order_id: int) -> dict:
        """Cancel a single order by ID."""
        return self.api_client.cancel_order(order_id)
    
    def cancel_order_multi(self, order_ids: List[int]) -> dict:
        """Cancel multiple orders by IDs."""
        return self.api_client.cancel_order_multi(order_ids)
    
    def update_order(self, order_id: int, price: Optional[float] = None, 
                     amount: Optional[float] = None, delta: Optional[float] = None,
                     use_cancel_recreate: bool = False) -> Dict[str, Any]:
        """
        Update an existing order using configurable strategies.
        
        Delegates to the focused order update service and converts the result
        to the legacy format for backward compatibility.
        """
        result = self.order_update_service.update_order(
            order_id, price, amount, delta, use_cancel_recreate
        )
        
        if result.success:
            return {
                "method": result.method,
                "status": "success", 
                "order_id": result.order_id,
                "result": result.response_data,
                "message": result.message,
                "new_order": result.response_data.get('new_order') if result.response_data else None
            }
        else:
            # For failed updates, raise an exception with the error message
            raise OrderSubmissionError(result.message)
    
    def get_wallets(self) -> List[dict]:
        """Get wallet balances."""
        return self.api_client.get_wallets()
    
    def get_ticker(self, symbol: str) -> dict:
        """Get ticker data for symbol.""" 
        return self.api_client.get_ticker(symbol)
    
    def get_trades(self, symbol: str, limit: int = 1) -> List[dict]:
        """Get recent trades for symbol."""
        return self.api_client.get_trades(symbol, limit)
    
    @property
    def wss(self):
        """Access to WebSocket interface for real-time data."""
        return self.api_client.wss
    
    def get_api_client(self) -> BitfinexAPIClient:
        """Get the underlying API client for advanced use cases."""
        return self.api_client


def create_trading_facade(api_key: str, api_secret: str) -> TradingFacade:
    """
    Factory function to create trading facade.
    
    Args:
        api_key: Bitfinex API key
        api_secret: Bitfinex API secret
        
    Returns:
        TradingFacade instance with coordinated components
    """
    return TradingFacade(api_key, api_secret)