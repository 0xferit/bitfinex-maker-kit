"""
Performance-monitored trading service wrapper for Maker-Kit.

Provides performance monitoring and metrics collection for all
trading operations with transparent integration.
"""

import asyncio
import logging
from typing import Any

from ..domain.amount import Amount
from ..domain.order_id import OrderId
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

    async def __aenter__(self) -> "MonitoredTradingService":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Async context manager exit."""
        await self.cleanup()

    def get_client(self) -> Any:
        """Get the underlying trading client."""
        return self._trading_service.get_client()

    async def place_order(
        self,
        symbol: Symbol,
        side: str,
        amount: Amount,
        price: Price | None = None,
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
        # Ensure monitoring is started in async context
        await self.performance_monitor.ensure_monitoring_started()

        operation_name = f"place_order_{side}_{symbol}"

        with (
            self.performance_monitor.time_operation(
                operation_name, {"symbol": str(symbol), "side": side}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                success, result = self._trading_service.place_order(symbol, side, amount, price)

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "place_order", str(symbol), success=success
                )

                return {"success": success, "result": result}

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "place_order", str(symbol), success=False
                )
                raise

    async def cancel_order(self, order_id: OrderId, symbol: Symbol | None = None) -> dict[str, Any]:
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
                operation_name, {"order_id": str(order_id), "symbol": symbol_str}
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                success, result = self._trading_service.cancel_order(order_id)

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "cancel_order", symbol_str, success=success
                )

                return {"success": success, "result": result}

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "cancel_order", symbol_str, success=False
                )
                raise

    async def update_order(
        self,
        order_id: OrderId,
        price: Price | None = None,
        amount: Amount | None = None,
        delta: Amount | None = None,
        use_cancel_recreate: bool = False,
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
        order_id_str = str(order_id)

        with (
            self.performance_monitor.time_operation(
                operation_name,
                {
                    "order_id": order_id_str,
                    "has_amount": str(amount is not None),
                    "has_price": str(price is not None),
                },
            ),
            self.profiler.profile_context(operation_name),
        ):
            try:
                success, result = self._trading_service.update_order(
                    order_id, price, amount, delta, use_cancel_recreate
                )

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "update_order", "order_update", success=success
                )

                return {"success": success, "result": result}

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "update_order", "order_update", success=False
                )
                raise

    async def get_orders(self, symbol: Symbol | None = None) -> list[dict[str, Any]]:
        """
        Get active orders with performance monitoring.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of active orders
        """
        operation_name = "get_orders"
        symbol_str = str(symbol) if symbol else "all"

        with (
            self.performance_monitor.time_operation(operation_name, {"symbol": symbol_str}),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = self._trading_service.get_orders(symbol)

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "get_orders", symbol_str, success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "get_orders", symbol_str, success=False
                )
                raise

    async def get_order_statistics(self) -> dict[str, Any]:
        """
        Get order statistics with performance monitoring.

        Returns:
            Order statistics dictionary
        """
        operation_name = "get_order_statistics"

        with (
            self.performance_monitor.time_operation(operation_name),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = self._trading_service.get_order_statistics()

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "get_order_statistics", "all", success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "get_order_statistics", "all", success=False
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

        with (
            self.performance_monitor.time_operation(operation_name, {"symbol": symbol_str}),
            self.profiler.profile_context(operation_name),
        ):
            try:
                # Get orders first, then cancel them individually
                orders = self._trading_service.get_orders(symbol)
                results = []

                for order in orders:
                    order_id = OrderId(str(order.id))
                    success, result = self._trading_service.cancel_order(order_id)
                    results.append(
                        {"order_id": str(order_id), "success": success, "result": result}
                    )

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "cancel_all_orders", symbol_str, success=True
                )

                return results

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "cancel_all_orders", symbol_str, success=False
                )
                raise

    async def get_wallet_balances(self) -> list[dict[str, Any]]:
        """
        Get wallet balances with performance monitoring.

        Returns:
            List of wallet balances
        """
        operation_name = "get_wallet_balances"

        with (
            self.performance_monitor.time_operation(operation_name),
            self.profiler.profile_context(operation_name),
        ):
            try:
                result = self._trading_service.get_wallet_balances()

                # Track successful operation
                self.performance_monitor.track_trading_operation(
                    "get_wallet_balances", "all", success=True
                )

                return result

            except Exception:
                # Track failed operation
                self.performance_monitor.track_trading_operation(
                    "get_wallet_balances", "all", success=False
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
                # Place orders individually since TradingService doesn't have batch method
                results = []
                for order_spec in orders:
                    symbol = Symbol(order_spec["symbol"])
                    side = order_spec["side"]
                    amount = Amount(order_spec["amount"])
                    price = Price(order_spec["price"]) if "price" in order_spec else None

                    success, result = self._trading_service.place_order(symbol, side, amount, price)
                    results.append({"success": success, "result": result})

                # Track successful batch operation
                self.performance_monitor.track_trading_operation(
                    "place_batch_orders", f"batch_{batch_size}", success=True
                )

                return results

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
