"""
Exchange-specific client wrappers and implementations.

This package contains client wrappers for different cryptocurrency exchanges,
providing consistent interfaces and enforcing trading rules specific to each exchange.
"""

from .bitfinex_client import create_wrapper_client, Order, Notification

__all__ = [
    'create_wrapper_client',
    'Order', 
    'Notification'
] 