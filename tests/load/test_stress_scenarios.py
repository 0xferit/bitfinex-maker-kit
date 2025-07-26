"""
Comprehensive stress testing scenarios for Bitfinex-Maker-Kit.

Tests system behavior under extreme load conditions, resource exhaustion,
and concurrent access patterns to validate production readiness.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any

import psutil
import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol

from ..mocks.service_mocks import create_mock_cache_service, create_mock_trading_service


@dataclass
class StressTestResult:
    """Result of a stress test scenario."""

    test_name: str
    duration: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    success_rate: float
    peak_memory_mb: float
    average_cpu_percent: float
    error_details: list[str]
    metadata: dict[str, Any]


class StressTestRunner:
    """Utility for running comprehensive stress tests."""

    def __init__(self):
        self.process = psutil.Process()
        self.results: list[StressTestResult] = []

    async def run_stress_test(
        self,
        test_name: str,
        stress_function,
        duration_seconds: float = 30.0,
        metadata: dict[str, Any] | None = None,
    ) -> StressTestResult:
        """
        Run a stress test for specified duration.

        Args:
            test_name: Name of the stress test
            stress_function: Async function that performs stress operations
            duration_seconds: How long to run the test
            metadata: Additional test metadata

        Returns:
            StressTestResult with comprehensive metrics
        """
        print(f"Starting stress test: {test_name} (duration: {duration_seconds}s)")

        # Initialize metrics tracking
        start_time = time.time()
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        cpu_samples = []

        total_operations = 0
        successful_operations = 0
        failed_operations = 0
        error_details = []

        # Start CPU monitoring
        self.process.cpu_percent()

        # Run stress test
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            try:
                # Execute stress operation
                result = await stress_function()
                total_operations += 1

                if result:
                    successful_operations += 1
                else:
                    failed_operations += 1

                # Sample system metrics
                current_memory = self.process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                cpu_samples.append(self.process.cpu_percent())

            except Exception as e:
                total_operations += 1
                failed_operations += 1
                error_details.append(str(e))

                # Limit error collection to prevent memory issues
                if len(error_details) > 100:
                    error_details = error_details[-50:]  # Keep last 50 errors

        # Calculate final metrics
        actual_duration = time.time() - start_time
        ops_per_second = total_operations / actual_duration if actual_duration > 0 else 0
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0

        result = StressTestResult(
            test_name=test_name,
            duration=actual_duration,
            total_operations=total_operations,
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            operations_per_second=ops_per_second,
            success_rate=success_rate,
            peak_memory_mb=peak_memory - initial_memory,
            average_cpu_percent=avg_cpu,
            error_details=error_details[:10],  # Keep top 10 errors
            metadata=metadata or {},
        )

        self.results.append(result)
        print(
            f"Completed stress test: {test_name} - {ops_per_second:.1f} ops/sec, {success_rate:.1%} success"
        )

        return result


@pytest.mark.load
class TestTradingStressScenarios:
    """Stress tests for trading operations under extreme load."""

    @pytest.fixture
    def stress_runner(self):
        """Create stress test runner."""
        return StressTestRunner()

    @pytest.mark.asyncio
    async def test_high_frequency_order_placement(self, stress_runner):
        """Test high-frequency order placement under stress."""
        trading_service = create_mock_trading_service("normal")
        order_counter = 0

        async def place_rapid_orders():
            """Place orders as rapidly as possible."""
            nonlocal order_counter
            order_counter += 1

            try:
                return await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.001"),  # Small HFT size
                    price=Price(f"{50000 + (order_counter % 1000)}.0"),
                    side="buy" if order_counter % 2 == 0 else "sell",
                )
            except Exception:
                return None

        result = await stress_runner.run_stress_test(
            "high_frequency_order_placement",
            place_rapid_orders,
            duration_seconds=10.0,
            metadata={"target_frequency": "maximum", "order_size": "0.001"},
        )

        # High-frequency stress test assertions
        assert result.operations_per_second >= 10, (
            f"HFT throughput too low: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.7, f"HFT success rate too low: {result.success_rate:.1%}"
        assert result.peak_memory_mb < 100, f"Memory usage too high: {result.peak_memory_mb:.1f}MB"

    @pytest.mark.asyncio
    async def test_massive_concurrent_orders(self, stress_runner):
        """Test massive concurrent order placement stress."""
        trading_service = create_mock_trading_service("normal")

        async def concurrent_order_burst():
            """Place multiple orders concurrently."""

            async def single_order(order_id):
                try:
                    return await trading_service.place_order(
                        symbol=Symbol("tBTCUSD"),
                        amount=Amount(f"{random.uniform(0.01, 0.1):.6f}"),
                        price=Price(f"{random.uniform(49000, 51000):.2f}"),
                        side=random.choice(["buy", "sell"]),
                    )
                except Exception:
                    return None

            # Launch 50 concurrent orders
            tasks = [single_order(i) for i in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = len([r for r in results if r is not None and not isinstance(r, Exception)])
            return successful > 0

        result = await stress_runner.run_stress_test(
            "massive_concurrent_orders",
            concurrent_order_burst,
            duration_seconds=15.0,
            metadata={"concurrent_orders_per_burst": 50},
        )

        # Concurrent order stress assertions
        assert result.success_rate >= 0.5, (
            f"Concurrent order success rate too low: {result.success_rate:.1%}"
        )
        assert result.operations_per_second >= 1, (
            f"Concurrent throughput too low: {result.operations_per_second:.1f} ops/sec"
        )

    @pytest.mark.asyncio
    async def test_order_cancel_storm(self, stress_runner):
        """Test rapid order cancellation under stress."""
        trading_service = create_mock_trading_service("normal")

        # Pre-place orders to cancel
        placed_orders = []
        for i in range(200):
            try:
                order = await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.01"),
                    price=Price(f"{50000 + i}.0"),
                    side="buy",
                )
                placed_orders.append(order["id"])
            except Exception:
                continue

        cancel_index = 0

        async def rapid_cancellation():
            """Cancel orders rapidly."""
            nonlocal cancel_index

            if cancel_index < len(placed_orders):
                order_id = placed_orders[cancel_index]
                cancel_index += 1

                try:
                    await trading_service.cancel_order(str(order_id))
                    return True
                except Exception:
                    return False
            else:
                # Create and immediately cancel new order
                try:
                    order = await trading_service.place_order(
                        symbol=Symbol("tBTCUSD"),
                        amount=Amount("0.01"),
                        price=Price(f"{60000 + cancel_index}.0"),
                        side="buy",
                    )
                    await trading_service.cancel_order(str(order["id"]))
                    return True
                except Exception:
                    return False

        result = await stress_runner.run_stress_test(
            "order_cancel_storm",
            rapid_cancellation,
            duration_seconds=10.0,
            metadata={"pre_placed_orders": len(placed_orders)},
        )

        # Cancel storm assertions
        assert result.operations_per_second >= 15, (
            f"Cancel throughput too low: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.8, f"Cancel success rate too low: {result.success_rate:.1%}"

    @pytest.mark.asyncio
    async def test_mixed_operation_chaos(self, stress_runner):
        """Test chaotic mix of all trading operations."""
        trading_service = create_mock_trading_service("normal")
        operation_counter = 0

        async def chaotic_operations():
            """Perform random trading operations."""
            nonlocal operation_counter
            operation_counter += 1

            operation = random.choice(["place", "cancel", "status", "list"])

            try:
                if operation == "place":
                    return await trading_service.place_order(
                        symbol=Symbol(random.choice(["tBTCUSD", "tETHUSD"])),
                        amount=Amount(f"{random.uniform(0.001, 0.1):.6f}"),
                        price=Price(f"{random.uniform(30000, 70000):.2f}"),
                        side=random.choice(["buy", "sell"]),
                    )
                elif operation == "cancel":
                    # Try to cancel a random order ID
                    order_id = random.randint(10000000, 99999999)
                    await trading_service.cancel_order(str(order_id))
                    return True
                elif operation == "status":
                    order_id = random.randint(10000000, 99999999)
                    await trading_service.get_order_status(str(order_id))
                    return True
                elif operation == "list":
                    await trading_service.get_active_orders()
                    return True

            except Exception:
                return False

        result = await stress_runner.run_stress_test(
            "mixed_operation_chaos",
            chaotic_operations,
            duration_seconds=20.0,
            metadata={"operation_types": ["place", "cancel", "status", "list"]},
        )

        # Chaos test assertions
        assert result.operations_per_second >= 5, (
            f"Chaos throughput too low: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.3, f"Chaos success rate too low: {result.success_rate:.1%}"


@pytest.mark.load
class TestCacheStressScenarios:
    """Stress tests for cache operations under extreme load."""

    @pytest.fixture
    def stress_runner(self):
        """Create stress test runner."""
        return StressTestRunner()

    @pytest.mark.asyncio
    async def test_cache_write_storm(self, stress_runner):
        """Test cache under heavy write load."""
        cache_service = create_mock_cache_service("normal")
        write_counter = 0

        try:

            async def rapid_cache_writes():
                """Perform rapid cache writes."""
                nonlocal write_counter
                write_counter += 1

                try:
                    await cache_service.set(
                        "stress_test",
                        f"key_{write_counter}",
                        f"value_{write_counter}_{time.time()}",
                        ttl=random.uniform(1.0, 300.0),
                    )
                    return True
                except Exception:
                    return False

            result = await stress_runner.run_stress_test(
                "cache_write_storm",
                rapid_cache_writes,
                duration_seconds=10.0,
                metadata={"operation_type": "write_heavy"},
            )

            # Cache write storm assertions
            assert result.operations_per_second >= 50, (
                f"Cache write throughput too low: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.95, (
                f"Cache write success rate too low: {result.success_rate:.1%}"
            )

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    async def test_cache_read_storm(self, stress_runner):
        """Test cache under heavy read load."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Pre-populate cache with test data
            for i in range(1000):
                await cache_service.set("stress_test", f"key_{i}", f"value_{i}")

            read_counter = 0

            async def rapid_cache_reads():
                """Perform rapid cache reads."""
                nonlocal read_counter
                read_counter += 1

                key = f"key_{read_counter % 1000}"  # Cycle through existing keys

                try:
                    result = await cache_service.get("stress_test", key)
                    return result is not None
                except Exception:
                    return False

            result = await stress_runner.run_stress_test(
                "cache_read_storm",
                rapid_cache_reads,
                duration_seconds=10.0,
                metadata={"operation_type": "read_heavy", "pre_populated_keys": 1000},
            )

            # Cache read storm assertions
            assert result.operations_per_second >= 200, (
                f"Cache read throughput too low: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.98, (
                f"Cache read success rate too low: {result.success_rate:.1%}"
            )

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    async def test_cache_mixed_load_storm(self, stress_runner):
        """Test cache under mixed read/write/delete load."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Pre-populate with some data
            for i in range(100):
                await cache_service.set("mixed_test", f"initial_key_{i}", f"initial_value_{i}")

            operation_counter = 0

            async def mixed_cache_operations():
                """Perform mixed cache operations."""
                nonlocal operation_counter
                operation_counter += 1

                operation = random.choices(
                    ["read", "write", "delete", "get_or_set"],
                    weights=[50, 30, 10, 10],  # Read-heavy workload
                )[0]

                key = f"mixed_key_{operation_counter % 500}"

                try:
                    if operation == "read":
                        await cache_service.get("mixed_test", key)
                        return True
                    elif operation == "write":
                        await cache_service.set("mixed_test", key, f"value_{operation_counter}")
                        return True
                    elif operation == "delete":
                        await cache_service.delete("mixed_test", key)
                        return True
                    elif operation == "get_or_set":

                        async def fetch_function():
                            return f"computed_value_{operation_counter}"

                        await cache_service.get_or_set("mixed_test", key, fetch_function)
                        return True

                except Exception:
                    return False

            result = await stress_runner.run_stress_test(
                "cache_mixed_load_storm",
                mixed_cache_operations,
                duration_seconds=15.0,
                metadata={
                    "operation_mix": "read:50%, write:30%, delete:10%, get_or_set:10%",
                    "pre_populated_keys": 100,
                },
            )

            # Mixed load assertions
            assert result.operations_per_second >= 100, (
                f"Mixed cache throughput too low: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.90, (
                f"Mixed cache success rate too low: {result.success_rate:.1%}"
            )

        finally:
            await cache_service.cleanup()


@pytest.mark.load
class TestSystemIntegrationStress:
    """Integration stress tests for complete system scenarios."""

    @pytest.fixture
    def stress_runner(self):
        """Create stress test runner."""
        return StressTestRunner()

    @pytest.mark.asyncio
    async def test_full_system_load(self, stress_runner):
        """Test complete system under realistic trading load."""
        trading_service = create_mock_trading_service("normal")
        cache_service = create_mock_cache_service("normal")

        try:
            operation_counter = 0

            async def realistic_trading_session():
                """Simulate realistic trading session operations."""
                nonlocal operation_counter
                operation_counter += 1

                try:
                    # 1. Cache market data lookup
                    symbol = random.choice(["tBTCUSD", "tETHUSD", "tPNKUSD"])
                    cached_price = await cache_service.get("market_data", f"{symbol}_price")

                    if cached_price is None:
                        # Simulate fetching from external API
                        current_price = random.uniform(30000, 70000)
                        await cache_service.set(
                            "market_data", f"{symbol}_price", current_price, ttl=10.0
                        )
                    else:
                        current_price = cached_price

                    # 2. Make trading decision
                    if random.random() < 0.7:  # 70% chance to place order
                        offset = random.uniform(-1000, 1000)
                        order_price = max(0.01, current_price + offset)

                        order = await trading_service.place_order(
                            symbol=Symbol(symbol),
                            amount=Amount(f"{random.uniform(0.01, 1.0):.6f}"),
                            price=Price(f"{order_price:.2f}"),
                            side=random.choice(["buy", "sell"]),
                        )

                        # 3. Cache order information
                        await cache_service.set("orders", f"order_{order['id']}", order, ttl=300.0)

                        # 4. Occasionally check order status
                        if random.random() < 0.3:
                            await trading_service.get_order_status(str(order["id"]))

                    return True

                except Exception:
                    return False

            result = await stress_runner.run_stress_test(
                "full_system_load",
                realistic_trading_session,
                duration_seconds=30.0,
                metadata={
                    "scenario": "realistic_trading_session",
                    "components": ["trading", "cache", "market_data"],
                },
            )

            # Full system load assertions
            assert result.operations_per_second >= 5, (
                f"System throughput too low: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.8, (
                f"System success rate too low: {result.success_rate:.1%}"
            )
            assert result.peak_memory_mb < 200, (
                f"System memory usage too high: {result.peak_memory_mb:.1f}MB"
            )

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    async def test_resource_exhaustion_resilience(self, stress_runner):
        """Test system resilience under resource exhaustion."""
        trading_service = create_mock_trading_service("normal")
        cache_service = create_mock_cache_service("normal")

        try:
            # Create resource-intensive operations
            large_objects = []
            operation_counter = 0

            async def resource_intensive_operations():
                """Perform resource-intensive operations."""
                nonlocal operation_counter
                operation_counter += 1

                try:
                    # Create memory pressure
                    if len(large_objects) < 100:  # Limit to prevent test crash
                        large_objects.append("x" * 10000)  # 10KB objects

                    # CPU-intensive cache operations
                    for i in range(5):
                        await cache_service.set(
                            "resource_test",
                            f"large_key_{operation_counter}_{i}",
                            "x" * 1000,  # 1KB values
                            ttl=1.0,
                        )

                    # Trading operations
                    await trading_service.place_order(
                        symbol=Symbol("tBTCUSD"),
                        amount=Amount(f"{random.uniform(0.001, 0.01):.6f}"),
                        price=Price(f"{random.uniform(45000, 55000):.2f}"),
                        side=random.choice(["buy", "sell"]),
                    )

                    return True

                except Exception:
                    return False

            result = await stress_runner.run_stress_test(
                "resource_exhaustion_resilience",
                resource_intensive_operations,
                duration_seconds=15.0,
                metadata={"resource_pressure": "memory_and_cpu"},
            )

            # Resource exhaustion resilience assertions
            assert result.operations_per_second >= 1, (
                f"Resource-constrained throughput too low: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.5, (
                f"Resource-constrained success rate too low: {result.success_rate:.1%}"
            )

            # System should survive resource pressure
            assert len(result.error_details) < result.total_operations, (
                "System completely failed under resource pressure"
            )

        finally:
            await cache_service.cleanup()
            # Clean up large objects
            large_objects.clear()


@pytest.mark.load
class TestLoadTestReporting:
    """Tests for load test reporting and analysis."""

    @pytest.mark.asyncio
    async def test_stress_test_result_export(self):
        """Test stress test result export functionality."""
        stress_runner = StressTestRunner()

        # Create a simple test operation
        async def simple_operation():
            await asyncio.sleep(0.001)  # Simulate work
            return True

        # Run test
        result = await stress_runner.run_stress_test(
            "export_test",
            simple_operation,
            duration_seconds=1.0,
            metadata={"test_type": "export_validation"},
        )

        # Verify result structure
        assert result.test_name == "export_test"
        assert result.duration > 0
        assert result.total_operations > 0
        assert result.operations_per_second > 0
        assert 0 <= result.success_rate <= 1
        assert result.peak_memory_mb >= 0
        assert result.average_cpu_percent >= 0
        assert isinstance(result.error_details, list)
        assert isinstance(result.metadata, dict)

        # Test that results are stored
        assert len(stress_runner.results) == 1
        assert stress_runner.results[0] == result

    @pytest.mark.asyncio
    async def test_multiple_stress_test_aggregation(self):
        """Test aggregation of multiple stress test results."""
        stress_runner = StressTestRunner()

        # Run multiple tests
        for i in range(3):

            async def test_operation(iteration=i):
                await asyncio.sleep(0.001 * (iteration + 1))  # Variable timing
                return iteration % 2 == 0  # Alternate success/failure

            await stress_runner.run_stress_test(
                f"aggregation_test_{i}",
                test_operation,
                duration_seconds=0.5,
                metadata={"test_number": i},
            )

        # Verify all results collected
        assert len(stress_runner.results) == 3

        # Verify results have different characteristics
        test_names = [r.test_name for r in stress_runner.results]
        assert "aggregation_test_0" in test_names
        assert "aggregation_test_1" in test_names
        assert "aggregation_test_2" in test_names

        # Verify metadata preservation
        for i, result in enumerate(stress_runner.results):
            assert result.metadata["test_number"] == i
