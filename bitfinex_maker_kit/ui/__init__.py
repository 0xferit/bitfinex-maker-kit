"""
User interface components for Maker-Kit.

This package handles all user interaction including console output,
prompts, and progress reporting, separated from business logic.
"""

from .market_maker_console import MarketMakerUI

__all__ = ["MarketMakerUI"]
