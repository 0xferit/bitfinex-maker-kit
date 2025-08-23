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

__version__ = "4.7.0"
__author__ = "Maker-Kit Developer"
__description__ = "Bitfinex CLI Tool for Automated Trading and Market Making"

# Core modules
from . import cli, utilities

# Re-export commonly used types from wrapper (maintains API boundary)
from .bitfinex_client import Notification, Order
from .utilities.constants import OrderSide, OrderSubmissionError, OrderType, ValidationError

__all__ = [
    "Notification",
    "Order",
    "OrderSide",
    "OrderSubmissionError",
    "OrderType",
    "ValidationError",
    "cli",
    "utilities",
]
