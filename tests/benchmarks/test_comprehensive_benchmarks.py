"""
Comprehensive benchmarking suite for Maker-Kit.

Provides detailed performance benchmarks for all system components
including API operations, cache performance, and trading throughput.
"""

import asyncio
import contextlib
import gc
import statistics
import time
from dataclasses import dataclass
from typing import Any

import psutil
import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.order_id import OrderId
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol

from ..fixtures.performance_data import PerformanceFixtures
from ..mocks.client_mocks import create_mock_client
from ..mocks.service_mocks import create_mock_cache_service, create_mock_trading_service


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""

    test_name: str
    operations_count: int
    total_time: float
    operations_per_second: float
    avg_time_per_op: float
    min_time: float
    max_time: float
    p50_time: float
    p95_time: float
    p99_time: float
    memory_used_mb: float
    cpu_percent: float
    success_rate: float
    error_count: int
    metadata: dict[str, Any]


class BenchmarkRunner:
    """Utility class for running performance benchmarks."""

    def __init__(self):
        self.process = psutil.Process()
        self.results: list[BenchmarkResult] = []

    async def run_benchmark(
        self,
        test_name: str,
        operation_func,
        iterations: int = 1000,
        warmup_iterations: int = 100,
        metadata: dict[str, Any] | None = None,
    ) -> BenchmarkResult:
        """
        Run a comprehensive benchmark test.

        Args:
            test_name: Name of the benchmark test
            operation_func: Async function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            metadata: Additional metadata for the benchmark

        Returns:
            BenchmarkResult with detailed performance metrics
        """
        # Force garbage collection before benchmark
        gc.collect()

        # Get initial memory usage
        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # Warmup phase
        for _ in range(warmup_iterations):
            with contextlib.suppress(Exception):
                await operation_func()

        # Reset CPU measurement
        self.process.cpu_percent()

        # Benchmark phase
        execution_times = []
        error_count = 0
        start_time = time.time()

        for _i in range(iterations):
            op_start = time.time()
            try:
                await operation_func()
                op_end = time.time()
                execution_times.append(op_end - op_start)
            except Exception:
                error_count += 1
                execution_times.append(0)  # Record failed operation

        end_time = time.time()
        total_time = end_time - start_time

        # Get final measurements
        final_memory = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()

        # Calculate statistics
        valid_times = [t for t in execution_times if t > 0]

        if valid_times:
            sorted_times = sorted(valid_times)
            avg_time = statistics.mean(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
            p50_time = sorted_times[len(sorted_times) // 2]
            p95_time = (
                sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) > 20 else max_time
            )
            p99_time = (
                sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 100 else max_time
            )
        else:
            avg_time = min_time = max_time = p50_time = p95_time = p99_time = 0

        successful_ops = iterations - error_count
        ops_per_second = successful_ops / total_time if total_time > 0 else 0
        success_rate = successful_ops / iterations if iterations > 0 else 0
        memory_used = final_memory - initial_memory

        result = BenchmarkResult(
            test_name=test_name,
            operations_count=iterations,
            total_time=total_time,
            operations_per_second=ops_per_second,
            avg_time_per_op=avg_time,
            min_time=min_time,
            max_time=max_time,
            p50_time=p50_time,
            p95_time=p95_time,
            p99_time=p99_time,
            memory_used_mb=memory_used,
            cpu_percent=cpu_percent,
            success_rate=success_rate,
            error_count=error_count,
            metadata=metadata or {},
        )

        self.results.append(result)
        return result

    def get_results(self) -> list[BenchmarkResult]:
        """Get all benchmark results."""
        return self.results.copy()

    def export_results(self, format: str = "json") -> str:
        """Export benchmark results in specified format."""
        if format == "json":
            import json

            return json.dumps(
                [
                    {
                        "test_name": r.test_name,
                        "operations_per_second": r.operations_per_second,
                        "avg_time_per_op_ms": r.avg_time_per_op * 1000,
                        "p95_time_ms": r.p95_time * 1000,
                        "p99_time_ms": r.p99_time * 1000,
                        "success_rate": r.success_rate,
                        "memory_used_mb": r.memory_used_mb,
                        "cpu_percent": r.cpu_percent,
                        "metadata": r.metadata,
                    }
                    for r in self.results
                ],
                indent=2,
            )
        elif format == "csv":
            lines = ["test_name,ops_per_sec,avg_time_ms,p95_time_ms,success_rate,memory_mb"]
            for r in self.results:
                lines.append(
                    f"{r.test_name},{r.operations_per_second:.2f},"
                    f"{r.avg_time_per_op * 1000:.2f},{r.p95_time * 1000:.2f},"
                    f"{r.success_rate:.3f},{r.memory_used_mb:.2f}"
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


@pytest.mark.load
class TestDomainObjectBenchmarks:
    """Benchmark tests for domain objects."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    async def test_symbol_creation_benchmark(self, benchmark_runner):
        """Benchmark symbol creation performance."""
        symbols = ["tBTCUSD", "tETHUSD", "tPNKUSD", "tLTCUSD", "tXRPUSD"]

        async def create_symbol():
            symbol_str = symbols[int(time.time() * 1000) % len(symbols)]
            return Symbol(symbol_str)

        result = await benchmark_runner.run_benchmark(
            "symbol_creation",
            create_symbol,
            iterations=10000,
            metadata={"symbols_count": len(symbols)},
        )

        # Assert performance requirements
        assert result.operations_per_second >= 5000, (
            f"Symbol creation too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.avg_time_per_op < 0.001, (
            f"Average symbol creation time too high: {result.avg_time_per_op * 1000:.2f}ms"
        )
        assert result.success_rate >= 0.99, (
            f"Symbol creation success rate too low: {result.success_rate:.3f}"
        )

    async def test_price_arithmetic_benchmark(self, benchmark_runner):
        """Benchmark price arithmetic operations."""
        base_prices = [Price(str(i * 1000)) for i in range(1, 101)]

        async def price_arithmetic():
            price1 = base_prices[int(time.time() * 1000) % len(base_prices)]
            price2 = base_prices[int(time.time() * 1001) % len(base_prices)]

            # Perform various arithmetic operations
            result1 = price1 + price2
            result2 = price1 - price2 if price1.value > price2.value else price2 - price1
            result3 = price1 * 2
            result4 = price1 / 2

            return result1, result2, result3, result4

        result = await benchmark_runner.run_benchmark(
            "price_arithmetic",
            price_arithmetic,
            iterations=5000,
            metadata={"operations_per_call": 4},
        )

        # Assert performance requirements
        assert result.operations_per_second >= 2000, (
            f"Price arithmetic too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.avg_time_per_op < 0.002, (
            f"Average price arithmetic time too high: {result.avg_time_per_op * 1000:.2f}ms"
        )

    async def test_amount_operations_benchmark(self, benchmark_runner):
        """Benchmark amount operations."""
        amounts = [Amount(str(i * 0.1)) for i in range(1, 101)]

        async def amount_operations():
            amount = amounts[int(time.time() * 1000) % len(amounts)]

            # Test various amount operations
            abs_amount = amount.abs()
            neg_amount = -amount
            is_pos = amount.is_positive()
            is_neg = amount.is_negative()

            return abs_amount, neg_amount, is_pos, is_neg

        result = await benchmark_runner.run_benchmark(
            "amount_operations", amount_operations, iterations=5000
        )

        # Assert performance requirements
        assert result.operations_per_second >= 3000, (
            f"Amount operations too slow: {result.operations_per_second:.1f} ops/sec"
        )

    async def test_order_id_operations_benchmark(self, benchmark_runner):
        """Benchmark order ID operations."""
        order_ids = [OrderId(10000000 + i) for i in range(1000)]

        async def order_id_operations():
            order_id = order_ids[int(time.time() * 1000) % len(order_ids)]

            # Test various operations
            str_repr = str(order_id)
            hash_val = hash(order_id)
            comparison = order_id == order_ids[0]

            return str_repr, hash_val, comparison

        result = await benchmark_runner.run_benchmark(
            "order_id_operations", order_id_operations, iterations=5000
        )

        # Assert performance requirements
        assert result.operations_per_second >= 4000, (
            f"Order ID operations too slow: {result.operations_per_second:.1f} ops/sec"
        )


@pytest.mark.load
class TestTradingServiceBenchmarks:
    """Benchmark tests for trading service operations."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    @pytest.fixture
    def trading_service(self):
        """Create trading service for benchmarking."""
        return create_mock_trading_service("normal")

    async def test_order_placement_benchmark(self, benchmark_runner, trading_service):
        """Benchmark order placement performance."""
        counter = 0

        async def place_order():
            nonlocal counter
            counter += 1

            return await trading_service.place_order(
                symbol=Symbol("tBTCUSD"),
                amount=Amount("0.1"),
                price=Price(f"{50000 + (counter % 1000)}.0"),
                side="buy" if counter % 2 == 0 else "sell",
            )

        result = await benchmark_runner.run_benchmark(
            "order_placement",
            place_order,
            iterations=1000,
            metadata={"order_type": "EXCHANGE LIMIT"},
        )

        # Assert performance requirements
        assert result.operations_per_second >= 100, (
            f"Order placement too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.avg_time_per_op < 0.1, (
            f"Average order placement time too high: {result.avg_time_per_op * 1000:.2f}ms"
        )
        assert result.success_rate >= 0.95, (
            f"Order placement success rate too low: {result.success_rate:.3f}"
        )

    async def test_order_cancellation_benchmark(self, benchmark_runner, trading_service):
        """Benchmark order cancellation performance."""
        # Pre-place orders to cancel
        placed_orders = []
        for i in range(500):
            try:
                order = await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.1"),
                    price=Price(f"{50000 + i}.0"),
                    side="buy",
                )
                placed_orders.append(order["id"])
            except Exception:
                continue

        order_index = 0

        async def cancel_order():
            nonlocal order_index
            if order_index < len(placed_orders):
                order_id = placed_orders[order_index]
                order_index += 1
                return await trading_service.cancel_order(str(order_id))
            else:
                # Create and immediately cancel new order
                order = await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.1"),
                    price=Price(f"{60000 + order_index}.0"),
                    side="buy",
                )
                return await trading_service.cancel_order(str(order["id"]))

        result = await benchmark_runner.run_benchmark(
            "order_cancellation",
            cancel_order,
            iterations=min(500, len(placed_orders)),
            metadata={"pre_placed_orders": len(placed_orders)},
        )

        # Assert performance requirements
        assert result.operations_per_second >= 80, (
            f"Order cancellation too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.90, (
            f"Order cancellation success rate too low: {result.success_rate:.3f}"
        )

    async def test_batch_order_benchmark(self, benchmark_runner, trading_service):
        """Benchmark batch order operations."""
        batch_sizes = [5, 10, 20, 50]

        for batch_size in batch_sizes:

            async def place_batch_orders():
                orders = []
                for i in range(batch_size):
                    orders.append(
                        {
                            "symbol": "tBTCUSD",
                            "amount": "0.1",
                            "price": f"{50000 + i}.0",
                            "side": "buy" if i % 2 == 0 else "sell",
                            "type": "EXCHANGE LIMIT",
                        }
                    )

                return await trading_service.place_batch_orders(orders)

            result = await benchmark_runner.run_benchmark(
                f"batch_orders_{batch_size}",
                place_batch_orders,
                iterations=100,
                metadata={"batch_size": batch_size},
            )

            # Assert batch performance scales appropriately
            expected_min_ops_per_sec = max(10, 100 - batch_size)  # Allow some overhead
            assert result.operations_per_second >= expected_min_ops_per_sec, (
                f"Batch order placement (size {batch_size}) too slow: {result.operations_per_second:.1f} ops/sec"
            )

    async def test_concurrent_trading_benchmark(self, benchmark_runner, trading_service):
        """Benchmark concurrent trading operations."""
        concurrent_levels = [5, 10, 20]

        for concurrency in concurrent_levels:

            async def concurrent_operations():
                async def single_operation(op_id):
                    return await trading_service.place_order(
                        symbol=Symbol("tBTCUSD"),
                        amount=Amount("0.01"),
                        price=Price(f"{50000 + op_id}.0"),
                        side="buy" if op_id % 2 == 0 else "sell",
                    )

                tasks = [single_operation(i) for i in range(concurrency)]
                return await asyncio.gather(*tasks, return_exceptions=True)

            result = await benchmark_runner.run_benchmark(
                f"concurrent_trading_{concurrency}",
                concurrent_operations,
                iterations=50,
                metadata={"concurrency_level": concurrency},
            )

            # Assert concurrent performance
            # Total throughput should scale with concurrency (with some overhead)
            expected_throughput = min(concurrency * 20, 500)  # Cap at reasonable limit
            assert result.operations_per_second >= expected_throughput * 0.7, (
                f"Concurrent trading (level {concurrency}) throughput too low: {result.operations_per_second:.1f} ops/sec"
            )


