"""
Service layer for Maker-Kit.

This package provides the service layer architecture with dependency injection,
centralized business logic, and clean abstractions for trading operations.
"""

from .container import ServiceContainer
from .trading_service import TradingService

__all__ = ["ServiceContainer", "TradingService"]
