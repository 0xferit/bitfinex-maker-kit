"""
Performance profiling utilities for Maker-Kit.

Provides code profiling, memory analysis, and performance
optimization tools for trading operations.
"""

import asyncio
import cProfile
import io
import logging
import pstats
import threading
import time
import tracemalloc
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import psutil

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class ProfileResult:
    """Results from profiling operation."""

    function_name: str
    duration: float
    calls_count: int
    memory_peak: int | None = None
    memory_current: int | None = None
    cpu_time: float | None = None
    profile_data: str | None = None


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""

    timestamp: float
    current_mb: float
    peak_mb: float
    tracemalloc_current: int | None = None
    tracemalloc_peak: int | None = None


class PerformanceProfiler:
    """
    Comprehensive performance profiler for trading operations.

    Provides profiling capabilities including execution time,
    memory usage, and CPU utilization analysis.
    """

    def __init__(self, enable_memory_tracking: bool = True):
        """
        Initialize performance profiler.

        Args:
            enable_memory_tracking: Whether to enable memory tracking
        """
        self.enable_memory_tracking = enable_memory_tracking
        self._profile_results: dict[str, list[ProfileResult]] = {}
        self._memory_snapshots: list[MemorySnapshot] = []
        self._process = psutil.Process()
        self._lock = threading.Lock()

        if enable_memory_tracking:
            try:
                tracemalloc.start()
                logger.info("Memory tracking enabled")
            except Exception as e:
                logger.warning(f"Could not enable memory tracking: {e}")

        logger.info("Performance profiler initialized")

    def profile_function(
        self, func_name: str | None = None, memory_tracking: bool = True
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Decorator for profiling function performance.

        Args:
            func_name: Optional custom function name
            memory_tracking: Whether to track memory usage

        Returns:
            Decorated function
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            name = func_name or f"{func.__module__}.{func.__name__}"

            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    with self.profile_context(name, memory_tracking):
                        result = await func(*args, **kwargs)
                        return result  # type: ignore[no-any-return]

                return async_wrapper  # type: ignore[return-value]
            else:

                @wraps(func)
                def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    with self.profile_context(name, memory_tracking):
                        return func(*args, **kwargs)

                return sync_wrapper  # type: ignore[return-value]

        return decorator

    @contextmanager
    def profile_context(
        self, operation_name: str, memory_tracking: bool = True
    ) -> Generator[None, None, None]:
        """
        Context manager for profiling code blocks.

        Args:
            operation_name: Name of the operation being profiled
            memory_tracking: Whether to track memory usage
        """
        # Start profiling
        profiler = cProfile.Profile()
        profiler.enable()

        # Memory tracking

        if memory_tracking and self.enable_memory_tracking:
            with suppress(Exception):
                tracemalloc.get_traced_memory()

        start_time = time.time()

        try:
            yield
        finally:
            # Stop profiling
            end_time = time.time()
            profiler.disable()

            duration = end_time - start_time

            # Memory tracking
            tracemalloc_current = None
            tracemalloc_peak = None

            if memory_tracking and self.enable_memory_tracking:
                with suppress(Exception):
                    tracemalloc_current, tracemalloc_peak = tracemalloc.get_traced_memory()

            # Generate profile data
            profile_data = self._format_profile_data(profiler)

            # Count function calls
            stats = pstats.Stats(profiler)
            calls_count = sum(stats.stats[key][0] for key in stats.stats)  # type: ignore[attr-defined]

            # Store result
            result = ProfileResult(
                function_name=operation_name,
                duration=duration,
                calls_count=calls_count,
                memory_peak=tracemalloc_peak,
                memory_current=tracemalloc_current,
                profile_data=profile_data,
            )

            with self._lock:
                if operation_name not in self._profile_results:
                    self._profile_results[operation_name] = []
                self._profile_results[operation_name].append(result)

            logger.debug(f"Profiled {operation_name}: {duration:.3f}s, {calls_count} calls")

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self._process.memory_info()
            return float(memory_info.rss / 1024 / 1024)
        except Exception:
            return 0.0

    def _format_profile_data(self, profiler: cProfile.Profile) -> str:
        """Format profile data as string."""
        try:
            s = io.StringIO()
            stats = pstats.Stats(profiler, stream=s)
            stats.sort_stats("cumulative")
            stats.print_stats(20)  # Top 20 functions
            return s.getvalue()
        except Exception as e:
            logger.error(f"Error formatting profile data: {e}")
            return ""

    def take_memory_snapshot(self) -> MemorySnapshot:
        """
        Take memory usage snapshot.

        Returns:
            Memory snapshot data
        """
        current_mb = self._get_memory_usage()
        peak_mb = current_mb  # Simple approximation

        tracemalloc_current = None
        tracemalloc_peak = None

        if self.enable_memory_tracking:
            with suppress(Exception):
                tracemalloc_current, tracemalloc_peak = tracemalloc.get_traced_memory()

        snapshot = MemorySnapshot(
            timestamp=time.time(),
            current_mb=current_mb,
            peak_mb=peak_mb,
            tracemalloc_current=tracemalloc_current,
            tracemalloc_peak=tracemalloc_peak,
        )

        with self._lock:
            self._memory_snapshots.append(snapshot)

            # Keep only recent snapshots (last hour)
            cutoff_time = time.time() - 3600
            self._memory_snapshots = [
                s for s in self._memory_snapshots if s.timestamp >= cutoff_time
            ]

        return snapshot

    def get_function_profile(self, function_name: str) -> list[ProfileResult]:
        """
        Get profiling results for a function.

        Args:
            function_name: Name of the function

        Returns:
            List of profile results
        """
        with self._lock:
            return self._profile_results.get(function_name, []).copy()

    def get_top_slowest_functions(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top slowest functions by average execution time.

        Args:
            limit: Number of functions to return

        Returns:
            List of function performance data
        """
        function_stats = []

        with self._lock:
            for func_name, results in self._profile_results.items():
                if not results:
                    continue

                total_time = sum(r.duration for r in results)
                avg_time = total_time / len(results)
                max_time = max(r.duration for r in results)
                total_calls = sum(r.calls_count for r in results)

                function_stats.append(
                    {
                        "function_name": func_name,
                        "total_time": total_time,
                        "avg_time": avg_time,
                        "max_time": max_time,
                        "call_count": len(results),
                        "total_function_calls": total_calls,
                    }
                )

        # Sort by average time
        function_stats.sort(key=lambda x: x["avg_time"], reverse=True)
        return function_stats[:limit]

    def get_memory_usage_trend(self, duration: float = 3600.0) -> list[MemorySnapshot]:
        """
        Get memory usage trend over specified duration.

        Args:
            duration: Duration in seconds

        Returns:
            List of memory snapshots
        """
        cutoff_time = time.time() - duration

        with self._lock:
            return [
                snapshot for snapshot in self._memory_snapshots if snapshot.timestamp >= cutoff_time
            ]

    def generate_performance_report(self) -> dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Performance report dictionary
        """
        report = {
            "timestamp": time.time(),
            "summary": {},
            "top_slowest_functions": self.get_top_slowest_functions(),
            "memory_usage": {},
            "recommendations": [],
        }

        # Summary statistics
        with self._lock:
            total_functions = len(self._profile_results)
            total_executions = sum(len(results) for results in self._profile_results.values())

            if total_executions > 0:
                all_durations = [
                    r.duration for results in self._profile_results.values() for r in results
                ]

                report["summary"] = {
                    "total_functions_profiled": total_functions,
                    "total_executions": total_executions,
                    "avg_execution_time": sum(all_durations) / len(all_durations),
                    "max_execution_time": max(all_durations),
                    "min_execution_time": min(all_durations),
                }

        # Memory usage
        recent_snapshots = self.get_memory_usage_trend(300)  # Last 5 minutes
        if recent_snapshots:
            current_memory = recent_snapshots[-1].current_mb
            avg_memory = sum(s.current_mb for s in recent_snapshots) / len(recent_snapshots)
            max_memory = max(s.current_mb for s in recent_snapshots)

            report["memory_usage"] = {
                "current_mb": current_memory,
                "average_mb": avg_memory,
                "peak_mb": max_memory,
                "snapshots_count": len(recent_snapshots),
            }

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: dict[str, Any]) -> list[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        # Check slow functions
        if report.get("top_slowest_functions"):
            slowest = report["top_slowest_functions"][0]
            if slowest["avg_time"] > 1.0:
                recommendations.append(
                    f"Function '{slowest['function_name']}' has high average "
                    f"execution time ({slowest['avg_time']:.3f}s) - consider optimization"
                )

        # Check memory usage
        memory_usage = report.get("memory_usage", {})
        current_memory = memory_usage.get("current_mb", 0)
        if current_memory > 500:
            recommendations.append(
                f"High memory usage detected ({current_memory:.1f}MB) - "
                "consider memory optimization"
            )

        # Check function call counts
        if report.get("top_slowest_functions"):
            for func_data in report["top_slowest_functions"][:3]:
                if func_data["total_function_calls"] > 10000:
                    recommendations.append(
                        f"Function '{func_data['function_name']}' has high call count "
                        f"({func_data['total_function_calls']}) - consider caching or optimization"
                    )

        return recommendations

    def clear_profile_data(self) -> None:
        """Clear all profiling data."""
        with self._lock:
            self._profile_results.clear()
            self._memory_snapshots.clear()

        logger.info("Profile data cleared")

    def export_profile_data(self, output_file: str) -> None:
        """
        Export profile data to file.

        Args:
            output_file: Output file path
        """
        try:
            report = self.generate_performance_report()

            import json

            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Profile data exported to {output_file}")

        except Exception as e:
            logger.error(f"Error exporting profile data: {e}")


# Global profiler instance
_global_profiler: PerformanceProfiler | None = None


def get_profiler() -> PerformanceProfiler:
    """Get or create global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile(
    func_name: str | None = None, memory_tracking: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Convenience decorator for profiling functions.

    Args:
        func_name: Optional custom function name
        memory_tracking: Whether to track memory usage
    """
    profiler = get_profiler()
    return profiler.profile_function(func_name, memory_tracking)


@contextmanager
def profile_block(operation_name: str, memory_tracking: bool = True) -> Generator[None, None, None]:
    """
    Convenience context manager for profiling code blocks.

    Args:
        operation_name: Name of the operation
        memory_tracking: Whether to track memory usage
    """
    profiler = get_profiler()
    with profiler.profile_context(operation_name, memory_tracking):
        yield


def create_profiler(enable_memory_tracking: bool = True) -> PerformanceProfiler:
    """
    Create performance profiler with configuration.

    Args:
        enable_memory_tracking: Whether to enable memory tracking

    Returns:
        Configured PerformanceProfiler instance
    """
    return PerformanceProfiler(enable_memory_tracking)
