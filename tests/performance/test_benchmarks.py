"""
Performance benchmark tests for Maker-Kit.

Comprehensive benchmarks for API operations, cache performance,
trading operations, and system resource usage.
"""

import asyncio
import time
from statistics import mean, median

import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol

from ..fixtures.performance_data import PerformanceFixtures
from ..mocks.client_mocks import create_mock_client
from ..mocks.service_mocks import create_mock_cache_service, create_mock_trading_service


@pytest.mark.performance
class TestAPIPerformanceBenchmarks:
    """Benchmark tests for API operations."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client for benchmarking."""
        return create_mock_client("normal")

    @pytest.fixture
    def slow_mock_client(self):
        """Create slow mock client for benchmarking."""
        return create_mock_client("slow")

    def test_api_call_throughput(self, mock_client, performance_thresholds):
        """Benchmark API call throughput."""
        iterations = 100
        start_time = time.time()

        # Perform API calls
        for _ in range(iterations):
            mock_client.get_ticker("tBTCUSD")

        end_time = time.time()
        total_time = end_time - start_time
        calls_per_second = iterations / total_time

        # Assert performance threshold
        min_calls_per_second = 50  # Minimum acceptable throughput
        assert calls_per_second >= min_calls_per_second, (
            f"API throughput {calls_per_second:.2f} calls/sec below threshold "
            f"{min_calls_per_second} calls/sec"
        )

    def test_api_response_time_distribution(self, mock_client):
        """Benchmark API response time distribution."""
        iterations = 50
        response_times = []

        for _ in range(iterations):
            start = time.time()
            mock_client.get_ticker("tBTCUSD")
            end = time.time()
            response_times.append((end - start) * 1000)  # Convert to ms

        # Calculate statistics
        avg_time = mean(response_times)
        median_time = median(response_times)
        p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
        p99_time = sorted(response_times)[int(len(response_times) * 0.99)]

        # Assert performance thresholds
        assert avg_time < 10.0, f"Average response time {avg_time:.2f}ms too high"
        assert median_time < 8.0, f"Median response time {median_time:.2f}ms too high"
        assert p95_time < 20.0, f"P95 response time {p95_time:.2f}ms too high"
        assert p99_time < 50.0, f"P99 response time {p99_time:.2f}ms too high"

    def test_concurrent_api_calls(self, mock_client):
        """Benchmark concurrent API call performance."""
        concurrent_calls = 10
        iterations_per_call = 10

        async def api_call_batch():
            """Perform batch of API calls."""
            start_time = time.time()

            for _ in range(iterations_per_call):
                mock_client.get_ticker("tBTCUSD")

            return time.time() - start_time

        # Run concurrent batches
        start_time = time.time()

        # Simulate concurrent calls (sync version)
        batch_times = []
        for _ in range(concurrent_calls):
            batch_time = 0
            for _ in range(iterations_per_call):
                call_start = time.time()
                mock_client.get_ticker("tBTCUSD")
                batch_time += time.time() - call_start
            batch_times.append(batch_time)

        total_time = time.time() - start_time
        total_calls = concurrent_calls * iterations_per_call
        overall_throughput = total_calls / total_time

        # Assert concurrent performance
        assert overall_throughput >= 20, (
            f"Concurrent throughput {overall_throughput:.2f} calls/sec too low"
        )


