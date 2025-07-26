"""
Commands package for the Bitfinex CLI tool.

This package contains individual command modules that provide the main functionality
for the CLI tool. Each command is in its own module for better organization.
"""

from .auto_market_make import auto_market_make_command
from .cancel import cancel_command
from .clear import clear_command
from .fill_spread import fill_spread_command
from .list import list_command
from .market_make import market_make_command
from .put import put_command
from .test import test_command
from .update import update_command
from .wallet import wallet_command

__all__ = [
    "auto_market_make_command",
    "cancel_command",
    "clear_command",
    "fill_spread_command",
    "list_command",
    "market_make_command",
    "put_command",
    "test_command",
    "update_command",
    "wallet_command",
]
