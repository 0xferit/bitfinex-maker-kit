"""
DEPRECATED: This file contains old mock-based load tests that provide unrealistic performance metrics.

⚠️  IMPORTANT: These tests are deprecated and will be removed in a future version.

🔄 MIGRATION: Use tests/load/test_realistic_load.py instead for:
   - Realistic API testing against Bitfinex Paper Trading
   - Actual network conditions and rate limits
   - Meaningful performance metrics
   - Production readiness validation

📖 SETUP: See PAPER_TRADING_SETUP.md for configuration instructions

The tests in this file achieve unrealistic throughput (12,000+ ops/sec) because they use
mock services with zero network delay. This provides false confidence about production performance.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import psutil
import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price


@dataclass
class RealisticLoadTestResult:
    """Result of a realistic load test scenario against real API."""

    test_name: str
    duration: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    success_rate: float
    peak_memory_mb: float
    average_cpu_percent: float
    average_response_time_ms: float
    max_response_time_ms: float
    rate_limit_violations: int
    network_errors: int
    api_errors: int
    error_details: list[str]
    metadata: dict[str, Any]


class RealisticLoadTestRunner:
    """Utility for running realistic load tests against real APIs."""

    def __init__(self):
        self.process = psutil.Process()
        self.results: list[RealisticLoadTestResult] = []

    async def run_realistic_load_test(
        self,
        test_name: str,
        load_function,
        duration_seconds: float = 30.0,  # Longer duration for realistic testing
        max_operations_per_second: float = 10.0,  # Realistic rate limit
        metadata: dict[str, Any] | None = None,
    ) -> RealisticLoadTestResult:
        """
        Run a realistic load test against real API for specified duration.

        Args:
            test_name: Name of the test
            load_function: Async function to execute (should return response time in ms)
            duration_seconds: How long to run the test
            max_operations_per_second: Rate limit to enforce
            metadata: Additional test metadata

        Returns:
            RealisticLoadTestResult with comprehensive performance metrics
        """
        print(
            f"Starting realistic load test: {test_name} (duration: {duration_seconds}s, max {max_operations_per_second} ops/sec)"
        )

        start_time = time.time()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        cpu_samples = []
        response_times = []

        total_operations = 0
        successful_operations = 0
        failed_operations = 0
        rate_limit_violations = 0
        network_errors = 0
        api_errors = 0
        error_details = []

        # Start CPU monitoring
        self.process.cpu_percent()

        # Calculate minimum interval between operations for rate limiting
        min_interval = 1.0 / max_operations_per_second
        last_operation_time = start_time

        # Run realistic load test
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            try:
                # Enforce rate limiting
                current_time = time.time()
                time_since_last = current_time - last_operation_time
                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)

                last_operation_time = time.time()

                # Execute operation and measure response time
                operation_start = time.time()
                result = await load_function()
                operation_end = time.time()

                response_time_ms = (operation_end - operation_start) * 1000
                response_times.append(response_time_ms)
                total_operations += 1

                if result:
                    successful_operations += 1
                else:
                    failed_operations += 1

                # Sample system metrics
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

                cpu_usage = self.process.cpu_percent()
                if cpu_usage > 0:  # Only record valid samples
                    cpu_samples.append(cpu_usage)

            except ConnectionError as e:
                total_operations += 1
                failed_operations += 1
                network_errors += 1
                error_details.append(f"Network error: {e!s}")
            except Exception as e:
                total_operations += 1
                failed_operations += 1
                error_str = str(e).lower()
                if "rate limit" in error_str or "too many requests" in error_str:
                    rate_limit_violations += 1
                    error_details.append(f"Rate limit: {e!s}")
                else:
                    api_errors += 1
                    error_details.append(f"API error: {e!s}")

                # Limit error collection to prevent memory issues
                if len(error_details) > 100:
                    error_details = error_details[-50:]  # Keep last 50 errors

        # Calculate metrics
        actual_duration = time.time() - start_time
        operations_per_second = total_operations / actual_duration if actual_duration > 0 else 0
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        average_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        average_response_time = sum(response_times) / len(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        result = RealisticLoadTestResult(
            test_name=test_name,
            duration=actual_duration,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            operations_per_second=operations_per_second,
            success_rate=success_rate,
            peak_memory_mb=peak_memory,
            average_cpu_percent=average_cpu,
            average_response_time_ms=average_response_time,
            max_response_time_ms=max_response_time,
            rate_limit_violations=rate_limit_violations,
            network_errors=network_errors,
            api_errors=api_errors,
            error_details=error_details[:10],  # Keep top 10 errors
            metadata=metadata or {},
        )

        print(
            f"Completed realistic load test: {test_name} - "
            f"{operations_per_second:.1f} ops/sec, "
            f"{success_rate:.1%} success, "
            f"{average_response_time:.0f}ms avg response"
        )

        self.results.append(result)
        return result


@pytest.mark.load
@pytest.mark.paper_trading
@pytest.mark.realistic_load
class TestRealisticTradingLoadScenarios:
    """Realistic load tests for trading operations using Bitfinex Paper Trading API."""

    @pytest.fixture
    def load_test_runner(self):
        """Create realistic load test runner."""
        return RealisticLoadTestRunner()

    @pytest.mark.asyncio
    async def test_realistic_order_placement_load(
        self,
        load_test_runner,
        paper_trading_service,
        paper_trading_symbol,
        realistic_load_thresholds,
    ):
        """Test realistic order placement load against Paper Trading API."""
        order_counter = 0

        async def place_paper_trading_order():
            """Place orders against real Paper Trading API."""
            nonlocal order_counter
            order_counter += 1

            try:
                # Use realistic price variations
                base_price = 50000.0
                price_variation = (order_counter % 100) * 10  # ±$1000 variation
                price = Price(f"{base_price + price_variation:.2f}")

                success, result = paper_trading_service.place_order(
                    symbol=paper_trading_symbol,
                    amount=Amount("0.001"),  # Small test size
                    price=price,
                    side="buy" if order_counter % 2 == 0 else "sell",
                )
                return success
            except Exception as e:
                print(f"Order placement error: {e}")
                return False

        result = await load_test_runner.run_realistic_load_test(
            "realistic_order_placement_load",
            place_paper_trading_order,
            duration_seconds=30.0,
            max_operations_per_second=5.0,  # Realistic API rate limit
            metadata={"api": "paper_trading", "order_size": "0.001"},
        )

        # Realistic load test assertions
        assert (
            result.operations_per_second >= realistic_load_thresholds["min_operations_per_second"]
        ), f"Throughput too low: {result.operations_per_second:.1f} ops/sec"
        assert (
            result.operations_per_second <= realistic_load_thresholds["max_operations_per_second"]
        ), f"Throughput unrealistic: {result.operations_per_second:.1f} ops/sec"
        assert (
            result.average_response_time_ms <= realistic_load_thresholds["max_api_response_time_ms"]
        ), f"API response too slow: {result.average_response_time_ms:.0f}ms"
        assert result.peak_memory_mb <= realistic_load_thresholds["max_memory_usage_mb"], (
            f"Memory usage too high: {result.peak_memory_mb:.1f}MB"
        )
        assert result.rate_limit_violations == 0, (
            f"Rate limit violations detected: {result.rate_limit_violations}"
        )

    # DEPRECATED: All tests in this file are deprecated
    # Use tests/load/test_realistic_load.py instead

    def test_deprecated_notice(self):
        """Show deprecation notice for old mock-based tests."""
        import warnings

        warnings.warn(
            "This test file is deprecated. Use tests/load/test_realistic_load.py for realistic load testing.",
            DeprecationWarning,
            stacklevel=2,
        )
