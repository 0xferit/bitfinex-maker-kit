"""
Load and stress tests for Maker-Kit.

Comprehensive load testing to validate system behavior under
high load, concurrent users, and stress conditions.
"""

import asyncio
import random
import time
from statistics import mean

import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol

from ..mocks.service_mocks import create_mock_cache_service, create_mock_trading_service


@pytest.mark.load
class TestHighVolumeTrading:
    """Load tests for high volume trading scenarios."""

    @pytest.fixture
    def trading_service(self):
        """Create trading service for load testing."""
        return create_mock_trading_service("normal")

    @pytest.mark.asyncio
    async def test_high_frequency_order_placement(self, trading_service):
        """Test high frequency order placement load."""
        orders_per_second = 50
        test_duration = 10  # seconds
        total_orders = orders_per_second * test_duration

        start_time = time.time()
        successful_orders = 0
        failed_orders = 0
        response_times = []

        # Generate orders rapidly
        for i in range(total_orders):
            order_start = time.time()

            try:
                await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.01"),  # Small amounts for HFT
                    price=Price(f"{50000 + random.randint(-100, 100)}.0"),
                    side=random.choice(["buy", "sell"]),
                )
                successful_orders += 1

            except Exception:
                failed_orders += 1

            order_end = time.time()
            response_times.append((order_end - order_start) * 1000)  # ms

            # Maintain target rate
            expected_time = start_time + (i + 1) / orders_per_second
            current_time = time.time()
            if current_time < expected_time:
                await asyncio.sleep(expected_time - current_time)

        end_time = time.time()
        actual_duration = end_time - start_time
        actual_rate = total_orders / actual_duration

        # Analyze results
        success_rate = successful_orders / total_orders
        avg_response_time = mean(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]

        # Assert performance requirements
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
        assert actual_rate >= orders_per_second * 0.9, (
            f"Actual rate {actual_rate:.1f} ops/sec below target {orders_per_second} ops/sec"
        )
        assert avg_response_time < 100.0, (
            f"Average response time {avg_response_time:.1f}ms too high"
        )
        assert p95_response_time < 200.0, f"P95 response time {p95_response_time:.1f}ms too high"

    @pytest.mark.asyncio
    async def test_bulk_order_management(self, trading_service):
        """Test bulk order management under load."""
        batch_size = 100
        num_batches = 10

        all_order_ids = []
        batch_times = []

        # Place orders in batches
        for batch_num in range(num_batches):
            batch_orders = []

            for i in range(batch_size):
                batch_orders.append(
                    {
                        "symbol": "tBTCUSD",
                        "amount": "0.1",
                        "price": f"{50000 + batch_num * 100 + i}.0",
                        "side": "buy" if i % 2 == 0 else "sell",
                        "type": "EXCHANGE LIMIT",
                    }
                )

            # Time batch placement
            batch_start = time.time()
            results = await trading_service.place_batch_orders(batch_orders)
            batch_end = time.time()

            batch_times.append(batch_end - batch_start)

            # Collect order IDs
            for result in results:
                if "id" in result:
                    all_order_ids.append(result["id"])

        # Test bulk cancellation
        cancel_start = time.time()
        await trading_service.cancel_all_orders()
        cancel_end = time.time()

        cancel_time = cancel_end - cancel_start

        # Analyze batch performance
        avg_batch_time = mean(batch_times)
        total_orders = batch_size * num_batches
        overall_throughput = total_orders / sum(batch_times)

        # Assert bulk operation performance
        assert avg_batch_time < 5.0, f"Average batch time {avg_batch_time:.2f}s too high"
        assert overall_throughput >= 50, (
            f"Bulk throughput {overall_throughput:.1f} orders/sec too low"
        )
        assert cancel_time < 2.0, f"Bulk cancellation time {cancel_time:.2f}s too high"
        assert len(all_order_ids) >= total_orders * 0.95, "Too many order placement failures"

    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(self, trading_service):
        """Test concurrent user trading simulation."""
        num_users = 20
        operations_per_user = 25

        async def simulate_user_activity(user_id: int):
            """Simulate individual user trading activity."""
            user_stats = {
                "orders_placed": 0,
                "orders_cancelled": 0,
                "errors": 0,
                "response_times": [],
            }

            for op_num in range(operations_per_user):
                operation_start = time.time()

                try:
                    if op_num % 3 == 0:  # Cancel some orders
                        # Get active orders first
                        active_orders = await trading_service.get_active_orders()
                        if active_orders:
                            order_to_cancel = random.choice(active_orders)
                            await trading_service.cancel_order(str(order_to_cancel["id"]))
                            user_stats["orders_cancelled"] += 1
                    else:  # Place new orders
                        await trading_service.place_order(
                            symbol=Symbol("tBTCUSD"),
                            amount=Amount(f"{random.uniform(0.01, 0.5):.6f}"),
                            price=Price(f"{50000 + random.randint(-500, 500)}.0"),
                            side=random.choice(["buy", "sell"]),
                        )
                        user_stats["orders_placed"] += 1

                except Exception:
                    user_stats["errors"] += 1

                operation_end = time.time()
                user_stats["response_times"].append((operation_end - operation_start) * 1000)

                # Random delay between operations
                await asyncio.sleep(random.uniform(0.1, 0.5))

            return user_stats

        # Run concurrent users
        start_time = time.time()
        user_tasks = [simulate_user_activity(i) for i in range(num_users)]
        user_results = await asyncio.gather(*user_tasks)
        end_time = time.time()

        total_duration = end_time - start_time

        # Aggregate results
        total_operations = 0
        total_errors = 0
        all_response_times = []

        for user_stats in user_results:
            user_operations = user_stats["orders_placed"] + user_stats["orders_cancelled"]
            total_operations += user_operations
            total_errors += user_stats["errors"]
            all_response_times.extend(user_stats["response_times"])

        # Calculate metrics
        overall_success_rate = 1 - (total_errors / total_operations) if total_operations > 0 else 0
        operations_per_second = total_operations / total_duration
        avg_response_time = mean(all_response_times) if all_response_times else 0

        # Assert concurrent performance
        assert overall_success_rate >= 0.90, f"Success rate {overall_success_rate:.2%} below 90%"
        assert operations_per_second >= 15, (
            f"Concurrent throughput {operations_per_second:.1f} ops/sec too low"
        )
        assert avg_response_time < 500.0, (
            f"Average response time {avg_response_time:.1f}ms too high"
        )


