"""
Pytest configuration and shared fixtures for Maker-Kit tests.

Provides comprehensive test configuration, fixtures, and utilities
for all test categories including unit, integration, and performance tests.
"""

import asyncio
import os
import tempfile
import time
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.order_id import OrderId
from bitfinex_maker_kit.domain.price import Price

# Import project modules
from bitfinex_maker_kit.domain.symbol import Symbol
from bitfinex_maker_kit.services.cache_service import CacheService, create_cache_service
from bitfinex_maker_kit.services.container import ServiceContainer, get_container
from bitfinex_maker_kit.services.performance_monitor import (
    PerformanceMonitor,
    create_performance_monitor,
)
from bitfinex_maker_kit.utilities.profiler import PerformanceProfiler, create_profiler


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: mark test as unit test (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (slower, requires setup)"
    )
    config.addinivalue_line("markers", "performance: mark test as performance test (benchmarking)")
    config.addinivalue_line("markers", "load: mark test as load test (stress testing)")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "api: mark test as requiring API access")
    config.addinivalue_line("markers", "websocket: mark test as requiring WebSocket functionality")
    config.addinivalue_line("markers", "cache: mark test as cache-related")
    config.addinivalue_line("markers", "async_test: mark test as async test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "load" in str(item.fspath):
            item.add_marker(pytest.mark.load)

        # Add async marker for async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.async_test)


# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Domain object fixtures
@pytest.fixture
def sample_symbol() -> Symbol:
    """Create sample trading symbol."""
    return Symbol("tBTCUSD")


@pytest.fixture
def sample_price() -> Price:
    """Create sample price."""
    return Price("50000.0")


@pytest.fixture
def sample_amount() -> Amount:
    """Create sample amount."""
    return Amount("0.1")


@pytest.fixture
def sample_order_id() -> OrderId:
    """Create sample order ID."""
    return OrderId("12345678")


@pytest.fixture
def multiple_symbols() -> list[Symbol]:
    """Create list of sample symbols."""
    return [
        Symbol("tBTCUSD"),
        Symbol("tETHUSD"),
        Symbol("tPNKUSD"),
        Symbol("tLTCUSD"),
        Symbol("tXRPUSD"),
    ]


# Mock API responses fixtures
@pytest.fixture
def mock_ticker_response() -> dict[str, Any]:
    """Mock ticker API response."""
    return {
        "symbol": "tBTCUSD",
        "bid": 49950.0,
        "ask": 50050.0,
        "last_price": 50000.0,
        "bid_size": 1.5,
        "ask_size": 2.0,
        "volume": 1000.0,
        "high": 51000.0,
        "low": 49000.0,
        "timestamp": time.time(),
    }


@pytest.fixture
def mock_order_response() -> dict[str, Any]:
    """Mock order API response."""
    return {
        "id": 12345678,
        "symbol": "tBTCUSD",
        "amount": "0.1",
        "price": "50000.0",
        "side": "buy",
        "type": "EXCHANGE LIMIT",
        "status": "ACTIVE",
        "timestamp": time.time(),
        "flags": 512,  # POST_ONLY flag
    }


@pytest.fixture
def mock_orders_list() -> list[dict[str, Any]]:
    """Mock list of orders."""
    return [
        {
            "id": 12345678,
            "symbol": "tBTCUSD",
            "amount": "0.1",
            "price": "50000.0",
            "side": "buy",
            "type": "EXCHANGE LIMIT",
            "status": "ACTIVE",
        },
        {
            "id": 12345679,
            "symbol": "tBTCUSD",
            "amount": "-0.1",
            "price": "50100.0",
            "side": "sell",
            "type": "EXCHANGE LIMIT",
            "status": "ACTIVE",
        },
    ]


@pytest.fixture
def mock_wallet_response() -> list[dict[str, Any]]:
    """Mock wallet API response."""
    return [
        {"currency": "USD", "type": "exchange", "balance": 10000.0, "available": 9500.0},
        {"currency": "BTC", "type": "exchange", "balance": 1.0, "available": 0.9},
    ]


# Mock client fixtures
@pytest.fixture
def mock_bitfinex_client():
    """Create mock Bitfinex client."""
    client = Mock()

    # Configure mock methods
    client.get_ticker = Mock()
    client.get_orderbook = Mock()
    client.get_trades = Mock()
    client.get_wallets = Mock()
    client.submit_order = Mock()
    client.cancel_order = Mock()
    client.get_orders = Mock()
    client.get_order_status = Mock()

    return client


@pytest.fixture
async def mock_async_client():
    """Create mock async client."""
    client = AsyncMock()

    # Configure async mock methods
    client.get_ticker = AsyncMock()
    client.get_orderbook = AsyncMock()
    client.get_trades = AsyncMock()
    client.get_wallets = AsyncMock()
    client.submit_order = AsyncMock()
    client.cancel_order = AsyncMock()
    client.get_orders = AsyncMock()
    client.get_order_status = AsyncMock()

    return client


# Service fixtures
@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_config() -> dict[str, Any]:
    """Test configuration."""
    return {
        "api_key": "test_api_key",
        "api_secret": "test_api_secret",
        "base_url": "https://api-pub.bitfinex.com",
        "websocket_url": "wss://api-pub.bitfinex.com/ws/2",
        "rate_limit": 60,
        "timeout": 30.0,
        "max_retries": 3,
    }


@pytest.fixture
async def cache_service() -> AsyncGenerator[CacheService, None]:
    """Create cache service for testing."""
    service = create_cache_service(max_size=100, default_ttl=10.0)
    yield service
    await service.cleanup()


@pytest.fixture
def performance_monitor() -> Generator[PerformanceMonitor, None]:
    """Create performance monitor for testing."""
    monitor = create_performance_monitor(monitoring_interval=1.0, retention_period=60.0)
    monitor.start_monitoring()
    yield monitor
    asyncio.create_task(monitor.stop_monitoring())


@pytest.fixture
def profiler() -> PerformanceProfiler:
    """Create profiler for testing."""
    return create_profiler(enable_memory_tracking=False)  # Disable for tests


@pytest.fixture
async def service_container(
    mock_bitfinex_client, test_config
) -> AsyncGenerator[ServiceContainer, None]:
    """Create service container for testing."""
    container = get_container()
    container.configure(test_config)

    # Mock the client creation
    with patch.object(container, "_create_bitfinex_client", return_value=mock_bitfinex_client):
        yield container

    await container.cleanup()


# Environment fixtures
@pytest.fixture
def env_vars() -> Generator[None, None, None]:
    """Set test environment variables."""
    test_env = {
        "BITFINEX_API_KEY": "test_key",
        "BITFINEX_API_SECRET": "test_secret",
        "MAKER_KIT_ENV": "test",
    }

    # Save original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def no_api_key_env() -> Generator[None, None, None]:
    """Remove API key from environment."""
    original_key = os.environ.get("BITFINEX_API_KEY")
    original_secret = os.environ.get("BITFINEX_API_SECRET")

    os.environ.pop("BITFINEX_API_KEY", None)
    os.environ.pop("BITFINEX_API_SECRET", None)

    yield

    # Restore original values
    if original_key:
        os.environ["BITFINEX_API_KEY"] = original_key
    if original_secret:
        os.environ["BITFINEX_API_SECRET"] = original_secret


# Test data fixtures
@pytest.fixture
def market_data_sample() -> dict[str, Any]:
    """Sample market data for testing."""
    return {
        "ticker": {
            "symbol": "tBTCUSD",
            "bid": 49950.0,
            "ask": 50050.0,
            "last_price": 50000.0,
            "volume": 1000.0,
        },
        "orderbook": {
            "symbol": "tBTCUSD",
            "bids": [[49950.0, 1.0], [49940.0, 2.0], [49930.0, 1.5]],
            "asks": [[50050.0, 1.0], [50060.0, 2.0], [50070.0, 1.5]],
        },
        "trades": [
            {"price": 50000.0, "amount": 0.1, "timestamp": time.time()},
            {"price": 49995.0, "amount": 0.2, "timestamp": time.time() - 60},
        ],
    }


@pytest.fixture
def order_scenarios() -> dict[str, dict[str, Any]]:
    """Various order scenarios for testing."""
    return {
        "valid_buy_order": {
            "symbol": "tBTCUSD",
            "amount": "0.1",
            "price": "49000.0",
            "side": "buy",
            "type": "EXCHANGE LIMIT",
        },
        "valid_sell_order": {
            "symbol": "tBTCUSD",
            "amount": "0.1",
            "price": "51000.0",
            "side": "sell",
            "type": "EXCHANGE LIMIT",
        },
        "invalid_amount": {
            "symbol": "tBTCUSD",
            "amount": "0.0",
            "price": "50000.0",
            "side": "buy",
            "type": "EXCHANGE LIMIT",
        },
        "invalid_price": {
            "symbol": "tBTCUSD",
            "amount": "0.1",
            "price": "0.0",
            "side": "buy",
            "type": "EXCHANGE LIMIT",
        },
    }


# Performance test fixtures
@pytest.fixture
def performance_thresholds() -> dict[str, float]:
    """Performance test thresholds."""
    return {
        "api_response_time_ms": 1000.0,
        "cache_hit_ratio": 0.8,
        "memory_usage_mb": 500.0,
        "cpu_usage_pct": 50.0,
        "order_processing_time_ms": 100.0,
    }


# WebSocket fixtures
@pytest.fixture
def mock_websocket():
    """Create mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


@pytest.fixture
def websocket_messages() -> list[dict[str, Any]]:
    """Sample WebSocket messages."""
    return [
        {"event": "subscribed", "channel": "ticker", "symbol": "tBTCUSD", "chanId": 1},
        {
            "event": "update",
            "channel": "ticker",
            "data": [
                1,
                50000.0,
                0.1,
                50050.0,
                0.2,
                100.0,
                0.002,
                50000.0,
                1000.0,
                51000.0,
                49000.0,
            ],
        },
    ]


# Error simulation fixtures
@pytest.fixture
def api_error_scenarios() -> dict[str, Exception]:
    """API error scenarios for testing."""
    return {
        "network_error": ConnectionError("Network connection failed"),
        "api_error": Exception("API rate limit exceeded"),
        "auth_error": Exception("Invalid API credentials"),
        "invalid_symbol": Exception("Invalid trading symbol"),
        "insufficient_balance": Exception("Insufficient account balance"),
    }


# Utility functions for tests
@pytest.fixture
def assert_performance():
    """Performance assertion helper."""

    def _assert_performance(operation_time: float, threshold: float, operation_name: str):
        """Assert operation performance meets threshold."""
        assert operation_time <= threshold, (
            f"{operation_name} took {operation_time:.3f}s, exceeding threshold of {threshold:.3f}s"
        )

    return _assert_performance


@pytest.fixture
def capture_logs():
    """Log capture utility."""
    import logging
    from io import StringIO

    def _capture_logs(logger_name: str | None = None):
        """Capture logs for testing."""
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)

        logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        return log_capture, handler, logger

    return _capture_logs


# Test isolation helpers
@pytest.fixture(autouse=True)
def isolate_tests():
    """Ensure test isolation."""
    # Clear any global state before each test
    yield
    # Clean up after each test


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=["memory", "redis"])
def cache_backend_type(request):
    """Parametrized cache backend types."""
    return request.param


@pytest.fixture(params=[1, 5, 10, 50])
def batch_sizes(request):
    """Parametrized batch sizes for testing."""
    return request.param


@pytest.fixture(params=[0.1, 1.0, 5.0])
def timeout_values(request):
    """Parametrized timeout values for testing."""
    return request.param
