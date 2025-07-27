"""
Mock utilities package for Maker-Kit tests.

Provides comprehensive mocking utilities for all system components
including API clients, services, and external dependencies.
"""

from .api_mocks import MockAPIResponse, MockBitfinexAPI, MockWebSocketConnection
from .client_mocks import (
    MockAsyncClient,
    MockBitfinexClient,
    create_mock_async_client,
    create_mock_client,
)
from .service_mocks import MockCacheService, MockPerformanceMonitor, MockTradingService

__all__ = [
    "MockAPIResponse",
    "MockAsyncClient",
    # API mocks
    "MockBitfinexAPI",
    # Client mocks
    "MockBitfinexClient",
    "MockCacheService",
    "MockPerformanceMonitor",
    # Service mocks
    "MockTradingService",
    "MockWebSocketConnection",
    "create_mock_async_client",
    "create_mock_client",
]
