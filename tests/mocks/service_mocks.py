"""
Service mock utilities for testing.

Provides comprehensive mocking for internal services including
trading services, cache services, and monitoring components.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

from ..fixtures.performance_data import MetricsFixture, PerformanceFixtures
from ..fixtures.trading_data import OrderFixture, TradingFixtures


class MockTradingService:
    """
    Mock trading service for testing.

    Provides realistic trading operations without actual API calls,
    allowing for comprehensive testing of trading logic.
    """

    def __init__(
        self, initial_balance: dict[str, float] | None = None, order_execution_delay: float = 0.0
    ):
        """
        Initialize mock trading service.

        Args:
            initial_balance: Initial account balances
            order_execution_delay: Simulated order execution delay
        """
        self.initial_balance = initial_balance or {"USD": 10000.0, "BTC": 1.0}
        self.order_execution_delay = order_execution_delay

        # Service state
        self.balances = self.initial_balance.copy()
        self.orders = {}  # order_id -> OrderFixture
        self.order_counter = 10000000

        # Operation tracking
        self.operations = []
        self.call_count = 0

        # Mock responses
        self.fixtures = TradingFixtures()

    def _record_operation(self, operation: str, **kwargs):
        """Record operation for tracking."""
        self.call_count += 1
        self.operations.append(
            {
                "operation": operation,
                "timestamp": time.time(),
                "call_number": self.call_count,
                "kwargs": kwargs,
            }
        )

    async def _simulate_delay(self):
        """Simulate operation delay."""
        if self.order_execution_delay > 0:
            await asyncio.sleep(self.order_execution_delay)

    def get_client(self):
        """Get mock client."""
        return Mock()

    async def place_order(
        self, symbol, amount, price, side, order_type: str = "EXCHANGE LIMIT", **kwargs
    ) -> dict[str, Any]:
        """Mock place order operation."""
        self._record_operation(
            "place_order", symbol=str(symbol), amount=str(amount), price=str(price), side=side
        )
        await self._simulate_delay()

        # Create order
        order_id = self.order_counter
        self.order_counter += 1

        order = self.fixtures.create_order(
            order_id=order_id,
            symbol=str(symbol),
            amount=str(amount),
            price=str(price),
            side=side,
            order_type=order_type,
        )

        self.orders[order_id] = order
        return order.to_dict()

    async def cancel_order(self, order_id: str, symbol=None) -> dict[str, Any]:
        """Mock cancel order operation."""
        self._record_operation(
            "cancel_order", order_id=order_id, symbol=str(symbol) if symbol else None
        )
        await self._simulate_delay()

        order_id_int = int(order_id)

        if order_id_int in self.orders:
            order = self.orders[order_id_int]
            canceled_order = order.mark_canceled()
            self.orders[order_id_int] = canceled_order
            return canceled_order.to_dict()
        else:
            raise Exception(f"Order {order_id} not found")

    async def update_order(
        self, order_id: str, new_amount=None, new_price=None, symbol=None
    ) -> dict[str, Any]:
        """Mock update order operation."""
        self._record_operation(
            "update_order",
            order_id=order_id,
            new_amount=str(new_amount) if new_amount else None,
            new_price=str(new_price) if new_price else None,
        )
        await self._simulate_delay()

        order_id_int = int(order_id)

        if order_id_int in self.orders:
            order = self.orders[order_id_int]

            # Update order fields
            updated_order = OrderFixture(
                id=order.id,
                symbol=order.symbol,
                amount=str(new_amount) if new_amount else order.amount,
                price=str(new_price) if new_price else order.price,
                side=order.side,
                order_type=order.order_type,
                status=order.status,
                timestamp=order.timestamp,
                flags=order.flags,
            )

            self.orders[order_id_int] = updated_order
            return updated_order.to_dict()
        else:
            raise Exception(f"Order {order_id} not found")

    async def get_active_orders(self, symbol=None) -> list[dict[str, Any]]:
        """Mock get active orders operation."""
        self._record_operation("get_active_orders", symbol=str(symbol) if symbol else None)
        await self._simulate_delay()

        active_orders = []
        for order in self.orders.values():
            if order.status == "ACTIVE":
                if symbol is None or order.symbol == str(symbol):
                    active_orders.append(order.to_dict())

        return active_orders

    async def get_order_status(self, order_id: str, symbol=None) -> dict[str, Any]:
        """Mock get order status operation."""
        self._record_operation("get_order_status", order_id=order_id)
        await self._simulate_delay()

        order_id_int = int(order_id)

        if order_id_int in self.orders:
            return self.orders[order_id_int].to_dict()
        else:
            raise Exception(f"Order {order_id} not found")

    async def cancel_all_orders(self, symbol=None) -> list[dict[str, Any]]:
        """Mock cancel all orders operation."""
        self._record_operation("cancel_all_orders", symbol=str(symbol) if symbol else None)
        await self._simulate_delay()

        canceled_orders = []

        for order_id, order in self.orders.items():
            if order.status == "ACTIVE":
                if symbol is None or order.symbol == str(symbol):
                    canceled_order = order.mark_canceled()
                    self.orders[order_id] = canceled_order
                    canceled_orders.append(canceled_order.to_dict())

        return canceled_orders

    async def get_account_balance(self) -> list[dict[str, Any]]:
        """Mock get account balance operation."""
        self._record_operation("get_account_balance")
        await self._simulate_delay()

        balances = []
        for currency, balance in self.balances.items():
            balances.append(
                {
                    "currency": currency,
                    "type": "exchange",
                    "balance": balance,
                    "available": balance * 0.95,  # 95% available
                }
            )

        return balances

    async def place_batch_orders(self, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Mock place batch orders operation."""
        self._record_operation("place_batch_orders", order_count=len(orders))
        await self._simulate_delay()

        results = []

        for order_spec in orders:
            try:
                result = await self.place_order(
                    symbol=order_spec["symbol"],
                    amount=order_spec["amount"],
                    price=order_spec["price"],
                    side=order_spec["side"],
                    order_type=order_spec.get("type", "EXCHANGE LIMIT"),
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        return results

    def simulate_order_execution(self, order_id: int, execution_price: str | None = None):
        """Simulate order execution."""
        if order_id in self.orders:
            order = self.orders[order_id]
            executed_order = order.mark_executed(execution_price)
            self.orders[order_id] = executed_order

    def simulate_partial_fill(self, order_id: int, filled_amount: str, execution_price: str):
        """Simulate partial order fill."""
        if order_id in self.orders:
            order = self.orders[order_id]
            partially_filled_order = order.mark_partially_filled(filled_amount, execution_price)
            self.orders[order_id] = partially_filled_order

    def get_operation_stats(self) -> dict[str, Any]:
        """Get operation statistics."""
        operation_counts = {}
        for op in self.operations:
            operation = op["operation"]
            operation_counts[operation] = operation_counts.get(operation, 0) + 1

        return {
            "total_operations": self.call_count,
            "operation_counts": operation_counts,
            "order_count": len(self.orders),
            "active_orders": len([o for o in self.orders.values() if o.status == "ACTIVE"]),
        }


class MockCacheService:
    """
    Mock cache service for testing.

    Provides in-memory caching behavior without external dependencies,
    allowing for cache-related testing scenarios.
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 30.0):
        """
        Initialize mock cache service.

        Args:
            max_size: Maximum cache size
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Cache storage
        self.cache = {}  # namespace:key -> {'value': value, 'expires': timestamp}

        # Statistics
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0

        # Operation tracking
        self.operations = []

    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        return f"{namespace}:{key}"

    def _is_expired(self, cache_entry: dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() > cache_entry["expires"]

    def _record_operation(self, operation: str, **kwargs):
        """Record cache operation."""
        self.operations.append({"operation": operation, "timestamp": time.time(), "kwargs": kwargs})

    async def get(self, namespace: str, key: str) -> Any:
        """Get value from cache."""
        cache_key = self._make_key(namespace, key)
        self._record_operation("get", namespace=namespace, key=key)

        if cache_key in self.cache:
            entry = self.cache[cache_key]

            if self._is_expired(entry):
                del self.cache[cache_key]
                self.misses += 1
                return None

            self.hits += 1
            return entry["value"]

        self.misses += 1
        return None

    async def set(self, namespace: str, key: str, value: Any, ttl: float | None = None) -> None:
        """Set value in cache."""
        cache_key = self._make_key(namespace, key)
        cache_ttl = ttl if ttl is not None else self.default_ttl
        expires = time.time() + cache_ttl

        self._record_operation("set", namespace=namespace, key=key, ttl=cache_ttl)

        # Evict if at capacity
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            self._evict_lru()

        self.cache[cache_key] = {"value": value, "expires": expires, "accessed": time.time()}

        self.sets += 1

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(namespace, key)
        self._record_operation("delete", namespace=namespace, key=key)

        if cache_key in self.cache:
            del self.cache[cache_key]
            self.deletes += 1
            return True

        return False

    async def get_or_set(
        self, namespace: str, key: str, fetch_func: Callable, ttl: float | None = None
    ) -> Any:
        """Get value from cache or fetch and cache if not found."""
        value = await self.get(namespace, key)

        if value is not None:
            return value

        # Fetch value
        if asyncio.iscoroutinefunction(fetch_func):
            value = await fetch_func()
        else:
            value = fetch_func()

        await self.set(namespace, key, value, ttl)
        return value

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return

        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k]["accessed"])

        del self.cache[lru_key]
        self.evictions += 1

    async def cleanup(self):
        """Clean up cache service."""
        self.cache.clear()
        self._record_operation("cleanup")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_ratio = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "hit_ratio": hit_ratio,
            "size": len(self.cache),
            "max_size": self.max_size,
        }