@pytest.mark.load
class TestCacheBenchmarks:
    """Benchmark tests for cache operations."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    @pytest.fixture
    async def cache_service(self):
        """Create cache service for benchmarking."""
        cache = create_mock_cache_service("normal")
        yield cache
        await cache.cleanup()

    async def test_cache_set_benchmark(self, benchmark_runner, cache_service):
        """Benchmark cache set operations."""
        counter = 0

        async def cache_set():
            nonlocal counter
            counter += 1
            await cache_service.set("benchmark", f"key_{counter}", f"value_{counter}")

        result = await benchmark_runner.run_benchmark("cache_set", cache_set, iterations=5000)

        # Assert cache set performance
        assert result.operations_per_second >= 1000, (
            f"Cache set too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.avg_time_per_op < 0.005, (
            f"Average cache set time too high: {result.avg_time_per_op * 1000:.2f}ms"
        )
        assert result.success_rate >= 0.99, (
            f"Cache set success rate too low: {result.success_rate:.3f}"
        )

    async def test_cache_get_benchmark(self, benchmark_runner, cache_service):
        """Benchmark cache get operations."""
        # Pre-populate cache
        for i in range(1000):
            await cache_service.set("benchmark", f"key_{i}", f"value_{i}")

        counter = 0

        async def cache_get():
            nonlocal counter
            counter += 1
            key_index = counter % 1000
            return await cache_service.get("benchmark", f"key_{key_index}")

        result = await benchmark_runner.run_benchmark("cache_get", cache_get, iterations=10000)

        # Assert cache get performance
        assert result.operations_per_second >= 5000, (
            f"Cache get too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.avg_time_per_op < 0.001, (
            f"Average cache get time too high: {result.avg_time_per_op * 1000:.2f}ms"
        )
        assert result.success_rate >= 0.99, (
            f"Cache get success rate too low: {result.success_rate:.3f}"
        )

    async def test_cache_get_or_set_benchmark(self, benchmark_runner, cache_service):
        """Benchmark cache get_or_set operations."""
        counter = 0

        async def cache_get_or_set():
            nonlocal counter
            counter += 1

            async def fetch_value():
                return f"computed_value_{counter}"

            # Mix of existing and new keys
            key = f"key_{counter % 500}"  # 50% hit rate
            return await cache_service.get_or_set("benchmark", key, fetch_value)

        result = await benchmark_runner.run_benchmark(
            "cache_get_or_set", cache_get_or_set, iterations=2000
        )

        # Assert cache get_or_set performance
        assert result.operations_per_second >= 500, (
            f"Cache get_or_set too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.95, (
            f"Cache get_or_set success rate too low: {result.success_rate:.3f}"
        )

    async def test_cache_mixed_operations_benchmark(self, benchmark_runner, cache_service):
        """Benchmark mixed cache operations."""
        counter = 0

        async def mixed_cache_operations():
            nonlocal counter
            counter += 1

            operation = counter % 4
            key = f"mixed_key_{counter % 100}"

            if operation == 0:  # 25% set
                await cache_service.set("mixed", key, f"value_{counter}")
            elif operation == 1:  # 25% get
                await cache_service.get("mixed", key)
            elif operation == 2:  # 25% delete
                await cache_service.delete("mixed", key)
            else:  # 25% get_or_set

                async def fetch():
                    return f"fetched_{counter}"

                await cache_service.get_or_set("mixed", key, fetch)

        result = await benchmark_runner.run_benchmark(
            "cache_mixed_operations",
            mixed_cache_operations,
            iterations=4000,
            metadata={"operation_mix": "25% each of set/get/delete/get_or_set"},
        )

        # Assert mixed operations performance
        assert result.operations_per_second >= 800, (
            f"Mixed cache operations too slow: {result.operations_per_second:.1f} ops/sec"
        )
        assert result.success_rate >= 0.90, (
            f"Mixed cache operations success rate too low: {result.success_rate:.3f}"
        )


@pytest.mark.load
class TestMemoryBenchmarks:
    """Benchmark tests for memory efficiency."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    async def test_domain_object_memory_benchmark(self, benchmark_runner):
        """Benchmark memory usage of domain objects."""
        objects_created = []

        async def create_domain_objects():
            # Create various domain objects
            symbol = Symbol("tBTCUSD")
            price = Price("50000.0")
            amount = Amount("1.0")
            order_id = OrderId(12345678)

            # Store to prevent garbage collection during test
            objects_created.extend([symbol, price, amount, order_id])

            return len(objects_created)

        result = await benchmark_runner.run_benchmark(
            "domain_object_creation",
            create_domain_objects,
            iterations=1000,
            metadata={"objects_per_iteration": 4},
        )

        # Assert memory efficiency
        total_objects = result.operations_count * 4
        memory_per_object = result.memory_used_mb * 1024 * 1024 / total_objects  # bytes per object

        # Each domain object should use reasonable memory
        assert memory_per_object < 1000, (
            f"Domain objects use too much memory: {memory_per_object:.1f} bytes per object"
        )
        assert result.operations_per_second >= 1000, (
            f"Domain object creation too slow: {result.operations_per_second:.1f} ops/sec"
        )

    async def test_cache_memory_efficiency_benchmark(self, benchmark_runner):
        """Benchmark cache memory efficiency."""
        cache_service = create_mock_cache_service("normal")

        try:

            async def populate_cache():
                # Add items to cache with fixed size values
                key = f"memory_test_{int(time.time() * 1000000) % 10000}"
                value = "x" * 100  # 100 bytes per value
                await cache_service.set("memory_test", key, value)

            result = await benchmark_runner.run_benchmark(
                "cache_memory_efficiency",
                populate_cache,
                iterations=1000,
                metadata={"bytes_per_value": 100},
            )

            # Calculate memory efficiency
            total_data_bytes = result.operations_count * 100  # 100 bytes per item
            overhead_ratio = (result.memory_used_mb * 1024 * 1024) / total_data_bytes

            # Memory overhead should be reasonable (allow up to 5x overhead for metadata)
            assert overhead_ratio < 5.0, f"Cache memory overhead too high: {overhead_ratio:.2f}x"

        finally:
            await cache_service.cleanup()