@pytest.mark.load
class TestCacheLoadTests:
    """Load tests for cache performance under high load."""

    @pytest.fixture
    async def cache_service(self):
        """Create cache service for load testing."""
        cache = create_mock_cache_service("normal")
        yield cache
        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_high_volume_cache_operations(self, cache_service):
        """Test cache performance under high volume operations."""
        operations_per_second = 1000
        test_duration = 5  # seconds
        total_operations = operations_per_second * test_duration

        start_time = time.time()
        successful_ops = 0
        failed_ops = 0

        # Pre-populate cache
        for i in range(100):
            await cache_service.set("load_test", f"key_{i}", f"value_{i}")

        # Perform high volume operations
        for i in range(total_operations):
            time.time()

            try:
                if i % 3 == 0:  # 33% writes
                    await cache_service.set("load_test", f"key_{i % 200}", f"value_{i}")
                else:  # 67% reads
                    await cache_service.get("load_test", f"key_{i % 100}")

                successful_ops += 1

            except Exception:
                failed_ops += 1

            # Maintain target rate
            expected_time = start_time + (i + 1) / operations_per_second
            current_time = time.time()
            if current_time < expected_time:
                await asyncio.sleep(expected_time - current_time)

        end_time = time.time()
        actual_duration = end_time - start_time
        actual_rate = total_operations / actual_duration

        # Get cache statistics
        stats = cache_service.get_stats()
        success_rate = successful_ops / total_operations

        # Assert cache load performance
        assert success_rate >= 0.98, f"Cache success rate {success_rate:.2%} below 98%"
        assert actual_rate >= operations_per_second * 0.9, (
            f"Cache operation rate {actual_rate:.1f} ops/sec below target"
        )
        assert stats["hit_ratio"] >= 0.6, (
            f"Cache hit ratio {stats['hit_ratio']:.2f} too low under load"
        )

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache_service):
        """Test concurrent cache access patterns."""
        num_workers = 50
        operations_per_worker = 100

        async def cache_worker(worker_id: int):
            """Simulate cache worker operations."""
            worker_stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}

            for i in range(operations_per_worker):
                try:
                    if i % 4 == 0:  # 25% writes
                        await cache_service.set(
                            f"worker_{worker_id}", f"key_{i}", f"value_{worker_id}_{i}"
                        )
                        worker_stats["sets"] += 1
                    else:  # 75% reads
                        # Mix of worker-specific and shared keys
                        if i % 2 == 0:
                            key = f"key_{i % 20}"  # Shared keys
                            namespace = "shared"
                        else:
                            key = f"key_{i % 10}"  # Worker-specific keys
                            namespace = f"worker_{worker_id}"

                        result = await cache_service.get(namespace, key)
                        if result is not None:
                            worker_stats["hits"] += 1
                        else:
                            worker_stats["misses"] += 1

                except Exception:
                    worker_stats["errors"] += 1

            return worker_stats

        # Pre-populate shared cache
        for i in range(20):
            await cache_service.set("shared", f"key_{i}", f"shared_value_{i}")

        # Run concurrent workers
        start_time = time.time()
        worker_tasks = [cache_worker(i) for i in range(num_workers)]
        worker_results = await asyncio.gather(*worker_tasks)
        end_time = time.time()

        total_duration = end_time - start_time

        # Aggregate results
        total_hits = sum(w["hits"] for w in worker_results)
        total_misses = sum(w["misses"] for w in worker_results)
        total_sets = sum(w["sets"] for w in worker_results)
        total_errors = sum(w["errors"] for w in worker_results)

        total_operations = total_hits + total_misses + total_sets
        error_rate = total_errors / (total_operations + total_errors) if total_operations > 0 else 1
        hit_ratio = (
            total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        )
        ops_per_second = total_operations / total_duration

        # Assert concurrent cache performance
        assert error_rate <= 0.01, f"Cache error rate {error_rate:.2%} too high"
        assert hit_ratio >= 0.4, f"Cache hit ratio {hit_ratio:.2f} too low under concurrent load"
        assert ops_per_second >= 500, (
            f"Concurrent cache throughput {ops_per_second:.1f} ops/sec too low"
        )