@pytest.mark.performance
class TestCachePerformanceBenchmarks:
    """Benchmark tests for cache operations."""

    @pytest.fixture
    async def cache_service(self):
        """Create cache service for benchmarking."""
        cache = create_mock_cache_service("normal")
        yield cache
        await cache.cleanup()

    async def test_cache_set_performance(self, cache_service):
        """Benchmark cache set operations."""
        iterations = 1000
        start_time = time.time()

        # Perform cache sets
        for i in range(iterations):
            await cache_service.set("benchmark", f"key_{i}", f"value_{i}")

        end_time = time.time()
        total_time = end_time - start_time
        sets_per_second = iterations / total_time

        # Assert performance threshold
        min_sets_per_second = 500  # Minimum acceptable set throughput
        assert sets_per_second >= min_sets_per_second, (
            f"Cache set throughput {sets_per_second:.2f} ops/sec below threshold "
            f"{min_sets_per_second} ops/sec"
        )

    async def test_cache_get_performance(self, cache_service):
        """Benchmark cache get operations."""
        # Pre-populate cache
        for i in range(100):
            await cache_service.set("benchmark", f"key_{i}", f"value_{i}")

        iterations = 1000
        start_time = time.time()

        # Perform cache gets
        for i in range(iterations):
            key_index = i % 100  # Cycle through existing keys
            await cache_service.get("benchmark", f"key_{key_index}")

        end_time = time.time()
        total_time = end_time - start_time
        gets_per_second = iterations / total_time

        # Assert performance threshold
        min_gets_per_second = 1000  # Get operations should be faster
        assert gets_per_second >= min_gets_per_second, (
            f"Cache get throughput {gets_per_second:.2f} ops/sec below threshold "
            f"{min_gets_per_second} ops/sec"
        )

    async def test_cache_hit_ratio_performance(self, cache_service):
        """Benchmark cache hit ratio under load."""
        # Pre-populate cache with some data
        for i in range(50):
            await cache_service.set("benchmark", f"key_{i}", f"value_{i}")

        hits = 0
        misses = 0
        iterations = 1000

        # Perform mixed get operations (80% existing keys, 20% new keys)
        for i in range(iterations):
            key = f"key_new_{i}" if i % 5 == 0 else f"key_{i % 50}"

            result = await cache_service.get("benchmark", key)
            if result is not None:
                hits += 1
            else:
                misses += 1

        hit_ratio = hits / (hits + misses)

        # Assert hit ratio performance
        min_hit_ratio = 0.75  # Should achieve at least 75% hit ratio
        assert hit_ratio >= min_hit_ratio, (
            f"Cache hit ratio {hit_ratio:.2f} below threshold {min_hit_ratio}"
        )

    async def test_concurrent_cache_operations(self, cache_service):
        """Benchmark concurrent cache operations."""
        concurrent_tasks = 20
        operations_per_task = 50

        async def cache_operation_batch():
            """Perform batch of cache operations."""
            for i in range(operations_per_task):
                # Mix of set and get operations
                if i % 2 == 0:
                    await cache_service.set("concurrent", f"key_{i}", f"value_{i}")
                else:
                    await cache_service.get("concurrent", f"key_{i - 1}")

        # Run concurrent tasks
        start_time = time.time()

        tasks = [cache_operation_batch() for _ in range(concurrent_tasks)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time
        total_operations = concurrent_tasks * operations_per_task
        ops_per_second = total_operations / total_time

        # Assert concurrent performance
        min_ops_per_second = 200
        assert ops_per_second >= min_ops_per_second, (
            f"Concurrent cache ops {ops_per_second:.2f} ops/sec below threshold "
            f"{min_ops_per_second} ops/sec"
        )


@pytest.mark.performance
class TestTradingOperationBenchmarks:
    """Benchmark tests for trading operations."""

    @pytest.fixture
    def trading_service(self):
        """Create trading service for benchmarking."""
        return create_mock_trading_service("normal")

    async def test_order_placement_performance(self, trading_service):
        """Benchmark order placement performance."""
        iterations = 100
        start_time = time.time()

        # Place orders
        for i in range(iterations):
            await trading_service.place_order(
                symbol=Symbol("tBTCUSD"),
                amount=Amount("0.1"),
                price=Price(f"{50000 + i}.0"),
                side="buy",
            )

        end_time = time.time()
        total_time = end_time - start_time
        orders_per_second = iterations / total_time

        # Assert performance threshold
        min_orders_per_second = 10  # Minimum acceptable order throughput
        assert orders_per_second >= min_orders_per_second, (
            f"Order placement throughput {orders_per_second:.2f} orders/sec "
            f"below threshold {min_orders_per_second} orders/sec"
        )

    async def test_order_cancellation_performance(self, trading_service):
        """Benchmark order cancellation performance."""
        # Pre-create orders
        order_ids = []
        for i in range(50):
            result = await trading_service.place_order(
                symbol=Symbol("tBTCUSD"),
                amount=Amount("0.1"),
                price=Price(f"{50000 + i}.0"),
                side="buy",
            )
            order_ids.append(result["id"])

        # Benchmark cancellations
        start_time = time.time()

        for order_id in order_ids:
            await trading_service.cancel_order(str(order_id))

        end_time = time.time()
        total_time = end_time - start_time
        cancellations_per_second = len(order_ids) / total_time

        # Assert performance threshold
        min_cancellations_per_second = 15
        assert cancellations_per_second >= min_cancellations_per_second, (
            f"Order cancellation throughput {cancellations_per_second:.2f} ops/sec "
            f"below threshold {min_cancellations_per_second} ops/sec"
        )

    async def test_batch_operations_performance(self, trading_service):
        """Benchmark batch operations performance."""
        # Prepare batch orders
        batch_orders = []
        for i in range(20):
            batch_orders.append(
                {
                    "symbol": "tBTCUSD",
                    "amount": "0.1",
                    "price": f"{50000 + i * 100}.0",
                    "side": "buy" if i % 2 == 0 else "sell",
                    "type": "EXCHANGE LIMIT",
                }
            )

        # Benchmark batch placement
        start_time = time.time()
        results = await trading_service.place_batch_orders(batch_orders)
        end_time = time.time()

        batch_time = end_time - start_time
        orders_per_second = len(batch_orders) / batch_time

        # Assert batch performance
        min_batch_throughput = 25  # Batch should be faster than individual
        assert orders_per_second >= min_batch_throughput, (
            f"Batch order throughput {orders_per_second:.2f} orders/sec "
            f"below threshold {min_batch_throughput} orders/sec"
        )

        # Verify all orders were placed successfully
        assert len(results) == len(batch_orders)
        successful_orders = [r for r in results if "error" not in r]
        success_rate = len(successful_orders) / len(results)

        assert success_rate >= 0.95, f"Batch success rate {success_rate:.2f} too low"

    async def test_concurrent_trading_operations(self, trading_service):
        """Benchmark concurrent trading operations."""
        concurrent_operations = 10

        async def trading_operation_sequence():
            """Perform sequence of trading operations."""
            # Place order
            result = await trading_service.place_order(
                symbol=Symbol("tBTCUSD"), amount=Amount("0.1"), price=Price("50000.0"), side="buy"
            )
            order_id = result["id"]

            # Get order status
            await trading_service.get_order_status(str(order_id))

            # Cancel order
            await trading_service.cancel_order(str(order_id))

        # Run concurrent operations
        start_time = time.time()

        tasks = [trading_operation_sequence() for _ in range(concurrent_operations)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time
        sequences_per_second = concurrent_operations / total_time

        # Assert concurrent performance
        min_sequences_per_second = 2
        assert sequences_per_second >= min_sequences_per_second, (
            f"Concurrent trading sequences {sequences_per_second:.2f} seq/sec "
            f"below threshold {min_sequences_per_second} seq/sec"
        )


@pytest.mark.performance
class TestMemoryPerformanceBenchmarks:
    """Benchmark tests for memory usage and efficiency."""

    def test_domain_object_memory_efficiency(self):
        """Benchmark memory usage of domain objects."""
        import sys

        # Create many domain objects
        symbols = [Symbol("tBTCUSD") for _ in range(1000)]
        prices = [Price("50000.0") for _ in range(1000)]
        amounts = [Amount("1.0") for _ in range(1000)]

        # Check memory usage (approximate)
        symbol_size = sys.getsizeof(symbols[0])
        price_size = sys.getsizeof(prices[0])
        amount_size = sys.getsizeof(amounts[0])

        # Assert reasonable memory usage
        max_object_size = 200  # bytes
        assert symbol_size < max_object_size, f"Symbol object too large: {symbol_size} bytes"
        assert price_size < max_object_size, f"Price object too large: {price_size} bytes"
        assert amount_size < max_object_size, f"Amount object too large: {amount_size} bytes"

    async def test_cache_memory_efficiency(self, cache_service):
        """Benchmark cache memory efficiency."""
        # Fill cache with data
        cache_size = 1000
        value_size = 100  # bytes

        for i in range(cache_size):
            value = "x" * value_size  # Create string of specific size
            await cache_service.set("memory_test", f"key_{i}", value)

        # Check cache statistics
        stats = cache_service.get_stats()

        # Verify cache is within expected size limits
        assert stats["size"] <= cache_size, "Cache size exceeded expected limit"

        # Test memory cleanup through eviction
        # Add more items to trigger eviction
        for i in range(cache_size, cache_size + 100):
            value = "x" * value_size
            await cache_service.set("memory_test", f"key_{i}", value)

        # Check that eviction occurred
        final_stats = cache_service.get_stats()
        assert final_stats["evictions"] > 0, "Expected cache evictions did not occur"


@pytest.mark.performance
class TestRegressionBenchmarks:
    """Benchmark tests for performance regression detection."""

    def test_api_performance_regression(self, mock_client):
        """Test for API performance regression."""
        fixtures = PerformanceFixtures()
        baseline_metrics = fixtures.create_baseline_metrics()

        # Perform API operations and measure
        iterations = 50
        response_times = []

        for _ in range(iterations):
            start = time.time()
            mock_client.get_ticker("tBTCUSD")
            end = time.time()
            response_times.append(end - start)

        avg_response_time = mean(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]

        # Compare with baseline
        baseline_avg = baseline_metrics.api_response_time_avg
        baseline_p95 = baseline_metrics.api_response_time_p95

        # Allow 20% performance degradation before failing
        max_avg_time = baseline_avg * 1.2
        max_p95_time = baseline_p95 * 1.2

        assert avg_response_time <= max_avg_time, (
            f"Average response time {avg_response_time:.3f}s exceeds baseline "
            f"{baseline_avg:.3f}s by more than 20%"
        )

        assert p95_response_time <= max_p95_time, (
            f"P95 response time {p95_response_time:.3f}s exceeds baseline "
            f"{baseline_p95:.3f}s by more than 20%"
        )

    async def test_cache_performance_regression(self, cache_service):
        """Test for cache performance regression."""
        fixtures = PerformanceFixtures()
        baseline_metrics = fixtures.create_baseline_metrics()

        # Pre-populate cache
        for i in range(100):
            await cache_service.set("regression_test", f"key_{i}", f"value_{i}")

        # Measure cache hit ratio
        hits = 0
        iterations = 200

        for i in range(iterations):
            key_index = i % 100  # 100% hit ratio expected
            result = await cache_service.get("regression_test", f"key_{key_index}")
            if result is not None:
                hits += 1

        hit_ratio = hits / iterations
        baseline_hit_ratio = baseline_metrics.cache_hit_ratio

        # Allow 10% degradation in hit ratio
        min_hit_ratio = baseline_hit_ratio * 0.9

        assert hit_ratio >= min_hit_ratio, (
            f"Cache hit ratio {hit_ratio:.3f} below baseline {baseline_hit_ratio:.3f} "
            f"by more than 10%"
        )


# Performance test utilities
def measure_execution_time(func, *args, **kwargs):
    """Utility to measure function execution time."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time = end_time - start_time
    return result, execution_time


async def measure_async_execution_time(func, *args, **kwargs):
    """Utility to measure async function execution time."""
    start_time = time.time()
    result = await func(*args, **kwargs)
    end_time = time.time()
    execution_time = end_time - start_time
    return result, execution_time