@pytest.mark.load
class TestRegressionBenchmarks:
    """Benchmark tests for performance regression detection."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    async def test_performance_regression_detection(self, benchmark_runner):
        """Test for performance regression using baseline metrics."""
        fixtures = PerformanceFixtures()
        baseline_metrics = fixtures.create_baseline_metrics()

        # Test current API performance
        client = create_mock_client("normal")

        async def api_operation():
            return client.get_ticker("tBTCUSD")

        current_result = await benchmark_runner.run_benchmark(
            "api_regression_test", api_operation, iterations=500
        )

        # Compare with baseline
        baseline_response_time = baseline_metrics.api_response_time_avg
        current_response_time = current_result.avg_time_per_op

        # Allow up to 50% performance degradation before flagging regression
        max_acceptable_time = baseline_response_time * 1.5

        assert current_response_time <= max_acceptable_time, (
            f"Performance regression detected: current {current_response_time * 1000:.2f}ms "
            f"vs baseline {baseline_response_time * 1000:.2f}ms "
            f"(max acceptable: {max_acceptable_time * 1000:.2f}ms)"
        )

        # Check throughput regression
        baseline_throughput = 1 / baseline_response_time
        current_throughput = current_result.operations_per_second
        min_acceptable_throughput = baseline_throughput * 0.7  # Allow 30% degradation

        assert current_throughput >= min_acceptable_throughput, (
            f"Throughput regression detected: current {current_throughput:.1f} ops/sec "
            f"vs baseline {baseline_throughput:.1f} ops/sec"
        )

    async def test_cache_performance_regression(self, benchmark_runner):
        """Test for cache performance regression."""
        cache_service = create_mock_cache_service("normal")
        fixtures = PerformanceFixtures()
        baseline_metrics = fixtures.create_baseline_metrics()

        try:
            # Pre-populate cache for realistic test
            for i in range(100):
                await cache_service.set("regression", f"key_{i}", f"value_{i}")

            counter = 0

            async def cache_operation():
                nonlocal counter
                counter += 1
                # 80% read, 20% write operations
                if counter % 5 == 0:
                    await cache_service.set(
                        "regression", f"key_{counter % 200}", f"new_value_{counter}"
                    )
                else:
                    await cache_service.get("regression", f"key_{counter % 100}")

            await benchmark_runner.run_benchmark(
                "cache_regression_test", cache_operation, iterations=1000
            )

            # Check cache hit ratio regression
            stats = cache_service.get_stats()
            current_hit_ratio = stats["hit_ratio"]
            baseline_hit_ratio = baseline_metrics.cache_hit_ratio

            # Allow 20% degradation in hit ratio
            min_acceptable_hit_ratio = baseline_hit_ratio * 0.8

            assert current_hit_ratio >= min_acceptable_hit_ratio, (
                f"Cache hit ratio regression detected: current {current_hit_ratio:.3f} "
                f"vs baseline {baseline_hit_ratio:.3f}"
            )

        finally:
            await cache_service.cleanup()


@pytest.mark.load
class TestComprehensiveBenchmarkSuite:
    """Comprehensive benchmark suite for full system testing."""

    @pytest.fixture
    def benchmark_runner(self):
        """Create benchmark runner."""
        return BenchmarkRunner()

    async def test_full_system_benchmark(self, benchmark_runner):
        """Run comprehensive system benchmark."""
        trading_service = create_mock_trading_service("normal")
        cache_service = create_mock_cache_service("normal")

        try:

            async def full_system_operation():
                """Simulate realistic system operation."""
                # 1. Cache market data lookup
                price_data = await cache_service.get("market", "tBTCUSD_price")
                if price_data is None:
                    price_data = 50000.0  # Simulate API fetch
                    await cache_service.set("market", "tBTCUSD_price", price_data, ttl=10.0)

                # 2. Place order based on market data
                order = await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.1"),
                    price=Price(str(price_data + 100)),
                    side="buy",
                )

                # 3. Check order status
                await trading_service.get_order_status(str(order["id"]))

                # 4. Cache order information
                await cache_service.set("orders", f"order_{order['id']}", order, ttl=300.0)

                return order["id"]

            result = await benchmark_runner.run_benchmark(
                "full_system_operation",
                full_system_operation,
                iterations=200,
                metadata={
                    "operations_per_iteration": 4,
                    "components": ["cache", "trading", "market_data"],
                },
            )

            # Assert comprehensive system performance
            assert result.operations_per_second >= 20, (
                f"Full system operations too slow: {result.operations_per_second:.1f} ops/sec"
            )
            assert result.success_rate >= 0.90, (
                f"Full system success rate too low: {result.success_rate:.3f}"
            )
            assert result.avg_time_per_op < 0.5, (
                f"Average system operation time too high: {result.avg_time_per_op * 1000:.2f}ms"
            )

            # Check memory efficiency for complex operations
            assert result.memory_used_mb < 50, (
                f"Full system operations use too much memory: {result.memory_used_mb:.1f}MB"
            )

        finally:
            await cache_service.cleanup()

    async def test_stress_benchmark_suite(self, benchmark_runner):
        """Run stress test benchmark suite."""
        # Test different load levels
        load_levels = [
            {"name": "light_load", "iterations": 100, "concurrency": 5},
            {"name": "medium_load", "iterations": 500, "concurrency": 10},
            {"name": "heavy_load", "iterations": 1000, "concurrency": 20},
        ]

        trading_service = create_mock_trading_service("normal")

        for load_config in load_levels:

            async def stress_operation():
                """Stress test operation."""

                # Concurrent order placements
                async def place_order(order_id):
                    return await trading_service.place_order(
                        symbol=Symbol("tBTCUSD"),
                        amount=Amount("0.01"),
                        price=Price(f"{50000 + order_id}.0"),
                        side="buy" if order_id % 2 == 0 else "sell",
                    )

                tasks = [place_order(i) for i in range(load_config["concurrency"])]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Return successful operations count
                return len([r for r in results if not isinstance(r, Exception)])

            result = await benchmark_runner.run_benchmark(
                f"stress_{load_config['name']}",
                stress_operation,
                iterations=load_config["iterations"] // load_config["concurrency"],
                metadata=load_config,
            )

            # Stress test should maintain reasonable performance
            min_expected_ops = (
                load_config["concurrency"] * 0.7
            )  # Allow 30% degradation under stress
            assert result.operations_per_second >= min_expected_ops, (
                f"Stress test {load_config['name']} performance too low: {result.operations_per_second:.1f} ops/sec"
            )

    async def test_benchmark_export_functionality(self, benchmark_runner):
        """Test benchmark result export functionality."""

        # Run a simple benchmark to generate results
        async def simple_operation():
            return len("test")

        await benchmark_runner.run_benchmark("export_test", simple_operation, iterations=10)

        # Test JSON export
        json_results = benchmark_runner.export_results("json")
        assert "export_test" in json_results
        assert "operations_per_second" in json_results

        # Test CSV export
        csv_results = benchmark_runner.export_results("csv")
        assert "test_name,ops_per_sec" in csv_results
        assert "export_test" in csv_results

        # Verify export contains valid data
        import json

        parsed_json = json.loads(json_results)
        assert len(parsed_json) >= 1
        assert parsed_json[0]["test_name"] == "export_test"
        assert parsed_json[0]["operations_per_second"] > 0