@pytest.mark.load
class TestSystemStressTests:
    """Stress tests for overall system limits."""

    @pytest.mark.asyncio
    async def test_memory_stress(self):
        """Test system behavior under memory stress."""
        # Create many domain objects to stress memory
        large_datasets = []

        try:
            # Create increasingly large datasets
            for size in [1000, 5000, 10000, 20000]:
                dataset = {
                    "symbols": [Symbol("tBTCUSD") for _ in range(size)],
                    "prices": [Price(f"{50000 + i}.0") for i in range(size)],
                    "amounts": [Amount(f"{i * 0.001:.6f}") for i in range(1, size + 1)],
                }
                large_datasets.append(dataset)

                # Verify objects are still functional
                sample_symbol = dataset["symbols"][0]
                sample_price = dataset["prices"][0]
                sample_amount = dataset["amounts"][0]

                assert str(sample_symbol) == "tBTCUSD"
                assert sample_price.value > 0
                assert sample_amount.value > 0

        except MemoryError:
            pytest.fail("System ran out of memory during stress test")

        # Test cleanup
        del large_datasets

        # Verify system is still responsive
        test_symbol = Symbol("tETHUSD")
        assert str(test_symbol) == "tETHUSD"

    @pytest.mark.asyncio
    async def test_error_cascade_resilience(self, trading_service):
        """Test system resilience to error cascades."""
        error_count = 0
        success_count = 0

        # Simulate mixed success/failure scenario
        for i in range(100):
            try:
                if i % 5 == 0:  # 20% error rate
                    # Force error by invalid parameters
                    trading_service._trading_service.get_client().submit_order.side_effect = (
                        Exception("Simulated error")
                    )
                else:
                    # Reset to normal behavior
                    trading_service._trading_service.get_client().submit_order.side_effect = None

                await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.1"),
                    price=Price(f"{50000 + i}.0"),
                    side="buy",
                )
                success_count += 1

            except Exception:
                error_count += 1

        # Verify system maintained partial functionality
        success_rate = success_count / (success_count + error_count)
        assert success_rate >= 0.75, f"System success rate {success_rate:.2%} too low under errors"

        # Verify system can recover
        trading_service._trading_service.get_client().submit_order.side_effect = None

        recovery_result = await trading_service.place_order(
            symbol=Symbol("tBTCUSD"), amount=Amount("0.1"), price=Price("50000.0"), side="buy"
        )

        assert recovery_result is not None, "System failed to recover after error cascade"

    @pytest.mark.asyncio
    async def test_resource_exhaustion_handling(self):
        """Test handling of resource exhaustion scenarios."""
        # Test large number of concurrent operations
        max_concurrent = 1000

        async def resource_intensive_operation(op_id: int):
            """Simulate resource-intensive operation."""
            # Create temporary objects
            temp_data = {
                "symbols": [Symbol("tBTCUSD") for _ in range(10)],
                "prices": [Price(f"{50000 + i}.0") for i in range(10)],
                "operation_id": op_id,
            }

            # Simulate processing time
            await asyncio.sleep(0.01)

            return len(temp_data["symbols"])

        # Launch many concurrent operations
        start_time = time.time()

        try:
            tasks = [resource_intensive_operation(i) for i in range(max_concurrent)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            duration = end_time - start_time

            # Analyze results
            successful_ops = [r for r in results if isinstance(r, int)]
            [r for r in results if isinstance(r, Exception)]

            success_rate = len(successful_ops) / len(results)
            ops_per_second = len(successful_ops) / duration

            # Assert resource handling
            assert success_rate >= 0.95, (
                f"Resource exhaustion success rate {success_rate:.2%} too low"
            )
            assert ops_per_second >= 50, (
                f"Resource exhaustion throughput {ops_per_second:.1f} ops/sec too low"
            )
            assert duration < 30.0, f"Resource exhaustion test took too long: {duration:.1f}s"

        except Exception as e:
            pytest.fail(f"Resource exhaustion test failed with exception: {e}")


@pytest.mark.load
@pytest.mark.slow
class TestEnduranceTests:
    """Long-running endurance tests."""

    @pytest.mark.asyncio
    async def test_sustained_operation_endurance(self, trading_service):
        """Test sustained operations over extended period."""
        test_duration = 60  # 1 minute for CI/CD compatibility
        operations_per_minute = 300  # 5 ops/sec

        start_time = time.time()
        operation_count = 0
        error_count = 0

        while time.time() - start_time < test_duration:
            try:
                await trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount("0.01"),
                    price=Price(f"{50000 + operation_count % 1000}.0"),
                    side="buy" if operation_count % 2 == 0 else "sell",
                )
                operation_count += 1

                # Maintain target rate
                target_interval = 60 / operations_per_minute  # seconds per operation
                await asyncio.sleep(target_interval)

            except Exception:
                error_count += 1

        end_time = time.time()
        actual_duration = end_time - start_time
        actual_rate = operation_count / (actual_duration / 60)  # ops per minute
        error_rate = error_count / (operation_count + error_count) if operation_count > 0 else 1

        # Assert endurance performance
        assert error_rate <= 0.05, f"Endurance error rate {error_rate:.2%} too high"
        assert actual_rate >= operations_per_minute * 0.9, (
            f"Endurance rate {actual_rate:.1f} ops/min below target {operations_per_minute} ops/min"
        )
        assert operation_count >= 250, f"Too few operations completed: {operation_count}"
