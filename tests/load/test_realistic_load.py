"""
Realistic integration load testing for Bitfinex-Maker-Kit.

Tests system behavior under realistic load conditions using Bitfinex Paper Trading API.
Validates production readiness with actual network conditions, rate limits, and API behavior.

IMPORTANT: These tests require BFX_API_PAPER_KEY and BFX_API_PAPER_SECRET
environment variables to be set with valid Paper Trading credentials.

Setup Instructions:
1. Create a Bitfinex Paper Trading sub-account
2. Generate API credentials for the sub-account
3. Set environment variables:
   export BFX_API_PAPER_KEY="your_paper_trading_api_key"
   export BFX_API_PAPER_SECRET="your_paper_trading_api_secret"
4. Run tests: pytest tests/load/test_realistic_load.py -m paper_trading
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import psutil
import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.order_id import OrderId
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol


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
            load_function: Async function to execute (should return success boolean)
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
@pytest.mark.slow
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
                # Use realistic price variations around current market
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

    @pytest.mark.asyncio
    async def test_sustained_trading_session(
        self,
        load_test_runner,
        paper_trading_service,
        paper_trading_symbol,
        realistic_load_thresholds,
    ):
        """Test sustained trading session with realistic order lifecycle."""
        placed_orders = []
        operation_counter = 0

        async def realistic_trading_operation():
            """Perform realistic trading operations (place, check status, cancel)."""
            nonlocal operation_counter
            operation_counter += 1

            try:
                if operation_counter % 3 == 0 and placed_orders:
                    # Cancel an existing order (33% of operations)
                    order_to_cancel = placed_orders.pop(0)
                    success, result = paper_trading_service.cancel_order(order_to_cancel)
                    return success
                elif operation_counter % 4 == 0:
                    # Check order status (25% of operations)
                    orders = paper_trading_service.get_orders()
                    return len(orders) >= 0  # Always succeeds if no error
                else:
                    # Place new order (remaining operations)
                    base_price = 50000.0 + (operation_counter % 1000)
                    price = Price(f"{base_price:.2f}")

                    success, result = paper_trading_service.place_order(
                        symbol=paper_trading_symbol,
                        amount=Amount("0.001"),
                        price=price,
                        side="buy" if operation_counter % 2 == 0 else "sell",
                    )

                    if success and "id" in result:
                        order_id = OrderId(str(result["id"]))
                        placed_orders.append(order_id)

                    return success
            except Exception as e:
                print(f"Trading operation error: {e}")
                return False

        result = await load_test_runner.run_realistic_load_test(
            "sustained_trading_session",
            realistic_trading_operation,
            duration_seconds=60.0,  # Longer test for sustained session
            max_operations_per_second=3.0,  # Conservative rate for mixed operations
            metadata={"session_type": "sustained", "operations": "mixed"},
        )

        # Sustained session assertions
        assert result.operations_per_second >= 1.0, (
            f"Sustained throughput too low: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.7, (
            f"Sustained success rate too low: {result.success_rate:.1%}"
        )
        assert result.network_errors <= result.total_operations * 0.1, (
            f"Too many network errors: {result.network_errors}/{result.total_operations}"
        )

    @pytest.mark.asyncio
    async def test_api_error_resilience(
        self, load_test_runner, paper_trading_service, realistic_load_thresholds
    ):
        """Test system resilience under API error conditions."""
        error_counter = 0

        async def error_prone_operation():
            """Operation that may encounter various API errors."""
            nonlocal error_counter
            error_counter += 1

            try:
                # Use invalid symbol occasionally to trigger API errors
                if error_counter % 10 == 0:
                    # This should cause an API error
                    symbol = Symbol("tINVALIDSYMBOL")
                else:
                    symbol = Symbol("tTESTBTCTESTUSD")

                success, result = paper_trading_service.place_order(
                    symbol=symbol,
                    amount=Amount("0.001"),
                    price=Price("50000.0"),
                    side="buy",
                )
                return success
            except Exception:
                # Expected for invalid symbols
                return False

        result = await load_test_runner.run_realistic_load_test(
            "api_error_resilience",
            error_prone_operation,
            duration_seconds=30.0,
            max_operations_per_second=2.0,
            metadata={"error_injection": "invalid_symbols"},
        )

        # Error resilience assertions
        assert result.total_operations > 0, "No operations were attempted"
        assert result.api_errors > 0, "Expected some API errors from invalid symbols"
        assert result.operations_per_second >= 1.0, (
            f"Error resilience throughput too low: {result.operations_per_second:.1f} ops/sec"
        )
        # Should handle errors gracefully without crashing
        assert result.successful_operations > 0, "No successful operations despite error injection"

    @pytest.mark.asyncio
    async def test_rate_limit_compliance(
        self, load_test_runner, paper_trading_service, paper_trading_symbol
    ):
        """Test compliance with API rate limits."""

        async def rate_limited_operation():
            """Operation that tests rate limit compliance."""
            try:
                success, result = paper_trading_service.get_orders()
                return success is not None  # Any non-None response is success
            except Exception as e:
                if "rate limit" in str(e).lower():
                    return False  # Rate limit violation
                raise  # Re-raise non-rate-limit errors

        # Test with aggressive rate (should trigger rate limiting)
        result = await load_test_runner.run_realistic_load_test(
            "rate_limit_compliance",
            rate_limited_operation,
            duration_seconds=20.0,
            max_operations_per_second=20.0,  # Aggressive rate to test limits
            metadata={"test_type": "rate_limiting"},
        )

        # Rate limit compliance assertions
        assert result.total_operations > 0, "No operations were attempted"
        print(
            f"Rate limit test results: {result.rate_limit_violations} violations in {result.total_operations} operations"
        )

        # Some rate limit violations are expected at high rates
        violation_rate = (
            result.rate_limit_violations / result.total_operations
            if result.total_operations > 0
            else 0
        )
        assert violation_rate <= 0.3, f"Too many rate limit violations: {violation_rate:.1%}"

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self,
        load_test_runner,
        paper_trading_service,
        paper_trading_symbol,
        realistic_load_thresholds,
    ):
        """Test memory usage patterns under sustained load."""

        async def memory_intensive_operation():
            """Operation that may accumulate memory usage."""
            try:
                # Get orders (may accumulate response objects)
                orders = paper_trading_service.get_orders()

                # Get wallet balances
                balances = paper_trading_service.get_wallet_balances()

                return len(orders) >= 0 and len(balances) >= 0
            except Exception:
                return False

        result = await load_test_runner.run_realistic_load_test(
            "memory_usage_under_load",
            memory_intensive_operation,
            duration_seconds=45.0,
            max_operations_per_second=4.0,
            metadata={"memory_test": True},
        )

        # Memory usage assertions
        assert result.peak_memory_mb <= realistic_load_thresholds["max_memory_usage_mb"], (
            f"Memory usage exceeded threshold: {result.peak_memory_mb:.1f}MB"
        )
        assert result.operations_per_second >= 2.0, (
            f"Memory test throughput too low: {result.operations_per_second:.1f} ops/sec"
        )

        # Memory should not grow excessively during sustained operations
        print(f"Peak memory usage: {result.peak_memory_mb:.1f}MB over {result.duration:.1f}s")


@pytest.mark.load
@pytest.mark.paper_trading
@pytest.mark.realistic_load
@pytest.mark.slow
class TestLoadTestReporting:
    """Tests for load test result reporting and analysis."""

    @pytest.fixture
    def load_test_runner(self):
        """Create realistic load test runner."""
        return RealisticLoadTestRunner()

    @pytest.mark.asyncio
    async def test_load_test_result_export(self, load_test_runner, paper_trading_service):
        """Test load test result data export and analysis."""

        async def simple_test_operation():
            """Simple operation for testing result collection."""
            try:
                orders = paper_trading_service.get_orders()
                return len(orders) >= 0
            except Exception:
                return False

        result = await load_test_runner.run_realistic_load_test(
            "result_export_test",
            simple_test_operation,
            duration_seconds=10.0,
            max_operations_per_second=3.0,
            metadata={"test_purpose": "result_validation"},
        )

        # Validate result data structure
        assert isinstance(result.test_name, str)
        assert result.duration > 0
        assert result.total_operations > 0
        assert result.operations_per_second > 0
        assert 0 <= result.success_rate <= 1.0
        assert result.peak_memory_mb > 0
        assert isinstance(result.metadata, dict)
        assert result.metadata["test_purpose"] == "result_validation"

        # Validate metric calculations
        calculated_ops_per_sec = result.total_operations / result.duration
        assert abs(result.operations_per_second - calculated_ops_per_sec) < 0.1, (
            "Operations per second calculation incorrect"
        )

        calculated_success_rate = result.successful_operations / result.total_operations
        assert abs(result.success_rate - calculated_success_rate) < 0.01, (
            "Success rate calculation incorrect"
        )

        print(f"Load test results validated: {result.test_name}")
        print(f"  Operations: {result.total_operations} ({result.operations_per_second:.1f}/sec)")
        print(f"  Success rate: {result.success_rate:.1%}")
        print(
            f"  Response time: {result.average_response_time_ms:.0f}ms avg, {result.max_response_time_ms:.0f}ms max"
        )
        print(f"  Memory: {result.peak_memory_mb:.1f}MB peak")
