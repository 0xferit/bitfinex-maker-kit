"""
Central trading service for Maker-Kit.

Provides a high-level interface for all trading operations,
abstracting the underlying Bitfinex client implementation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from ..bitfinex_client import BitfinexClientWrapper
from ..domain.price import Price
from ..domain.amount import Amount
from ..domain.symbol import Symbol
from ..domain.order_id import OrderId
from ..utilities.constants import ValidationError, OrderSubmissionError

logger = logging.getLogger(__name__)


class TradingService:
    """
    Central service for all trading operations.
    
    Provides a clean, high-level interface for trading operations while
    maintaining all safety guarantees and POST_ONLY enforcement.
    """
    
    def __init__(self, client: BitfinexClientWrapper, config: Dict[str, Any]):
        """
        Initialize trading service.
        
        Args:
            client: Configured Bitfinex client wrapper
            config: Application configuration
        """
        self.client = client
        self.config = config
        logger.info("Trading service initialized")
    
    def get_client(self) -> BitfinexClientWrapper:
        """Get the underlying Bitfinex client."""
        return self.client
    
    def get_config(self) -> Dict[str, Any]:
        """Get the service configuration."""
        return self.config
    
    def place_order(self, symbol: Symbol, side: str, amount: Amount, 
                   price: Optional[Price] = None) -> Tuple[bool, Any]:
        """
        Place a single order with POST_ONLY enforcement.
        
        Args:
            symbol: Trading symbol
            side: Order side ('buy' or 'sell')
            amount: Order amount
            price: Order price (None for market order)
            
        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            logger.info(f"Placing {side} order: {amount} {symbol} @ {price}")
            
            # Convert domain objects to client format
            symbol_str = str(symbol)
            amount_float = float(amount.value)
            price_float = float(price.value) if price else None
            
            # Use client's submit_order method
            from ..utilities.orders import submit_order
            success, result = submit_order(
                symbol=symbol_str,
                amount=amount_float,
                side=side,
                price=price_float,
                client=self.client
            )
            
            if success:
                logger.info(f"Order placed successfully: {result}")
            else:
                logger.error(f"Order placement failed: {result}")
            
            return success, result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False, str(e)
    
    def cancel_order(self, order_id: OrderId) -> Tuple[bool, Any]:
        """
        Cancel an order by ID.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            logger.info(f"Cancelling order {order_id}")
            
            # Handle placeholder orders
            if order_id.is_placeholder():
                logger.warning(f"Cannot cancel placeholder order: {order_id}")
                return False, "Cannot cancel placeholder order"
            
            # Use client's cancel method
            result = self.client.cancel_order(order_id.value)
            
            logger.info(f"Order cancellation result: {result}")
            return True, result
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False, str(e)
    
    def get_orders(self, symbol: Optional[Symbol] = None) -> List[Any]:
        """
        Get active orders, optionally filtered by symbol.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of active orders
        """
        try:
            symbol_str = str(symbol) if symbol else None
            orders = self.client.get_orders(symbol_str)
            
            logger.debug(f"Retrieved {len(orders)} orders")
            return orders
            
        except Exception as e:
            logger.error(f"Error retrieving orders: {e}")
            return []
    
    def get_wallet_balances(self) -> List[Any]:
        """
        Get wallet balances.
        
        Returns:
            List of wallet balance entries
        """
        try:
            balances = self.client.get_wallets()
            logger.debug(f"Retrieved {len(balances)} wallet entries")
            return balances
            
        except Exception as e:
            logger.error(f"Error retrieving wallet balances: {e}")
            return []
    
    def get_ticker(self, symbol: Symbol) -> Optional[Dict[str, Any]]:
        """
        Get ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data or None if error
        """
        try:
            from ..utilities.market_data import get_ticker_data
            ticker = get_ticker_data(str(symbol))
            
            if ticker:
                logger.debug(f"Retrieved ticker for {symbol}")
            else:
                logger.warning(f"No ticker data for {symbol}")
            
            return ticker
            
        except Exception as e:
            logger.error(f"Error retrieving ticker for {symbol}: {e}")
            return None
    
    def update_order(self, order_id: OrderId, price: Optional[Price] = None,
                    amount: Optional[Amount] = None, delta: Optional[Amount] = None,
                    use_cancel_recreate: bool = False) -> Tuple[bool, Any]:
        """
        Update an existing order.
        
        Args:
            order_id: Order ID to update
            price: New price (optional)
            amount: New amount (optional) 
            delta: Amount delta (optional)
            use_cancel_recreate: Force cancel-and-recreate strategy
            
        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            logger.info(f"Updating order {order_id}")
            
            # Handle placeholder orders
            if order_id.is_placeholder():
                logger.warning(f"Cannot update placeholder order: {order_id}")
                return False, "Cannot update placeholder order"
            
            # Convert domain objects to client format
            price_float = float(price.value) if price else None
            amount_float = float(amount.value) if amount else None
            delta_float = float(delta.value) if delta else None
            
            # Use client's update method
            success, result = self.client.update_order(
                order_id=order_id.value,
                price=price_float,
                amount=amount_float,
                delta=delta_float,
                use_cancel_recreate=use_cancel_recreate
            )
            
            if success:
                logger.info(f"Order updated successfully: {result}")
            else:
                logger.error(f"Order update failed: {result}")
            
            return success, result
            
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False, str(e)
    
    def validate_order_parameters(self, symbol: Symbol, side: str, amount: Amount,
                                price: Optional[Price] = None) -> Tuple[bool, str]:
        """
        Validate order parameters before submission.
        
        Args:
            symbol: Trading symbol
            side: Order side
            amount: Order amount
            price: Order price (optional)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic validation
            if side not in ['buy', 'sell']:
                return False, f"Invalid side: {side}"
            
            if amount.value <= 0:
                return False, f"Amount must be positive: {amount}"
            
            if price and price.value <= 0:
                return False, f"Price must be positive: {price}"
            
            # Symbol format validation
            if not str(symbol).startswith('t'):
                return False, f"Symbol must start with 't': {symbol}"
            
            logger.debug(f"Order parameters validated successfully")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating order parameters: {e}")
            return False, str(e)
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current orders.
        
        Returns:
            Dictionary with order statistics
        """
        try:
            orders = self.get_orders()
            
            stats = {
                'total_orders': len(orders),
                'buy_orders': len([o for o in orders if float(o.amount) > 0]),
                'sell_orders': len([o for o in orders if float(o.amount) < 0]),
                'symbols': list(set(o.symbol for o in orders))
            }
            
            logger.debug(f"Generated order statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error generating order statistics: {e}")
            return {
                'total_orders': 0,
                'buy_orders': 0,
                'sell_orders': 0,
                'symbols': []
            }
    
    def close(self) -> None:
        """Close the trading service and clean up resources."""
        try:
            # Close WebSocket if active
            if hasattr(self.client, 'wss') and self.client.wss:
                # Note: Actual WebSocket cleanup would need async context
                pass
            
            logger.info("Trading service closed")
            
        except Exception as e:
            logger.error(f"Error closing trading service: {e}")