"""
Order management operations for Bitfinex CLI.

Core utilities for order submission and management.
"""

from typing import Optional, Union
from .auth import create_client
from .constants import OrderSide, ValidationError, OrderSubmissionError


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


def cancel_order(order_id: int):
    """Cancel a specific order by ID"""
    client = create_client()
    
    try:
        result = client.cancel_order(order_id)
        return True, "Order cancelled successfully"
    except Exception as e:
        return False, str(e)


def update_order(order_id: int, price: Optional[float] = None, 
                 amount: Optional[float] = None, delta: Optional[float] = None,
                 use_cancel_recreate: bool = False):
    """
    Update an existing order atomically using WebSocket (default) or cancel-and-recreate.
    
    This function uses the BitfinexClientWrapper which defaults to safer WebSocket
    atomic updates, with cancel-and-recreate as a fallback option.
    
    Args:
        order_id: ID of the order to update
        price: New price for the order
        amount: New absolute amount for the order
        delta: Amount to add/subtract from current amount (alternative to amount)
        use_cancel_recreate: If True, use riskier cancel-and-recreate method
    
    Returns:
        Tuple of (success: bool, result: str or response)
        
    Raises:
        ValidationError: If parameters are invalid
        OrderSubmissionError: If order update fails
    """
    try:
        # Get wrapper client
        client = create_client()
        
        # Update order through wrapper (WebSocket by default, cancel-recreate if requested)
        result = client.update_order(order_id, price, amount, delta, use_cancel_recreate)
        return True, result
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        # Re-raise OrderSubmissionError as-is, wrap others
        if isinstance(e, OrderSubmissionError):
            raise
        return False, str(e) 