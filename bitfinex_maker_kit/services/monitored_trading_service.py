"""
Performance-monitored trading service wrapper for Maker-Kit.

Provides performance monitoring and metrics collection for all
trading operations with transparent integration.
"""

import asyncio
import logging
from typing import Any

from ..domain.amount import Amount
from ..domain.price import Price
from ..domain.symbol import Symbol
from ..services.container import ServiceContainer
from ..services.performance_monitor import PerformanceMonitor, create_performance_monitor
from ..utilities.profiler import PerformanceProfiler, get_profiler

logger = logging.getLogger(__name__)


class MonitoredTradingService:
    """
    Trading service wrapper with comprehensive performance monitoring.

    Transparently adds performance tracking to all trading operations
    while maintaining the same interface as the original service.
    """

    def __init__(
        self,
        container: ServiceContainer,
        performance_monitor: PerformanceMonitor | None = None,
        profiler: PerformanceProfiler | None = None,
    ):
        """
        Initialize monitored trading service.

        Args:
            container: Service container for dependency injection
            performance_monitor: Optional performance monitor
            profiler: Optional performance profiler
        """
        self.container = container
        self.performance_monitor = performance_monitor or create_performance_monitor()
        self.profiler = profiler or get_profiler()

        # Get the actual trading service
        self._trading_service = container.create_trading_service()

        # Start performance monitoring
        self.performance_monitor.start_monitoring()

        logger.info("Monitored trading service initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    def get_client(self):
        """Get the underlying trading client."""
        return self._trading_service.get_client()

    async def place_order(
        self,
        symbol: Symbol,
        amount: Amount,
        price: Price,
        side: str,
        order_type: str = "EXCHANGE LIMIT",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Place order with performance monitoring.

        Args:
            symbol: Trading symbol
            amount: Order amount
            price: Order price
            side: Order side (buy/sell)
            order_type: Order type
            **kwargs: Additional order parameters

        Returns:
            Order result dictionary
        """
        operation_name = f"place_order_{side}_{symbol}"

        with (
            self.performance_monitor.time_operation(
                operation_name, {"symbol": str(symbol), "side": side, "order_type": order_type}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = await self._trading_service.place_order(
                    symbol, amount, price, side, order_type, **kwargs
                )

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "place_order", str(symbol), success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "place_order", str(symbol), success=False
                )
                raise

    async def cancel_order(self, order_id: str, symbol: Symbol | None = None) -> dict[str, Any]:
        """
        Cancel order with performance monitoring.

        Args:
            order_id: Order ID to cancel
            symbol: Optional trading symbol

        Returns:
            Cancellation result dictionary
        """
        operation_name = "cancel_order"
        symbol_str = str(symbol) if symbol else "unknown"

        with (
            self.performance_monitor.time_operation(
                operation_name, {"order_id": order_id, "symbol": symbol_str}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = await self._trading_service.cancel_order(order_id, symbol)

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "cancel_order", symbol_str, success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "cancel_order", symbol_str, success=False
                )
                raise

    async def update_order(
        self,
        order_id: str,
        new_amount: Amount | None = None,
        new_price: Price | None = None,
        symbol: Symbol | None = None,
    ) -> dict[str, Any]:
        """
        Update order with performance monitoring.

        Args:
            order_id: Order ID to update
            new_amount: New order amount
            new_price: New order price
            symbol: Optional trading symbol

        Returns:
            Update result dictionary
        """
        operation_name = "update_order"
        symbol_str = str(symbol) if symbol else "unknown"

        with (
            self.performance_monitor.time_operation(
                operation_name,
                {
                    "order_id": order_id,
                    "symbol": symbol_str,
                    "has_amount": new_amount is not None,
                    "has_price": new_price is not None,
                },
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = await self._trading_service.update_order(
                    order_id, new_amount, new_price, symbol
                )

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "update_order", symbol_str, success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "update_order", symbol_str, success=False
                )
                raise

    async def get_active_orders(self, symbol: Symbol | None = None) -> list[dict[str, Any]]:
        """
        Get active orders with performance monitoring.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of active orders
        """
        operation_name = "get_active_orders"
        symbol_str = str(symbol) if symbol else "all"

        with self.performance_monitor.time_operation(operation_name, {"symbol": symbol_str}):
            with self.profiler.profile_context(operation_name):
                try:
                    result = await self._trading_service.get_active_orders(symbol)

                    # Track successful operation
                    self.performance_monitor.track_trading_operation(
                        "get_active_orders", symbol_str, success=True
                    )

                    return result

                except Exception:
                    # Track failed operation
                    self.performance_monitor.track_trading_operation(
                        "get_active_orders", symbol_str, success=False
                    )
                    raise

    async def get_order_status(self, order_id: str, symbol: Symbol | None = None) -> dict[str, Any]:
        """
        Get order status with performance monitoring.

        Args:
            order_id: Order ID to check
            symbol: Optional trading symbol

        Returns:
            Order status dictionary
        """
        operation_name = "get_order_status"
        symbol_str = str(symbol) if symbol else "unknown"

        with (
            self.performance_monitor.time_operation(
                operation_name, {"order_id": order_id, "symbol": symbol_str}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = await self._trading_service.get_order_status(order_id, symbol)

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "get_order_status", symbol_str, success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "get_order_status", symbol_str, success=False
                )
                raise

    async def cancel_all_orders(self, symbol: Symbol | None = None) -> list[dict[str, Any]]:
        """
        Cancel all orders with performance monitoring.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of cancellation results
        """
        operation_name = "cancel_all_orders"
        symbol_str = str(symbol) if symbol else "all"

        with self.performance_monitor.time_operation(operation_name, {"symbol": symbol_str}):
            with self.profiler.profile_context(operation_name):
                try:
                    result = await self._trading_service.cancel_all_orders(symbol)

                    # Track successful operation
                    self.performance_monitor.track_trading_operation(
                        "cancel_all_orders", symbol_str, success=True
                    )

                    return result

                except Exception:
                    # Track failed operation
                    self.performance_monitor.track_trading_operation(
                        "cancel_all_orders", symbol_str, success=False
                    )
                    raise

    async def get_account_balance(self) -> list[dict[str, Any]]:
        """
        Get account balance with performance monitoring.

        Returns:
            List of account balances
        """
        operation_name = "get_account_balance"

        with self.performance_monitor.time_operation(operation_name):
            with self.profiler.profile_context(operation_name):
                try:
                    result = await self._trading_service.get_account_balance()

                    # Track successful operation
                    self.performance_monitor.track_trading_operation(
                        "get_account_balance", "all", success=True
                    )

                    return result

                except Exception:
                    # Track failed operation
                    self.performance_monitor.track_trading_operation(
                        "get_account_balance", "all", success=False
                    )
                    raise

    async def place_batch_orders(self, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Place batch orders with performance monitoring.

        Args:
            orders: List of order specifications

        Returns:
            List of order results
        """
        operation_name = "place_batch_orders"
        batch_size = len(orders)

        with (
            self.performance_monitor.time_operation(
                operation_name, {"batch_size": str(batch_size)}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = await self._trading_service.place_batch_orders(orders)

                # Track successful batch operation
                self.performance_monitor.track_trading_operation(
                    "place_batch_orders", f"batch_{batch_size}", success=True
                )

                return result

            except Exception:
                # Track failed batch operation
                self.performance_monitor.track_trading_operation(
                    "place_batch_orders", f"batch_{batch_size}", success=False
                )
                raise

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Performance metrics dictionary
        """
        return self.performance_monitor.get_current_metrics().to_dict()

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get performance summary with insights.

        Returns:
            Performance summary dictionary
        """
        return self.performance_monitor.get_performance_summary()

    def get_profiling_report(self) -> dict[str, Any]:
        """
        Get profiling report.

        Returns:
            Profiling report dictionary
        """
        return self.profiler.generate_performance_report()

    def export_performance_data(self, output_file: str) -> None:
        """
        Export performance data to file.

        Args:
            output_file: Output file path
        """
        try:
            # Combine monitoring and profiling data
            data = {
                "timestamp": asyncio.get_event_loop().time(),
                "performance_metrics": self.get_performance_metrics(),
                "performance_summary": self.get_performance_summary(),
                "profiling_report": self.get_profiling_report(),
            }

            import json

            with open(output_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Performance data exported to {output_file}")

        except Exception as e:
            logger.error(f"Error exporting performance data: {e}")

    def reset_metrics(self) -> None:
        """Reset all performance metrics and profiling data."""
        # Reset performance monitor counters (if method exists)
        # For now, we'll create a new monitor
        self.performance_monitor = create_performance_monitor()
        self.performance_monitor.start_monitoring()

        # Clear profiling data
        self.profiler.clear_profile_data()

        logger.info("Performance metrics reset")

    async def cleanup(self) -> None:
        """Clean up monitored trading service resources."""
        try:
            # Stop performance monitoring
            await self.performance_monitor.stop_monitoring()

            # Cleanup underlying trading service if it has cleanup method
            if hasattr(self._trading_service, "cleanup"):
                await self._trading_service.cleanup()

            logger.info("Monitored trading service cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def create_monitored_trading_service(
    container: ServiceContainer,
    performance_monitor: PerformanceMonitor | None = None,
    profiler: PerformanceProfiler | None = None,
) -> MonitoredTradingService:
    """
    Create monitored trading service with configuration.

    Args:
        container: Service container for dependency injection
        performance_monitor: Optional performance monitor
        profiler: Optional performance profiler

    Returns:
        Configured MonitoredTradingService instance
    """
    return MonitoredTradingService(container, performance_monitor, profiler)
