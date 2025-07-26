"""
Performance data fixtures for testing.

Provides realistic performance scenarios and benchmarks
for comprehensive performance testing and validation.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsFixture:
    """Fixture for performance metrics."""

    timestamp: float = field(default_factory=time.time)
    api_calls_total: int = 0
    api_calls_per_second: float = 0.0
    api_response_time_avg: float = 0.0
    api_response_time_p95: float = 0.0
    api_response_time_p99: float = 0.0
    cache_hit_ratio: float = 0.0
    cache_hits_total: int = 0
    cache_misses_total: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "timestamp": self.timestamp,
            "api_performance": {
                "total_calls": self.api_calls_total,
                "calls_per_second": self.api_calls_per_second,
                "avg_response_time_ms": self.api_response_time_avg * 1000,
                "p95_response_time_ms": self.api_response_time_p95 * 1000,
                "p99_response_time_ms": self.api_response_time_p99 * 1000,
                "error_rate_pct": self.error_rate * 100,
            },
            "cache_performance": {
                "hit_ratio": self.cache_hit_ratio,
                "total_hits": self.cache_hits_total,
                "total_misses": self.cache_misses_total,
            },
            "system_resources": {
                "memory_usage_mb": self.memory_usage_mb,
                "cpu_usage_pct": self.cpu_usage_percent,
            },
        }


@dataclass
class ProfileDataFixture:
    """Fixture for profiling data."""

    function_name: str
    total_calls: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = 0.0
    max_time: float = 0.0
    memory_usage: int | None = None

    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_calls > 0 and self.total_time > 0:
            self.avg_time = self.total_time / self.total_calls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "function_name": self.function_name,
            "total_calls": self.total_calls,
            "total_time": self.total_time,
            "avg_time": self.avg_time,
            "min_time": self.min_time,
            "max_time": self.max_time,
            "memory_usage": self.memory_usage,
        }


@dataclass
class BenchmarkFixture:
    """Fixture for benchmark data."""

    test_name: str
    operations_per_second: float = 0.0
    total_operations: int = 0
    total_time: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "test_name": self.test_name,
            "operations_per_second": self.operations_per_second,
            "total_operations": self.total_operations,
            "total_time": self.total_time,
            "success_rate": self.success_rate,
            "error_count": self.error_count,
        }


class PerformanceFixtures:
    """
    Factory class for creating comprehensive performance data fixtures.

    Provides realistic performance scenarios for testing monitoring,
    profiling, and benchmarking functionality.
    """

    @classmethod
    def create_baseline_metrics(cls) -> MetricsFixture:
        """Create baseline performance metrics."""
        return MetricsFixture(
            api_calls_total=1000,
            api_calls_per_second=10.0,
            api_response_time_avg=0.1,  # 100ms
            api_response_time_p95=0.2,  # 200ms
            api_response_time_p99=0.5,  # 500ms
            cache_hit_ratio=0.85,
            cache_hits_total=850,
            cache_misses_total=150,
            memory_usage_mb=256.0,
            cpu_usage_percent=25.0,
            error_rate=0.01,  # 1%
        )

    @classmethod
    def create_high_load_metrics(cls) -> MetricsFixture:
        """Create high load performance metrics."""
        return MetricsFixture(
            api_calls_total=10000,
            api_calls_per_second=50.0,
            api_response_time_avg=0.3,  # 300ms
            api_response_time_p95=0.8,  # 800ms
            api_response_time_p99=1.5,  # 1500ms
            cache_hit_ratio=0.75,
            cache_hits_total=7500,
            cache_misses_total=2500,
            memory_usage_mb=512.0,
            cpu_usage_percent=75.0,
            error_rate=0.05,  # 5%
        )

    @classmethod
    def create_stressed_metrics(cls) -> MetricsFixture:
        """Create stressed system performance metrics."""
        return MetricsFixture(
            api_calls_total=50000,
            api_calls_per_second=100.0,
            api_response_time_avg=1.0,  # 1000ms
            api_response_time_p95=2.0,  # 2000ms
            api_response_time_p99=5.0,  # 5000ms
            cache_hit_ratio=0.60,
            cache_hits_total=30000,
            cache_misses_total=20000,
            memory_usage_mb=1024.0,
            cpu_usage_percent=95.0,
            error_rate=0.15,  # 15%
        )

    @classmethod
    def create_optimized_metrics(cls) -> MetricsFixture:
        """Create optimized performance metrics."""
        return MetricsFixture(
            api_calls_total=5000,
            api_calls_per_second=25.0,
            api_response_time_avg=0.05,  # 50ms
            api_response_time_p95=0.1,  # 100ms
            api_response_time_p99=0.2,  # 200ms
            cache_hit_ratio=0.95,
            cache_hits_total=4750,
            cache_misses_total=250,
            memory_usage_mb=128.0,
            cpu_usage_percent=15.0,
            error_rate=0.001,  # 0.1%
        )

    @classmethod
    def create_profile_data(
        cls, function_name: str, scenario: str = "normal"
    ) -> ProfileDataFixture:
        """Create profiling data for a function."""
        scenarios = {
            "fast": {
                "total_calls": 1000,
                "total_time": 0.1,
                "min_time": 0.00001,
                "max_time": 0.001,
                "memory_usage": 1024,
            },
            "normal": {
                "total_calls": 500,
                "total_time": 1.0,
                "min_time": 0.0001,
                "max_time": 0.01,
                "memory_usage": 4096,
            },
            "slow": {
                "total_calls": 100,
                "total_time": 5.0,
                "min_time": 0.01,
                "max_time": 0.5,
                "memory_usage": 16384,
            },
            "heavy": {
                "total_calls": 50,
                "total_time": 10.0,
                "min_time": 0.1,
                "max_time": 2.0,
                "memory_usage": 65536,
            },
        }

        data = scenarios.get(scenario, scenarios["normal"])

        return ProfileDataFixture(function_name=function_name, **data)

    @classmethod
    def create_benchmark_suite(cls) -> dict[str, BenchmarkFixture]:
        """Create comprehensive benchmark suite."""
        return {
            "api_throughput": BenchmarkFixture(
                test_name="API Throughput Test",
                operations_per_second=50.0,
                total_operations=5000,
                total_time=100.0,
                success_rate=0.98,
                error_count=100,
            ),
            "cache_performance": BenchmarkFixture(
                test_name="Cache Performance Test",
                operations_per_second=1000.0,
                total_operations=100000,
                total_time=100.0,
                success_rate=1.0,
                error_count=0,
            ),
            "order_processing": BenchmarkFixture(
                test_name="Order Processing Test",
                operations_per_second=20.0,
                total_operations=2000,
                total_time=100.0,
                success_rate=0.95,
                error_count=100,
            ),
            "websocket_throughput": BenchmarkFixture(
                test_name="WebSocket Throughput Test",
                operations_per_second=500.0,
                total_operations=50000,
                total_time=100.0,
                success_rate=0.99,
                error_count=500,
            ),
            "memory_efficiency": BenchmarkFixture(
                test_name="Memory Efficiency Test",
                operations_per_second=100.0,
                total_operations=10000,
                total_time=100.0,
                success_rate=1.0,
                error_count=0,
            ),
        }

    @classmethod
    def create_regression_test_data(cls) -> dict[str, list[MetricsFixture]]:
        """Create regression test performance data."""
        # Simulate performance over time
        baseline = cls.create_baseline_metrics()

        # Generate degraded performance scenarios
        scenarios = {
            "performance_regression": [],
            "memory_leak": [],
            "cache_degradation": [],
            "api_slowdown": [],
        }

        # Performance regression (gradual slowdown)
        for i in range(10):
            degradation_factor = 1 + (i * 0.1)  # 10% degradation per step
            metrics = MetricsFixture(
                timestamp=baseline.timestamp + (i * 3600),  # 1 hour intervals
                api_calls_total=baseline.api_calls_total,
                api_response_time_avg=baseline.api_response_time_avg * degradation_factor,
                api_response_time_p95=baseline.api_response_time_p95 * degradation_factor,
                api_response_time_p99=baseline.api_response_time_p99 * degradation_factor,
                cache_hit_ratio=baseline.cache_hit_ratio,
                memory_usage_mb=baseline.memory_usage_mb,
                cpu_usage_percent=baseline.cpu_usage_percent * degradation_factor,
                error_rate=baseline.error_rate,
            )
            scenarios["performance_regression"].append(metrics)

        # Memory leak (growing memory usage)
        for i in range(10):
            memory_growth = baseline.memory_usage_mb * (1 + (i * 0.2))  # 20% growth per step
            metrics = MetricsFixture(
                timestamp=baseline.timestamp + (i * 3600),
                api_calls_total=baseline.api_calls_total,
                api_response_time_avg=baseline.api_response_time_avg,
                cache_hit_ratio=baseline.cache_hit_ratio,
                memory_usage_mb=memory_growth,
                cpu_usage_percent=baseline.cpu_usage_percent,
                error_rate=baseline.error_rate,
            )
            scenarios["memory_leak"].append(metrics)

        # Cache degradation (decreasing hit ratio)
        for i in range(10):
            hit_ratio_degradation = baseline.cache_hit_ratio * (
                1 - (i * 0.05)
            )  # 5% degradation per step
            metrics = MetricsFixture(
                timestamp=baseline.timestamp + (i * 3600),
                api_calls_total=baseline.api_calls_total,
                api_response_time_avg=baseline.api_response_time_avg,
                cache_hit_ratio=max(0.1, hit_ratio_degradation),  # Don't go below 10%
                memory_usage_mb=baseline.memory_usage_mb,
                cpu_usage_percent=baseline.cpu_usage_percent,
                error_rate=baseline.error_rate,
            )
            scenarios["cache_degradation"].append(metrics)

        return scenarios

    @classmethod
    def create_load_test_scenarios(cls) -> dict[str, dict[str, Any]]:
        """Create load test scenarios."""
        return {
            "light_load": {
                "concurrent_users": 10,
                "requests_per_second": 20,
                "duration_seconds": 300,
                "expected_response_time_ms": 100,
                "expected_error_rate": 0.01,
            },
            "medium_load": {
                "concurrent_users": 50,
                "requests_per_second": 100,
                "duration_seconds": 600,
                "expected_response_time_ms": 200,
                "expected_error_rate": 0.02,
            },
            "heavy_load": {
                "concurrent_users": 200,
                "requests_per_second": 500,
                "duration_seconds": 900,
                "expected_response_time_ms": 500,
                "expected_error_rate": 0.05,
            },
            "stress_test": {
                "concurrent_users": 1000,
                "requests_per_second": 2000,
                "duration_seconds": 300,
                "expected_response_time_ms": 2000,
                "expected_error_rate": 0.15,
            },
            "spike_test": {
                "concurrent_users": 500,
                "requests_per_second": 1000,
                "duration_seconds": 60,
                "expected_response_time_ms": 1000,
                "expected_error_rate": 0.10,
            },
        }

    @classmethod
    def create_performance_comparison(cls) -> dict[str, dict[str, Any]]:
        """Create performance comparison data."""
        return {
            "before_optimization": {
                "metrics": cls.create_baseline_metrics().to_dict(),
                "benchmark_results": {
                    "api_throughput": 25.0,
                    "cache_hit_ratio": 0.75,
                    "memory_efficiency": 0.70,
                    "error_rate": 0.05,
                },
            },
            "after_optimization": {
                "metrics": cls.create_optimized_metrics().to_dict(),
                "benchmark_results": {
                    "api_throughput": 50.0,
                    "cache_hit_ratio": 0.95,
                    "memory_efficiency": 0.90,
                    "error_rate": 0.001,
                },
            },
            "improvement": {
                "api_throughput_improvement": 100.0,  # 100% improvement
                "cache_hit_ratio_improvement": 26.7,  # 26.7% improvement
                "memory_efficiency_improvement": 28.6,  # 28.6% improvement
                "error_rate_improvement": 98.0,  # 98% improvement
            },
        }

    @classmethod
    def create_time_series_data(
        cls, duration_hours: int = 24, interval_minutes: int = 5
    ) -> list[MetricsFixture]:
        """Create time series performance data."""
        data_points = []
        start_time = time.time() - (duration_hours * 3600)
        interval_minutes * 60

        baseline = cls.create_baseline_metrics()

        for i in range(0, duration_hours * 60, interval_minutes):
            timestamp = start_time + (i * 60)

            # Add some realistic variance
            variance_factor = 1 + random.uniform(-0.2, 0.2)  # ±20% variance

            metrics = MetricsFixture(
                timestamp=timestamp,
                api_calls_total=baseline.api_calls_total + (i * 10),
                api_calls_per_second=baseline.api_calls_per_second * variance_factor,
                api_response_time_avg=baseline.api_response_time_avg * variance_factor,
                api_response_time_p95=baseline.api_response_time_p95 * variance_factor,
                api_response_time_p99=baseline.api_response_time_p99 * variance_factor,
                cache_hit_ratio=min(1.0, baseline.cache_hit_ratio * variance_factor),
                cache_hits_total=baseline.cache_hits_total + (i * 50),
                cache_misses_total=baseline.cache_misses_total + (i * 10),
                memory_usage_mb=baseline.memory_usage_mb * variance_factor,
                cpu_usage_percent=min(100.0, baseline.cpu_usage_percent * variance_factor),
                error_rate=max(0.0, baseline.error_rate * variance_factor),
            )

            data_points.append(metrics)

        return data_points
