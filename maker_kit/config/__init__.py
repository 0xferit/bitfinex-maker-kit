"""
Configuration management for Maker-Kit.

This package provides centralized configuration management,
replacing scattered constants and magic numbers with
proper configuration objects.
"""

from .trading_config import TradingConfig
from .environment import Environment, get_environment_config

__all__ = ['TradingConfig', 'Environment', 'get_environment_config']