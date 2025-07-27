"""
Configuration management for Maker-Kit.

This package provides centralized configuration management,
replacing scattered constants and magic numbers with
proper configuration objects.
"""

from .environment import Environment, get_environment_config
from .trading_config import TradingConfig

__all__ = ["Environment", "TradingConfig", "get_environment_config"]
