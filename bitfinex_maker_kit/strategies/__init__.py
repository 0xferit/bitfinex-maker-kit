"""
Trading strategies and order generation utilities.

This package contains pure business logic for generating orders
and calculating prices, separated from execution and UI concerns.
"""

from .order_generator import OrderGenerator

__all__ = ["OrderGenerator"]
