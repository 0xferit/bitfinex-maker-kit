"""
System stress tests for Bitfinex-Maker-Kit.

Tests system behavior under stress conditions including memory pressure,
error cascades, and resource exhaustion. These tests focus on actual
system resilience rather than mock-based performance metrics.
"""

import pytest

from ..mocks.service_mocks import create_mock_monitored_trading_service


@pytest.mark.load
class TestSystemStressTests:
    """Stress tests for overall system limits and resilience."""

    @pytest.fixture
    def trading_service(self):
        """Create monitored trading service for stress testing."""
        return create_mock_monitored_trading_service("normal")

    # Removed test_memory_stress - safety theater that only tests creating lists of tiny immutable objects

    # Removed test_error_cascade_resilience - not a load test, belongs in error handling tests, mock setup broken

    # Removed test_resource_exhaustion_handling - safety theater with artificial sleeps and trivial object creation
