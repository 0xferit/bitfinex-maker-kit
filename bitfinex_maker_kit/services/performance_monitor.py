"""
Performance monitoring and metrics service for Maker-Kit.

Provides comprehensive performance tracking, metrics collection,
and monitoring capabilities for trading operations.
"""

import asyncio
import contextlib
import json
import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

import psutil

logger = logging.getLogger(__name__)

T = TypeVar("T")


class MetricType(Enum):
    """Types of performance metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    api_calls_total: int = 0
    api_calls_per_second: float = 0.0
    api_response_time_avg: float = 0.0
    api_response_time_p95: float = 0.0
    api_response_time_p99: float = 0.0

    cache_hit_ratio: float = 0.0
    cache_hits_total: int = 0
    cache_misses_total: int = 0

    orders_placed_total: int = 0
    orders_cancelled_total: int = 0
    orders_updated_total: int = 0

    websocket_connections: int = 0
    websocket_messages_received: int = 0
    websocket_reconnections: int = 0

    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    batch_requests_efficiency: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
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
            "trading_activity": {
                "orders_placed": self.orders_placed_total,
                "orders_cancelled": self.orders_cancelled_total,
                "orders_updated": self.orders_updated_total,
            },
            "websocket_performance": {
                "active_connections": self.websocket_connections,
                "messages_received": self.websocket_messages_received,
                "reconnections": self.websocket_reconnections,
            },
            "system_resources": {
                "memory_usage_mb": self.memory_usage_mb,
                "cpu_usage_pct": self.cpu_usage_percent,
            },
            "batch_performance": {"efficiency_pct": self.batch_requests_efficiency * 100},
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring service.

    Tracks API performance, cache efficiency, trading activity,
    system resources, and provides real-time metrics.
    """

    def __init__(self, monitoring_interval: float = 5.0, retention_period: float = 3600.0):
        """
        Initialize performance monitor.

        Args:
            monitoring_interval: Interval between metric collections
            retention_period: How long to retain metric history
        """
        self.monitoring_interval = monitoring_interval
        self.retention_period = retention_period

        # Metric storage
        self._metrics: dict[str, deque] = defaultdict(lambda: deque())
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = defaultdict(float)
        self._timers: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Performance tracking
        self._api_call_times: deque = deque(maxlen=10000)
        self._api_call_timestamps: deque = deque(maxlen=1000)
        self._error_count = 0
        self._total_requests = 0

        # System monitoring
        self._process = psutil.Process()
        self._monitoring_task: asyncio.Task | None = None
        self._shutdown = False

        # Event callbacks
        self._event_callbacks: dict[str, list[Callable]] = defaultdict(list)

        # Thread safety
        self._lock = threading.Lock()

        logger.info("Performance monitor initialized")

    def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if self._monitoring_task is not None:
            return

        try:
            # Only start monitoring if there's a running event loop
            loop = asyncio.get_running_loop()
            self._monitoring_task = loop.create_task(self._monitoring_loop())
            logger.info("Performance monitoring started")
        except RuntimeError:
            # No running event loop - defer monitoring start
            logger.debug("No running event loop - performance monitoring will be started later")
            pass

    async def ensure_monitoring_started(self) -> None:
        """Ensure monitoring is started in an async context."""
        if self._monitoring_task is None and not self._shutdown:
            try:
                loop = asyncio.get_running_loop()
                self._monitoring_task = loop.create_task(self._monitoring_loop())
                logger.info("Performance monitoring started in async context")
            except RuntimeError:
                logger.warning("Could not start performance monitoring - no event loop")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._shutdown = True

        if self._monitoring_task:
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task
            self._monitoring_task = None

        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics."""
        try:
            # Memory usage
            memory_info = self._process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self.record_gauge("system.memory_usage_mb", memory_mb)

            # CPU usage
            cpu_percent = self._process.cpu_percent()
            self.record_gauge("system.cpu_usage_pct", cpu_percent)

            # Clean up old metrics
            self._cleanup_old_metrics()

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def _cleanup_old_metrics(self) -> None:
        """Clean up metrics older than retention period."""
        cutoff_time = time.time() - self.retention_period

        with self._lock:
            for _metric_name, points in self._metrics.items():
                while points and points[0].timestamp < cutoff_time:
                    points.popleft()

    def record_counter(
        self, name: str, value: int = 1, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record counter metric.

        Args:
            name: Metric name
            value: Counter increment
            labels: Optional metric labels
        """
        with self._lock:
            self._counters[name] += value

            point = MetricPoint(timestamp=time.time(), value=value, labels=labels or {})
            self._metrics[name].append(point)

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """
        Record gauge metric.

        Args:
            name: Metric name
            value: Current gauge value
            labels: Optional metric labels
        """
        with self._lock:
            self._gauges[name] = value

            point = MetricPoint(timestamp=time.time(), value=value, labels=labels or {})
            self._metrics[name].append(point)

    def record_timer(
        self, name: str, duration: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        Record timer metric.

        Args:
            name: Metric name
            duration: Duration in seconds
            labels: Optional metric labels
        """
        with self._lock:
            self._timers[name].append(duration)

            point = MetricPoint(timestamp=time.time(), value=duration, labels=labels or {})
            self._metrics[name].append(point)

    def time_operation(
        self, operation_name: str, labels: dict[str, str] | None = None
    ) -> "TimingContext":
        """
        Context manager for timing operations.

        Args:
            operation_name: Name of the operation
            labels: Optional metric labels

        Returns:
            Context manager for timing
        """
        return TimingContext(self, operation_name, labels)

    def track_api_call(
        self, method: str, endpoint: str, response_time: float, success: bool = True
    ) -> None:
        """
        Track API call performance.

        Args:
            method: HTTP method
            endpoint: API endpoint
            response_time: Response time in seconds
            success: Whether the call was successful
        """
        with self._lock:
            self._total_requests += 1

            if not success:
                self._error_count += 1

            self._api_call_times.append(response_time)
            self._api_call_timestamps.append(time.time())

        # Record metrics
        self.record_timer(
            "api.response_time",
            response_time,
            {"method": method, "endpoint": endpoint, "success": str(success)},
        )

        self.record_counter("api.calls_total", 1, {"method": method, "endpoint": endpoint})

        if not success:
            self.record_counter("api.errors_total", 1, {"method": method, "endpoint": endpoint})

    def track_cache_operation(self, operation: str, hit: bool) -> None:
        """
        Track cache operation.

        Args:
            operation: Cache operation type
            hit: Whether it was a cache hit
        """
        self.record_counter(
            "cache.operations_total",
            1,
            {"operation": operation, "result": "hit" if hit else "miss"},
        )

    def track_trading_operation(self, operation: str, symbol: str, success: bool = True) -> None:
        """
        Track trading operation.

        Args:
            operation: Trading operation type
            symbol: Trading symbol
            success: Whether operation was successful
        """
        self.record_counter(
            "trading.operations_total",
            1,
            {"operation": operation, "symbol": symbol, "success": str(success)},
        )

    def track_websocket_event(self, event_type: str, connection_id: str) -> None:
        """
        Track WebSocket event.

        Args:
            event_type: Type of WebSocket event
            connection_id: Connection identifier
        """
        self.record_counter(
            "websocket.events_total", 1, {"event_type": event_type, "connection_id": connection_id}
        )

    def register_event_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for metric events.

        Args:
            event_type: Type of event to monitor
            callback: Callback function
        """
        self._event_callbacks[event_type].append(callback)
        logger.info(f"Registered callback for event type: {event_type}")

    def get_current_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics.

        Returns:
            Current performance metrics
        """
        with self._lock:
            metrics = PerformanceMetrics()

            # API performance
            metrics.api_calls_total = self._counters.get("api.calls_total", 0)

            if self._api_call_times:
                metrics.api_response_time_avg = statistics.mean(self._api_call_times)

                if len(self._api_call_times) > 1:
                    sorted_times = sorted(self._api_call_times)
                    metrics.api_response_time_p95 = sorted_times[int(len(sorted_times) * 0.95)]
                    metrics.api_response_time_p99 = sorted_times[int(len(sorted_times) * 0.99)]

            # Calculate API calls per second
            current_time = time.time()
            recent_calls = [
                ts for ts in self._api_call_timestamps if current_time - ts <= 60
            ]  # Last minute
            metrics.api_calls_per_second = len(recent_calls) / 60.0

            # Error rate
            if self._total_requests > 0:
                metrics.error_rate = self._error_count / self._total_requests

            # Cache performance
            cache_hits = self._counters.get("cache.operations_total", 0)
            cache_misses = self._counters.get("cache.operations_total", 0)

            if cache_hits + cache_misses > 0:
                metrics.cache_hit_ratio = cache_hits / (cache_hits + cache_misses)

            metrics.cache_hits_total = cache_hits
            metrics.cache_misses_total = cache_misses

            # Trading activity
            metrics.orders_placed_total = self._counters.get("trading.operations_total", 0)
            metrics.orders_cancelled_total = self._counters.get("trading.operations_total", 0)
            metrics.orders_updated_total = self._counters.get("trading.operations_total", 0)

            # WebSocket performance
            metrics.websocket_messages_received = self._counters.get("websocket.events_total", 0)

            # System resources
            metrics.memory_usage_mb = self._gauges.get("system.memory_usage_mb", 0.0)
            metrics.cpu_usage_percent = self._gauges.get("system.cpu_usage_pct", 0.0)

            return metrics

    def get_metric_history(self, metric_name: str, duration: float = 300.0) -> list[MetricPoint]:
        """
        Get metric history for specified duration.

        Args:
            metric_name: Name of metric
            duration: Duration in seconds

        Returns:
            List of metric points
        """
        cutoff_time = time.time() - duration

        with self._lock:
            points = self._metrics.get(metric_name, deque())
            return [point for point in points if point.timestamp >= cutoff_time]

    def export_metrics_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus format metrics string
        """
        lines = []
        current_time = int(time.time() * 1000)

        with self._lock:
            # Export counters
            for name, value in self._counters.items():
                prometheus_name: str = name.replace(".", "_")
                lines.append(f"# TYPE {prometheus_name} counter")
                lines.append(f"{prometheus_name} {value} {current_time}")

            # Export gauges
            for gauge_name, gauge_value in self._gauges.items():
                gauge_prometheus_name: str = gauge_name.replace(".", "_")
                lines.append(f"# TYPE {gauge_prometheus_name} gauge")
                lines.append(f"{gauge_prometheus_name} {gauge_value} {current_time}")

        return "\n".join(lines)

    def export_metrics_json(self) -> str:
        """
        Export metrics in JSON format.

        Returns:
            JSON format metrics string
        """
        metrics = self.get_current_metrics()
        return json.dumps(metrics.to_dict(), indent=2)

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get performance summary with key insights.

        Returns:
            Performance summary dictionary
        """
        metrics = self.get_current_metrics()

        # Calculate performance insights
        api_health = "good"
        if metrics.api_response_time_avg > 1.0:
            api_health = "slow"
        elif metrics.error_rate > 0.05:
            api_health = "errors"

        cache_health = "good"
        if metrics.cache_hit_ratio < 0.5:
            cache_health = "poor"
        elif metrics.cache_hit_ratio < 0.8:
            cache_health = "fair"

        system_health = "good"
        if metrics.memory_usage_mb > 1000 or metrics.cpu_usage_percent > 80:
            system_health = "high_usage"

        return {
            "timestamp": time.time(),
            "overall_health": {"api": api_health, "cache": cache_health, "system": system_health},
            "key_metrics": metrics.to_dict(),
            "recommendations": self._get_performance_recommendations(metrics),
        }

    def _get_performance_recommendations(self, metrics: PerformanceMetrics) -> list[str]:
        """Get performance improvement recommendations."""
        recommendations = []

        if metrics.api_response_time_avg > 1.0:
            recommendations.append("Consider implementing request batching to reduce API latency")

        if metrics.cache_hit_ratio < 0.8:
            recommendations.append("Cache hit ratio is low - consider tuning cache TTL settings")

        if metrics.error_rate > 0.02:
            recommendations.append("Error rate is elevated - review API error handling")

        if metrics.memory_usage_mb > 500:
            recommendations.append("Memory usage is high - consider optimizing data structures")

        if metrics.cpu_usage_percent > 70:
            recommendations.append("CPU usage is high - review computational efficiency")

        return recommendations


class TimingContext:
    """Context manager for operation timing."""

    def __init__(
        self,
        monitor: PerformanceMonitor,
        operation_name: str,
        labels: dict[str, str] | None = None,
    ):
        self.monitor = monitor
        self.operation_name = operation_name
        self.labels = labels
        self.start_time: float | None = None

    def __enter__(self) -> "TimingContext":
        self.start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if self.start_time:
            duration = time.time() - self.start_time
            self.monitor.record_timer(self.operation_name, duration, self.labels)


def create_performance_monitor(
    monitoring_interval: float = 5.0, retention_period: float = 3600.0
) -> PerformanceMonitor:
    """
    Create performance monitor with configuration.

    Args:
        monitoring_interval: Interval between metric collections
        retention_period: How long to retain metric history

    Returns:
        Configured PerformanceMonitor instance
    """
    return PerformanceMonitor(monitoring_interval, retention_period)
