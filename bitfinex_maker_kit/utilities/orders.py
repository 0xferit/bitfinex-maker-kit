"""
Order management operations for Bitfinex CLI.

Core utilities for order submission and management.
REFACTORED: Now supports dependency injection pattern.
"""

from typing import Any

from .client_factory import get_client
from .constants import OrderSide, OrderSubmissionError, ValidationError
from .response_parser import OrderResponseParser


def _extract_order_id(response: Any) -> str | None:
    """
    Extract order ID from API response.

    DEPRECATED: Use OrderResponseParser.extract_order_id() directly.
    This function is maintained for backward compatibility.
    """
    # The OrderResponseParser.extract_order_id returns int | str | None
    # but this function is declared to return str | None
    # We convert int to str for consistency
    result = OrderResponseParser.extract_order_id(response)
    return str(result) if isinstance(result, int) else result


def submit_order(
    symbol: str, side: str | OrderSide, amount: float, price: float | None = None
) -> Any:
    """
    Centralized order submission function that ENFORCES POST_ONLY for all limit orders.

    REFACTORED: Now uses dependency injection with wrapper pattern for better testability
    and maintainability. The wrapper automatically enforces POST_ONLY for all orders.
    Falls back to legacy create_client() for backward compatibility.

    Args:
        symbol: Trading symbol (e.g., "tBTCUSD")
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
        # Get client through centralized factory
        client = get_client()

        # Submit order through wrapper (POST_ONLY automatically enforced)
        return client.submit_order(symbol, side, amount, price)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        # Re-raise OrderSubmissionError as-is, wrap others
        if isinstance(e, OrderSubmissionError):
            raise
        raise OrderSubmissionError(f"Order submission failed: {e}") from e


def cancel_order(order_id: int) -> tuple[bool, str]:
    """Cancel a specific order by ID - with dependency injection support."""
    client = get_client()

    try:
        client.cancel_order(order_id)
        return True, "Order cancelled successfully"
    except Exception as e:
        return False, str(e)


def update_order(
    order_id: int,
    price: float | None = None,
    amount: float | None = None,
    delta: float | None = None,
    use_cancel_recreate: bool = False,
) -> tuple[bool, Any]:
    """Delegate updates through TradingService to keep a single update surface."""
    from ..services.container import get_container

    container = get_container()
    service = container.create_trading_service()
    # Convert primitives to domain objects in service layer; keep this facade minimal
    from ..domain.amount import Amount
    from ..domain.order_id import OrderId
    from ..domain.price import Price

    order_id_obj = OrderId(order_id)
    price_obj = Price(price) if price is not None else None
    amount_obj = Amount(amount) if amount is not None else None
    delta_obj = Amount(delta) if delta is not None else None

    return service.update_order(order_id_obj, price_obj, amount_obj, delta_obj, use_cancel_recreate)
