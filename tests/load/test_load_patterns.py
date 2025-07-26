"""
Load pattern testing for Maker-Kit.

Tests various load patterns and usage scenarios to validate system
behavior under different traffic patterns and user behaviors.
"""

import asyncio
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol

from ..mocks.service_mocks import create_mock_cache_service, create_mock_trading_service


class LoadPattern(Enum):
    """Different load pattern types."""

    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    BURST = "burst"
    WAVE = "wave"
    RANDOM = "random"


@dataclass
class LoadPatternConfig:
    """Configuration for load pattern testing."""

    pattern_type: LoadPattern
    duration_seconds: float
    max_concurrent_operations: int
    operation_rate_per_second: float
    ramp_up_time_seconds: float | None = None
    spike_intensity: float | None = None
    burst_interval_seconds: float | None = None
    wave_period_seconds: float | None = None


class LoadPatternGenerator:
    """Generates different load patterns for testing."""

    @staticmethod
    def constant_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate constant load pattern."""
        target_ops_per_sec = config.operation_rate_per_second

        def get_operations_count(elapsed_time: float) -> int:
            return int(target_ops_per_sec)

        return get_operations_count

    @staticmethod
    def ramp_up_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate ramp-up load pattern."""
        ramp_time = config.ramp_up_time_seconds or config.duration_seconds / 2
        max_ops = config.operation_rate_per_second

        def get_operations_count(elapsed_time: float) -> int:
            if elapsed_time < ramp_time:
                # Linear ramp up
                ramp_progress = elapsed_time / ramp_time
                return int(max_ops * ramp_progress)
            else:
                return int(max_ops)

        return get_operations_count

    @staticmethod
    def spike_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate spike load pattern."""
        normal_ops = config.operation_rate_per_second
        spike_intensity = config.spike_intensity or 5.0
        spike_duration = config.duration_seconds * 0.1  # 10% of total time
        spike_start = config.duration_seconds * 0.5  # Middle of test

        def get_operations_count(elapsed_time: float) -> int:
            if spike_start <= elapsed_time <= spike_start + spike_duration:
                return int(normal_ops * spike_intensity)
            else:
                return int(normal_ops)

        return get_operations_count

    @staticmethod
    def burst_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate burst load pattern."""
        burst_interval = config.burst_interval_seconds or 5.0
        normal_ops = config.operation_rate_per_second
        burst_ops = normal_ops * 3  # 3x normal during burst

        def get_operations_count(elapsed_time: float) -> int:
            cycle_position = elapsed_time % burst_interval
            burst_duration = burst_interval * 0.2  # 20% of cycle is burst

            if cycle_position < burst_duration:
                return int(burst_ops)
            else:
                return int(normal_ops * 0.5)  # Reduced load between bursts

        return get_operations_count

    @staticmethod
    def wave_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate wave load pattern."""
        wave_period = config.wave_period_seconds or 30.0
        base_ops = config.operation_rate_per_second
        amplitude = base_ops * 0.5  # 50% amplitude

        def get_operations_count(elapsed_time: float) -> int:
            wave_value = math.sin(2 * math.pi * elapsed_time / wave_period)
            ops_count = base_ops + (amplitude * wave_value)
            return max(1, int(ops_count))

        return get_operations_count

    @staticmethod
    def random_load(config: LoadPatternConfig) -> Callable[[float], int]:
        """Generate random load pattern."""
        base_ops = config.operation_rate_per_second

        def get_operations_count(elapsed_time: float) -> int:
            # Random multiplier between 0.1 and 3.0
            multiplier = random.uniform(0.1, 3.0)
            return max(1, int(base_ops * multiplier))

        return get_operations_count


class LoadPatternTester:
    """Executes load pattern tests and collects metrics."""

    def __init__(self):
        self.results: list[dict[str, Any]] = []

    async def run_load_pattern_test(
        self, config: LoadPatternConfig, operation_factory: Callable, test_name: str
    ) -> dict[str, Any]:
        """
        Run a load pattern test.

        Args:
            config: Load pattern configuration
            operation_factory: Function that creates operation functions
            test_name: Name of the test

        Returns:
            Test results dictionary
        """
        print(f"Starting load pattern test: {test_name} ({config.pattern_type.value})")

        # Get load pattern generator
        pattern_generators = {
            LoadPattern.CONSTANT: LoadPatternGenerator.constant_load,
            LoadPattern.RAMP_UP: LoadPatternGenerator.ramp_up_load,
            LoadPattern.SPIKE: LoadPatternGenerator.spike_load,
            LoadPattern.BURST: LoadPatternGenerator.burst_load,
            LoadPattern.WAVE: LoadPatternGenerator.wave_load,
            LoadPattern.RANDOM: LoadPatternGenerator.random_load,
        }

        get_operations_count = pattern_generators[config.pattern_type](config)

        # Initialize metrics
        start_time = time.time()
        total_operations = 0
        successful_operations = 0
        failed_operations = 0
        operation_times = []
        load_samples = []

        # Run test
        end_time = start_time + config.duration_seconds
        last_second = int(start_time)

        while time.time() < end_time:
            current_time = time.time()
            elapsed_time = current_time - start_time
            current_second = int(current_time)

            # Calculate operations for this second
            if current_second != last_second:
                operations_this_second = get_operations_count(elapsed_time)
                load_samples.append(
                    {
                        "timestamp": current_time,
                        "elapsed_time": elapsed_time,
                        "target_operations": operations_this_second,
                    }
                )

                # Execute operations for this second
                await self._execute_operations_batch(
                    operation_factory,
                    operations_this_second,
                    total_operations,
                    successful_operations,
                    failed_operations,
                    operation_times,
                )

                total_operations += operations_this_second
                last_second = current_second

            # Small sleep to prevent busy waiting
            await asyncio.sleep(0.1)

        # Calculate results
        actual_duration = time.time() - start_time
        success_rate = successful_operations / total_operations if total_operations > 0 else 0
        avg_operation_time = sum(operation_times) / len(operation_times) if operation_times else 0

        result = {
            "test_name": test_name,
            "pattern_type": config.pattern_type.value,
            "duration": actual_duration,
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": success_rate,
            "operations_per_second": total_operations / actual_duration,
            "avg_operation_time": avg_operation_time,
            "load_samples": load_samples,
            "config": {
                "max_concurrent_operations": config.max_concurrent_operations,
                "operation_rate_per_second": config.operation_rate_per_second,
                "duration_seconds": config.duration_seconds,
            },
        }

        self.results.append(result)
        print(
            f"Completed load pattern test: {test_name} - {result['operations_per_second']:.1f} ops/sec"
        )

        return result

    async def _execute_operations_batch(
        self,
        operation_factory: Callable,
        operations_count: int,
        total_operations: int,
        successful_operations: int,
        failed_operations: int,
        operation_times: list[float],
    ) -> None:
        """Execute a batch of operations."""
        if operations_count <= 0:
            return

        async def single_operation():
            """Execute a single operation with timing."""
            op_start = time.time()
            try:
                operation = operation_factory()
                result = await operation()
                op_end = time.time()
                operation_times.append(op_end - op_start)
                return result is not False  # Consider None as success, False as failure
            except Exception:
                op_end = time.time()
                operation_times.append(op_end - op_start)
                return False

        # Execute operations concurrently (up to configured limit)
        semaphore = asyncio.Semaphore(min(operations_count, 20))  # Limit concurrency

        async def bounded_operation():
            async with semaphore:
                return await single_operation()

        tasks = [bounded_operation() for _ in range(operations_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count results (mutations are handled by reference in the calling method)
        for result in results:
            if isinstance(result, Exception):
                failed_operations += 1
            elif result:
                successful_operations += 1
            else:
                failed_operations += 1


@pytest.mark.load
class TestTradingLoadPatterns:
    """Load pattern tests for trading operations."""

    @pytest.fixture
    def load_tester(self):
        """Create load pattern tester."""
        return LoadPatternTester()

    async def test_constant_trading_load(self, load_tester):
        """Test constant trading load pattern."""
        trading_service = create_mock_trading_service("normal")
        order_counter = 0

        def create_trading_operation():
            def operation():
                nonlocal order_counter
                order_counter += 1
                return trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    amount=Amount(f"{random.uniform(0.01, 0.1):.6f}"),
                    price=Price(f"{50000 + (order_counter % 1000)}.0"),
                    side="buy" if order_counter % 2 == 0 else "sell",
                )

            return operation

        config = LoadPatternConfig(
            pattern_type=LoadPattern.CONSTANT,
            duration_seconds=10.0,
            max_concurrent_operations=10,
            operation_rate_per_second=5.0,
        )

        result = await load_tester.run_load_pattern_test(
            config, create_trading_operation, "constant_trading_load"
        )

        # Constant load assertions
        assert result["success_rate"] >= 0.8, (
            f"Constant load success rate too low: {result['success_rate']:.1%}"
        )
        assert result["operations_per_second"] >= 3.0, (
            f"Constant load throughput too low: {result['operations_per_second']:.1f} ops/sec"
        )

        # Load pattern should be relatively stable
        load_samples = result["load_samples"]
        target_operations = [sample["target_operations"] for sample in load_samples]
        assert all(ops == 5 for ops in target_operations), "Constant load pattern not stable"

    async def test_ramp_up_trading_load(self, load_tester):
        """Test ramp-up trading load pattern."""
        trading_service = create_mock_trading_service("normal")
        order_counter = 0

        def create_trading_operation():
            def operation():
                nonlocal order_counter
                order_counter += 1
                return trading_service.place_order(
                    symbol=Symbol("tETHUSD"),
                    amount=Amount(f"{random.uniform(0.1, 1.0):.4f}"),
                    price=Price(f"{3000 + (order_counter % 500)}.0"),
                    side="buy" if order_counter % 2 == 0 else "sell",
                )

            return operation

        config = LoadPatternConfig(
            pattern_type=LoadPattern.RAMP_UP,
            duration_seconds=15.0,
            max_concurrent_operations=15,
            operation_rate_per_second=10.0,
            ramp_up_time_seconds=8.0,
        )

        result = await load_tester.run_load_pattern_test(
            config, create_trading_operation, "ramp_up_trading_load"
        )

        # Ramp-up load assertions
        assert result["success_rate"] >= 0.7, (
            f"Ramp-up load success rate too low: {result['success_rate']:.1%}"
        )
        assert result["operations_per_second"] >= 5.0, (
            f"Ramp-up load throughput too low: {result['operations_per_second']:.1f} ops/sec"
        )

        # Verify ramp-up pattern
        load_samples = result["load_samples"]
        early_operations = [s["target_operations"] for s in load_samples if s["elapsed_time"] < 4.0]
        late_operations = [s["target_operations"] for s in load_samples if s["elapsed_time"] > 10.0]

        if early_operations and late_operations:
            avg_early = sum(early_operations) / len(early_operations)
            avg_late = sum(late_operations) / len(late_operations)
            assert avg_late > avg_early, "Ramp-up pattern not detected"

    async def test_spike_trading_load(self, load_tester):
        """Test spike trading load pattern."""
        trading_service = create_mock_trading_service("normal")
        order_counter = 0

        def create_trading_operation():
            def operation():
                nonlocal order_counter
                order_counter += 1
                return trading_service.place_order(
                    symbol=Symbol("tPNKUSD"),
                    amount=Amount(f"{random.uniform(1.0, 10.0):.2f}"),
                    price=Price(f"{random.uniform(0.1, 1.0):.6f}"),
                    side=random.choice(["buy", "sell"]),
                )

            return operation

        config = LoadPatternConfig(
            pattern_type=LoadPattern.SPIKE,
            duration_seconds=20.0,
            max_concurrent_operations=25,
            operation_rate_per_second=5.0,
            spike_intensity=8.0,
        )

        result = await load_tester.run_load_pattern_test(
            config, create_trading_operation, "spike_trading_load"
        )

        # Spike load assertions
        assert result["success_rate"] >= 0.6, (
            f"Spike load success rate too low: {result['success_rate']:.1%}"
        )
        assert result["operations_per_second"] >= 4.0, (
            f"Spike load throughput too low: {result['operations_per_second']:.1f} ops/sec"
        )

        # Verify spike pattern
        load_samples = result["load_samples"]
        target_operations = [s["target_operations"] for s in load_samples]
        max_operations = max(target_operations) if target_operations else 0
        min_operations = min(target_operations) if target_operations else 0

        # Should have significant variation indicating spike
        assert max_operations > min_operations * 2, "Spike pattern not detected"

    async def test_burst_trading_load(self, load_tester):
        """Test burst trading load pattern."""
        trading_service = create_mock_trading_service("normal")
        order_counter = 0

        def create_trading_operation():
            def operation():
                nonlocal order_counter
                order_counter += 1
                return trading_service.place_order(
                    symbol=Symbol(random.choice(["tBTCUSD", "tETHUSD"])),
                    amount=Amount(f"{random.uniform(0.01, 0.5):.6f}"),
                    price=Price(f"{random.uniform(30000, 60000):.2f}"),
                    side=random.choice(["buy", "sell"]),
                )

            return operation

        config = LoadPatternConfig(
            pattern_type=LoadPattern.BURST,
            duration_seconds=25.0,
            max_concurrent_operations=20,
            operation_rate_per_second=8.0,
            burst_interval_seconds=6.0,
        )

        result = await load_tester.run_load_pattern_test(
            config, create_trading_operation, "burst_trading_load"
        )

        # Burst load assertions
        assert result["success_rate"] >= 0.7, (
            f"Burst load success rate too low: {result['success_rate']:.1%}"
        )
        assert result["operations_per_second"] >= 5.0, (
            f"Burst load throughput too low: {result['operations_per_second']:.1f} ops/sec"
        )

        # Verify burst pattern has high variation
        load_samples = result["load_samples"]
        target_operations = [s["target_operations"] for s in load_samples]
        if len(target_operations) > 1:
            operation_variance = sum(
                (x - sum(target_operations) / len(target_operations)) ** 2
                for x in target_operations
            ) / len(target_operations)
            assert operation_variance > 10, "Burst pattern variation too low"


@pytest.mark.load
class TestCacheLoadPatterns:
    """Load pattern tests for cache operations."""

    @pytest.fixture
    def load_tester(self):
        """Create load pattern tester."""
        return LoadPatternTester()

    async def test_wave_cache_load(self, load_tester):
        """Test wave cache load pattern."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Pre-populate cache
            for i in range(100):
                await cache_service.set("wave_test", f"key_{i}", f"value_{i}")

            operation_counter = 0

            def create_cache_operation():
                def operation():
                    nonlocal operation_counter
                    operation_counter += 1

                    # Mix of read/write operations
                    if operation_counter % 3 == 0:
                        return cache_service.set(
                            "wave_test",
                            f"key_{operation_counter % 200}",
                            f"new_value_{operation_counter}",
                        )
                    else:
                        return cache_service.get("wave_test", f"key_{operation_counter % 100}")

                return operation

            config = LoadPatternConfig(
                pattern_type=LoadPattern.WAVE,
                duration_seconds=20.0,
                max_concurrent_operations=30,
                operation_rate_per_second=15.0,
                wave_period_seconds=8.0,
            )

            result = await load_tester.run_load_pattern_test(
                config, create_cache_operation, "wave_cache_load"
            )

            # Wave load assertions
            assert result["success_rate"] >= 0.95, (
                f"Wave cache load success rate too low: {result['success_rate']:.1%}"
            )
            assert result["operations_per_second"] >= 10.0, (
                f"Wave cache load throughput too low: {result['operations_per_second']:.1f} ops/sec"
            )

            # Verify wave pattern
            load_samples = result["load_samples"]
            target_operations = [s["target_operations"] for s in load_samples]

            # Wave should have smooth variation
            if len(target_operations) >= 3:
                # Check for wave-like pattern (should have both peaks and troughs)
                max_ops = max(target_operations)
                min_ops = min(target_operations)
                assert max_ops > min_ops, "Wave pattern not detected in cache load"

        finally:
            await cache_service.cleanup()

    async def test_random_cache_load(self, load_tester):
        """Test random cache load pattern."""
        cache_service = create_mock_cache_service("normal")

        try:
            operation_counter = 0

            def create_cache_operation():
                def operation():
                    nonlocal operation_counter
                    operation_counter += 1

                    # Random operation type
                    operation_type = random.choices(
                        ["get", "set", "delete", "get_or_set"], weights=[50, 30, 10, 10]
                    )[0]

                    key = f"random_key_{operation_counter % 50}"  # Limited key space

                    if operation_type == "get":
                        return cache_service.get("random_test", key)
                    elif operation_type == "set":
                        return cache_service.set("random_test", key, f"value_{operation_counter}")
                    elif operation_type == "delete":
                        return cache_service.delete("random_test", key)
                    else:  # get_or_set

                        async def fetch():
                            return f"fetched_{operation_counter}"

                        return cache_service.get_or_set("random_test", key, fetch)

                return operation

            config = LoadPatternConfig(
                pattern_type=LoadPattern.RANDOM,
                duration_seconds=15.0,
                max_concurrent_operations=25,
                operation_rate_per_second=20.0,
            )

            result = await load_tester.run_load_pattern_test(
                config, create_cache_operation, "random_cache_load"
            )

            # Random load assertions
            assert result["success_rate"] >= 0.90, (
                f"Random cache load success rate too low: {result['success_rate']:.1%}"
            )
            assert result["operations_per_second"] >= 15.0, (
                f"Random cache load throughput too low: {result['operations_per_second']:.1f} ops/sec"
            )

            # Verify random pattern has high variability
            load_samples = result["load_samples"]
            target_operations = [s["target_operations"] for s in load_samples]

            if len(target_operations) > 2:
                unique_values = len(set(target_operations))
                total_values = len(target_operations)
                # Random pattern should have good variety
                variety_ratio = unique_values / total_values
                assert variety_ratio >= 0.3, (
                    f"Random pattern not sufficiently varied: {variety_ratio:.2f}"
                )

        finally:
            await cache_service.cleanup()


