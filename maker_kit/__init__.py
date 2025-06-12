"""
Bitfinex CLI Tool - A powerful command-line interface for automated trading and market making.

This package provides comprehensive tools for:
- Market making strategies
- Order management
- Automated trading
- Market data analysis
- Wallet management

All limit orders are enforced to use POST_ONLY flag for maker rebates.
"""

__version__ = "1.0.0"
__author__ = "Maker-Kit Developer"
__description__ = "Bitfinex CLI Tool for Automated Trading and Market Making"

# Core modules
from . import auth
from . import bitfinex_client
from . import constants
from . import utils
from . import market_data
from . import orders
from . import market_making
from . import auto_market_maker
from . import wallet
from . import cli

# Re-export commonly used types from wrapper (maintains API boundary)
from .bitfinex_client import Order, Notification
from .constants import OrderSide, OrderType, ValidationError, OrderSubmissionError

__all__ = [
    'auth',
    'bitfinex_client',
    'constants',
    'utils',
    'market_data', 
    'orders',
    'market_making',
    'auto_market_maker',
    'wallet',
    'cli',
    'Order',
    'Notification',
    'OrderSide',
    'OrderType',
    'ValidationError',
    'OrderSubmissionError'
] 