class MockPerformanceMonitor:
    """
    Mock performance monitor for testing.

    Provides performance monitoring behavior without actual system
    monitoring, allowing for performance-related testing.
    """

    def __init__(self, monitoring_interval: float = 5.0):
        """
        Initialize mock performance monitor.

        Args:
            monitoring_interval: Monitoring interval in seconds
        """
        self.monitoring_interval = monitoring_interval
        self.running = False

        # Mock metrics
        self.fixtures = PerformanceFixtures()
        self.current_metrics = self.fixtures.create_baseline_metrics()

        # Operation tracking
        self.recorded_operations = []
        self.recorded_timers = []
        self.recorded_counters = {}
        self.recorded_gauges = {}

    def start_monitoring(self):
        """Start performance monitoring."""
        self.running = True

    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.running = False

    def record_counter(self, name: str, value: int = 1, labels=None):
        """Record counter metric."""
        if name not in self.recorded_counters:
            self.recorded_counters[name] = 0
        self.recorded_counters[name] += value

    def record_gauge(self, name: str, value: float, labels=None):
        """Record gauge metric."""
        self.recorded_gauges[name] = value

    def record_timer(self, name: str, duration: float, labels=None):
        """Record timer metric."""
        self.recorded_timers.append(
            {"name": name, "duration": duration, "timestamp": time.time(), "labels": labels}
        )

    def time_operation(self, operation_name: str, labels=None):
        """Context manager for timing operations."""
        return MockTimingContext(self, operation_name, labels)

    def track_api_call(
        self, method: str, endpoint: str, response_time: float, success: bool = True
    ):
        """Track API call performance."""
        self.record_timer(f"api.{method}.{endpoint}", response_time)
        self.record_counter("api.calls_total")

        if not success:
            self.record_counter("api.errors_total")

    def track_cache_operation(self, operation: str, hit: bool):
        """Track cache operation."""
        self.record_counter(f"cache.{operation}_total")

        if hit:
            self.record_counter("cache.hits_total")
        else:
            self.record_counter("cache.misses_total")

    def track_trading_operation(self, operation: str, symbol: str, success: bool = True):
        """Track trading operation."""
        self.record_counter(f"trading.{operation}_total")

        if not success:
            self.record_counter("trading.errors_total")

    def get_current_metrics(self) -> MetricsFixture:
        """Get current performance metrics."""
        # Update metrics based on recorded data
        self.current_metrics.api_calls_total = self.recorded_counters.get("api.calls_total", 0)
        self.current_metrics.cache_hits_total = self.recorded_counters.get("cache.hits_total", 0)
        self.current_metrics.cache_misses_total = self.recorded_counters.get(
            "cache.misses_total", 0
        )

        # Calculate cache hit ratio
        total_cache_ops = (
            self.current_metrics.cache_hits_total + self.current_metrics.cache_misses_total
        )
        if total_cache_ops > 0:
            self.current_metrics.cache_hit_ratio = (
                self.current_metrics.cache_hits_total / total_cache_ops
            )

        return self.current_metrics

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary."""
        metrics = self.get_current_metrics()

        return {
            "timestamp": time.time(),
            "overall_health": {"api": "good", "cache": "good", "system": "good"},
            "key_metrics": metrics.to_dict(),
            "recommendations": [],
        }

    def set_scenario(self, scenario: str):
        """Set performance scenario."""
        if scenario == "baseline":
            self.current_metrics = self.fixtures.create_baseline_metrics()
        elif scenario == "high_load":
            self.current_metrics = self.fixtures.create_high_load_metrics()
        elif scenario == "stressed":
            self.current_metrics = self.fixtures.create_stressed_metrics()
        elif scenario == "optimized":
            self.current_metrics = self.fixtures.create_optimized_metrics()


class MockTimingContext:
    """Mock timing context manager."""

    def __init__(self, monitor: MockPerformanceMonitor, operation_name: str, labels=None):
        self.monitor = monitor
        self.operation_name = operation_name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.monitor.record_timer(self.operation_name, duration, self.labels)


def create_mock_trading_service(scenario: str = "normal") -> MockTradingService:
    """Create mock trading service with predefined scenario."""
    scenarios = {
        "normal": {"initial_balance": {"USD": 10000.0, "BTC": 1.0}, "order_execution_delay": 0.0},
        "low_balance": {
            "initial_balance": {"USD": 100.0, "BTC": 0.01},
            "order_execution_delay": 0.0,
        },
        "slow": {"initial_balance": {"USD": 10000.0, "BTC": 1.0}, "order_execution_delay": 0.5},
    }

    config = scenarios.get(scenario, scenarios["normal"])
    return MockTradingService(**config)


def create_mock_cache_service(scenario: str = "normal") -> MockCacheService:
    """Create mock cache service with predefined scenario."""
    scenarios = {
        "normal": {"max_size": 1000, "default_ttl": 30.0},
        "small": {"max_size": 10, "default_ttl": 5.0},
        "large": {"max_size": 10000, "default_ttl": 300.0},
    }

    config = scenarios.get(scenario, scenarios["normal"])
    return MockCacheService(**config)


def create_mock_performance_monitor(scenario: str = "normal") -> MockPerformanceMonitor:
    """Create mock performance monitor with predefined scenario."""
    monitor = MockPerformanceMonitor()
    monitor.set_scenario(scenario)
    return monitor
