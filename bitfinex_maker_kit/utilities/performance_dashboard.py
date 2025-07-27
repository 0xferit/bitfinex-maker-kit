"""
Performance dashboard utilities for Maker-Kit.

Provides real-time performance visualization and monitoring
dashboard for trading operations and system health.
"""

import asyncio
import contextlib
import logging
import time
from typing import Any

from ..services.performance_monitor import PerformanceMonitor
from ..utilities.profiler import PerformanceProfiler

logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """
    Real-time performance dashboard for trading operations.

    Provides console-based performance monitoring with live updates,
    alerts, and performance insights.
    """

    def __init__(
        self,
        performance_monitor: PerformanceMonitor,
        profiler: PerformanceProfiler | None = None,
        update_interval: float = 5.0,
    ):
        """
        Initialize performance dashboard.

        Args:
            performance_monitor: Performance monitor instance
            profiler: Optional performance profiler
            update_interval: Dashboard update interval in seconds
        """
        self.performance_monitor = performance_monitor
        self.profiler = profiler
        self.update_interval = update_interval
        self._running = False
        self._dashboard_task: asyncio.Task | None = None

        # Alert thresholds
        self.alert_thresholds = {
            "api_response_time_ms": 2000,  # 2 seconds
            "error_rate_pct": 5.0,
            "cache_hit_ratio": 0.8,
            "memory_usage_mb": 1000,
            "cpu_usage_pct": 80.0,
        }

        logger.info("Performance dashboard initialized")

    async def start(self) -> None:
        """Start the performance dashboard."""
        if self._running:
            return

        self._running = True
        self._dashboard_task = asyncio.create_task(self._dashboard_loop())

        logger.info("Performance dashboard started")

    async def stop(self) -> None:
        """Stop the performance dashboard."""
        self._running = False

        if self._dashboard_task:
            self._dashboard_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._dashboard_task
            self._dashboard_task = None

        logger.info("Performance dashboard stopped")

    async def _dashboard_loop(self) -> None:
        """Main dashboard update loop."""
        while self._running:
            try:
                self._display_dashboard()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dashboard loop: {e}")
                await asyncio.sleep(self.update_interval)

    def _display_dashboard(self) -> None:
        """Display the performance dashboard."""
        try:
            # Clear screen (works on most terminals)
            print("\033[2J\033[H", end="")

            # Get current metrics
            metrics = self.performance_monitor.get_current_metrics()
            summary = self.performance_monitor.get_performance_summary()

            # Header
            print("=" * 80)
            print("🚀 MAKER-KIT PERFORMANCE DASHBOARD")
            print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

            # API Performance
            print("\n📡 API PERFORMANCE")
            print("-" * 40)

            api_health = summary["overall_health"]["api"]
            health_emoji = self._get_health_emoji(api_health)

            print(f"Status: {health_emoji} {api_health.upper()}")
            print(f"Total Calls: {metrics.api_calls_total:,}")
            print(f"Calls/sec: {metrics.api_calls_per_second:.2f}")
            print(f"Avg Response: {metrics.api_response_time_avg * 1000:.1f}ms")
            print(f"P95 Response: {metrics.api_response_time_p95 * 1000:.1f}ms")
            print(f"P99 Response: {metrics.api_response_time_p99 * 1000:.1f}ms")
            print(f"Error Rate: {metrics.error_rate * 100:.2f}%")

            # Cache Performance
            print("\n💾 CACHE PERFORMANCE")
            print("-" * 40)

            cache_health = summary["overall_health"]["cache"]
            cache_emoji = self._get_health_emoji(cache_health)

            print(f"Status: {cache_emoji} {cache_health.upper()}")
            print(f"Hit Ratio: {metrics.cache_hit_ratio * 100:.1f}%")
            print(f"Total Hits: {metrics.cache_hits_total:,}")
            print(f"Total Misses: {metrics.cache_misses_total:,}")

            # Trading Activity
            print("\n📈 TRADING ACTIVITY")
            print("-" * 40)
            print(f"Orders Placed: {metrics.orders_placed_total:,}")
            print(f"Orders Cancelled: {metrics.orders_cancelled_total:,}")
            print(f"Orders Updated: {metrics.orders_updated_total:,}")

            # WebSocket Performance
            print("\n🔌 WEBSOCKET PERFORMANCE")
            print("-" * 40)
            print(f"Active Connections: {metrics.websocket_connections}")
            print(f"Messages Received: {metrics.websocket_messages_received:,}")
            print(f"Reconnections: {metrics.websocket_reconnections}")

            # System Resources
            print("\n🖥️  SYSTEM RESOURCES")
            print("-" * 40)

            system_health = summary["overall_health"]["system"]
            system_emoji = self._get_health_emoji(system_health)

            print(f"Status: {system_emoji} {system_health.upper()}")
            print(f"Memory Usage: {metrics.memory_usage_mb:.1f} MB")
            print(f"CPU Usage: {metrics.cpu_usage_percent:.1f}%")

            # Batch Performance
            if metrics.batch_requests_efficiency > 0:
                print("\n📦 BATCH PERFORMANCE")
                print("-" * 40)
                print(f"Efficiency: {metrics.batch_requests_efficiency * 100:.1f}%")

            # Alerts
            alerts = self._check_alerts(metrics)
            if alerts:
                print("\n🚨 ALERTS")
                print("-" * 40)
                for alert in alerts:
                    print(f"⚠️  {alert}")

            # Recommendations
            recommendations = summary.get("recommendations", [])
            if recommendations:
                print("\n💡 RECOMMENDATIONS")
                print("-" * 40)
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"{i}. {rec}")

            # Profiler data (if available)
            if self.profiler:
                self._display_profiler_summary()

            print("\n" + "=" * 80)
            print("Press Ctrl+C to stop dashboard")

        except Exception as e:
            logger.error(f"Error displaying dashboard: {e}")

    def _display_profiler_summary(self) -> None:
        """Display profiler summary section."""
        try:
            if self.profiler is not None:
                top_functions = self.profiler.get_top_slowest_functions(3)
            else:
                top_functions = []

            if top_functions:
                print("\n🔍 TOP SLOWEST FUNCTIONS")
                print("-" * 40)

                for i, func_data in enumerate(top_functions, 1):
                    print(f"{i}. {func_data['function_name']}")
                    print(
                        f"   Avg: {func_data['avg_time'] * 1000:.1f}ms, "
                        f"Max: {func_data['max_time'] * 1000:.1f}ms, "
                        f"Calls: {func_data['call_count']}"
                    )

        except Exception as e:
            logger.error(f"Error displaying profiler summary: {e}")

    def _get_health_emoji(self, health: str) -> str:
        """Get emoji for health status."""
        emoji_map = {
            "good": "✅",
            "fair": "⚠️",
            "poor": "🔴",
            "slow": "🐌",
            "errors": "❌",
            "high_usage": "📈",
        }
        return emoji_map.get(health, "❓")

    def _check_alerts(self, metrics: Any) -> list[str]:
        """Check for performance alerts."""
        alerts = []

        # API response time alert
        if metrics.api_response_time_avg * 1000 > self.alert_thresholds["api_response_time_ms"]:
            alerts.append(
                f"High API response time: {metrics.api_response_time_avg * 1000:.1f}ms "
                f"(threshold: {self.alert_thresholds['api_response_time_ms']}ms)"
            )

        # Error rate alert
        if metrics.error_rate * 100 > self.alert_thresholds["error_rate_pct"]:
            alerts.append(
                f"High error rate: {metrics.error_rate * 100:.2f}% "
                f"(threshold: {self.alert_thresholds['error_rate_pct']}%)"
            )

        # Cache hit ratio alert
        if metrics.cache_hit_ratio < self.alert_thresholds["cache_hit_ratio"]:
            alerts.append(
                f"Low cache hit ratio: {metrics.cache_hit_ratio * 100:.1f}% "
                f"(threshold: {self.alert_thresholds['cache_hit_ratio'] * 100:.1f}%)"
            )

        # Memory usage alert
        if metrics.memory_usage_mb > self.alert_thresholds["memory_usage_mb"]:
            alerts.append(
                f"High memory usage: {metrics.memory_usage_mb:.1f}MB "
                f"(threshold: {self.alert_thresholds['memory_usage_mb']}MB)"
            )

        # CPU usage alert
        if metrics.cpu_usage_percent > self.alert_thresholds["cpu_usage_pct"]:
            alerts.append(
                f"High CPU usage: {metrics.cpu_usage_percent:.1f}% "
                f"(threshold: {self.alert_thresholds['cpu_usage_pct']}%)"
            )

        return alerts

    def set_alert_threshold(self, metric: str, value: float) -> None:
        """
        Set alert threshold for a metric.

        Args:
            metric: Metric name
            value: Threshold value
        """
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = value
            logger.info(f"Alert threshold for {metric} set to {value}")
        else:
            logger.warning(f"Unknown metric for alert threshold: {metric}")

    def display_static_report(self) -> None:
        """Display a static performance report."""
        try:
            metrics = self.performance_monitor.get_current_metrics()
            summary = self.performance_monitor.get_performance_summary()

            print("\n" + "=" * 60)
            print("📊 PERFORMANCE REPORT")
            print("=" * 60)

            # Overall Health
            print("\n🏥 OVERALL HEALTH")
            for component, health in summary["overall_health"].items():
                emoji = self._get_health_emoji(health)
                print(f"  {component.title()}: {emoji} {health.upper()}")

            # Key Metrics
            print("\n📈 KEY METRICS")
            print(f"  API Calls/sec: {metrics.api_calls_per_second:.2f}")
            print(f"  Avg Response Time: {metrics.api_response_time_avg * 1000:.1f}ms")
            print(f"  Cache Hit Ratio: {metrics.cache_hit_ratio * 100:.1f}%")
            print(f"  Error Rate: {metrics.error_rate * 100:.2f}%")
            print(f"  Memory Usage: {metrics.memory_usage_mb:.1f}MB")
            print(f"  CPU Usage: {metrics.cpu_usage_percent:.1f}%")

            # Trading Activity
            print("\n💰 TRADING ACTIVITY")
            print(f"  Orders Placed: {metrics.orders_placed_total:,}")
            print(f"  Orders Cancelled: {metrics.orders_cancelled_total:,}")
            print(f"  Orders Updated: {metrics.orders_updated_total:,}")

            # Recommendations
            recommendations = summary.get("recommendations", [])
            if recommendations:
                print("\n💡 RECOMMENDATIONS")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")

            print("\n" + "=" * 60)

        except Exception as e:
            logger.error(f"Error displaying static report: {e}")


def create_performance_dashboard(
    performance_monitor: PerformanceMonitor,
    profiler: PerformanceProfiler | None = None,
    update_interval: float = 5.0,
) -> PerformanceDashboard:
    """
    Create performance dashboard with configuration.

    Args:
        performance_monitor: Performance monitor instance
        profiler: Optional performance profiler
        update_interval: Dashboard update interval

    Returns:
        Configured PerformanceDashboard instance
    """
    return PerformanceDashboard(performance_monitor, profiler, update_interval)