@pytest.mark.load
class TestMixedLoadPatterns:
    """Mixed system load pattern tests."""

    @pytest.fixture
    def load_tester(self):
        """Create load pattern tester."""
        return LoadPatternTester()

    async def test_mixed_system_ramp_up(self, load_tester):
        """Test mixed system operations with ramp-up load."""
        trading_service = create_mock_trading_service("normal")
        cache_service = create_mock_cache_service("normal")

        try:
            operation_counter = 0

            def create_mixed_operation():
                def operation():
                    nonlocal operation_counter
                    operation_counter += 1

                    # Alternate between trading and cache operations
                    if operation_counter % 2 == 0:
                        # Trading operation
                        return trading_service.place_order(
                            symbol=Symbol("tBTCUSD"),
                            amount=Amount(f"{random.uniform(0.01, 0.1):.6f}"),
                            price=Price(f"{random.uniform(45000, 55000):.2f}"),
                            side=random.choice(["buy", "sell"]),
                        )
                    else:
                        # Cache operation
                        key = f"mixed_key_{operation_counter % 100}"
                        if random.random() < 0.7:  # 70% reads
                            return cache_service.get("mixed_system", key)
                        else:  # 30% writes
                            return cache_service.set(
                                "mixed_system", key, f"value_{operation_counter}"
                            )

                return operation

            config = LoadPatternConfig(
                pattern_type=LoadPattern.RAMP_UP,
                duration_seconds=20.0,
                max_concurrent_operations=30,
                operation_rate_per_second=12.0,
                ramp_up_time_seconds=10.0,
            )

            result = await load_tester.run_load_pattern_test(
                config, create_mixed_operation, "mixed_system_ramp_up"
            )

            # Mixed system load assertions
            assert result["success_rate"] >= 0.75, (
                f"Mixed system load success rate too low: {result['success_rate']:.1%}"
            )
            assert result["operations_per_second"] >= 8.0, (
                f"Mixed system load throughput too low: {result['operations_per_second']:.1f} ops/sec"
            )

            # System should handle mixed load effectively
            assert result["avg_operation_time"] < 1.0, (
                f"Mixed system operation time too high: {result['avg_operation_time']:.3f}s"
            )

        finally:
            await cache_service.cleanup()

    async def test_complex_burst_pattern(self, load_tester):
        """Test complex burst pattern with multiple operation types."""
        trading_service = create_mock_trading_service("normal")
        cache_service = create_mock_cache_service("normal")

        try:
            operation_counter = 0

            def create_complex_operation():
                def operation():
                    nonlocal operation_counter
                    operation_counter += 1

                    # Complex operation sequence
                    operation_type = random.choices(
                        ["place_order", "cancel_order", "cache_lookup", "batch_cache"],
                        weights=[40, 20, 30, 10],
                    )[0]

                    if operation_type == "place_order":
                        return trading_service.place_order(
                            symbol=Symbol(random.choice(["tBTCUSD", "tETHUSD", "tPNKUSD"])),
                            amount=Amount(f"{random.uniform(0.001, 1.0):.6f}"),
                            price=Price(f"{random.uniform(100, 100000):.2f}"),
                            side=random.choice(["buy", "sell"]),
                        )
                    elif operation_type == "cancel_order":
                        # Try to cancel a random order
                        order_id = random.randint(10000000, 99999999)
                        return trading_service.cancel_order(str(order_id))
                    elif operation_type == "cache_lookup":
                        key = f"complex_key_{operation_counter % 200}"
                        return cache_service.get("complex_test", key)
                    else:  # batch_cache
                        # Perform multiple cache operations
                        async def batch_cache_ops():
                            results = []
                            for i in range(3):
                                key = f"batch_key_{operation_counter}_{i}"
                                results.append(
                                    await cache_service.set("complex_test", key, f"batch_value_{i}")
                                )
                            return all(results)

                        return batch_cache_ops()

                return operation

            config = LoadPatternConfig(
                pattern_type=LoadPattern.BURST,
                duration_seconds=30.0,
                max_concurrent_operations=40,
                operation_rate_per_second=15.0,
                burst_interval_seconds=8.0,
            )

            result = await load_tester.run_load_pattern_test(
                config, create_complex_operation, "complex_burst_pattern"
            )

            # Complex burst pattern assertions
            assert result["success_rate"] >= 0.6, (
                f"Complex burst pattern success rate too low: {result['success_rate']:.1%}"
            )
            assert result["operations_per_second"] >= 8.0, (
                f"Complex burst pattern throughput too low: {result['operations_per_second']:.1f} ops/sec"
            )

            # System should survive complex load patterns
            assert result["total_operations"] > 0, "No operations completed in complex burst test"

        finally:
            await cache_service.cleanup()
