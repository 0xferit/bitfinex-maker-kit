"""
Put command - Place a single order.
"""

from typing import Optional
from decimal import Decimal
from ..utilities.constants import ValidationError, OrderSubmissionError, DEFAULT_SYMBOL
from ..utilities.formatters import format_price, format_amount
from ..utilities.console import (
    print_success, print_error, print_warning, print_info, confirm_action
)
from ..services.container import get_container
from ..domain.symbol import Symbol
from ..domain.price import Price
from ..domain.amount import Amount


def put_command(side: str, amount: float, price: Optional[str] = None, 
              symbol: str = DEFAULT_SYMBOL, dry_run: bool = False, yes: bool = False):
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
    
    if not yes and not confirm_action(f"Do you want to place this order: {order_desc}?"):
        print_error("Order cancelled")
        return
    
    print(f"\n🚀 Placing order...")
    
    try:
        # Create domain objects
        symbol_obj = Symbol(symbol)
        amount_obj = Amount(Decimal(str(amount)))
        price_obj = Price(Decimal(str(price_float))) if price_float else None
        
        # Get trading service through container
        container = get_container()
        trading_service = container.create_trading_service()
        
        # Validate order parameters
        is_valid, error_msg = trading_service.validate_order_parameters(
            symbol_obj, side, amount_obj, price_obj)
        
        if not is_valid:
            raise ValidationError(error_msg)
        
        # Place order using trading service
        success, result = trading_service.place_order(symbol_obj, side, amount_obj, price_obj)
        
        if not success:
            raise OrderSubmissionError(str(result))
        
        # Show success message
        order_status = "MARKET" if is_market_order else "POST-ONLY LIMIT"
        
        success_msg = f"{side.upper()} {order_status} order placed: {format_amount(amount)} {symbol}"
        if not is_market_order:
            success_msg += f" @ {format_price(price_float)}"
        
        # Try to extract order ID from result
        if hasattr(result, 'id'):
            success_msg += f" (ID: {result.id})"
        elif isinstance(result, dict) and 'id' in result:
            success_msg += f" (ID: {result['id']})"
        
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