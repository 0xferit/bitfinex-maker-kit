"""
Service mock utilities for testing.

Provides comprehensive mocking for trading services.
"""

import asyncio
import time
from typing import Any
from unittest.mock import Mock

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
        self, symbol, side, amount, price, order_type: str = "EXCHANGE LIMIT", **kwargs
    ) -> dict[str, Any]:
        """Mock place order operation - POST_ONLY limit orders only."""
        if price is None:
            raise ValueError(
                "Market orders are not supported. This program only supports POST_ONLY limit orders."
            )

        # Validate inputs
        symbol_str = str(symbol)
        amount_str = str(amount)
        price_str = str(price)

        price_val = float(price_str)
        amount_val = float(amount_str)

        if price_val <= 0:
            raise ValueError(f"Price must be positive, got {price_val}")
        if amount_val == 0:
            raise ValueError("Amount cannot be zero")
        if side not in ["buy", "sell"]:
            raise ValueError(f"Side must be 'buy' or 'sell', got {side}")

        self._record_operation(
            "place_order", symbol=symbol_str, amount=amount_str, price=price_str, side=side
        )
        await self._simulate_delay()

        # Create order
        order_id = self.order_counter
        self.order_counter += 1

        order = self.fixtures.create_order(
            order_id=order_id,
            symbol=symbol_str,
            amount=amount_str,
            price=price_str,
            side=side,
            order_type=order_type,
        )

        self.orders[order_id] = order
        return order.to_dict()

    def place_order_sync(
        self, symbol, side, amount, price, order_type: str = "EXCHANGE LIMIT", **kwargs
    ) -> tuple[bool, dict[str, Any]]:
        """Sync version of place_order for compatibility - POST_ONLY limit orders only."""
        try:
            if price is None:
                return (
                    False,
                    "Market orders are not supported. This program only supports POST_ONLY limit orders.",
                )

            symbol_str = str(symbol)
            amount_str = str(amount)
            price_str = str(price)

            price_val = float(price_str)
            if price_val <= 0:
                return False, f"Price must be positive, got {price_val}"

            amount_val = float(amount_str)
            if amount_val == 0:
                return False, "Amount cannot be zero"
            if side not in ["buy", "sell"]:
                return False, f"Side must be 'buy' or 'sell', got {side}"

            self._record_operation(
                "place_order", symbol=symbol_str, amount=amount_str, price=price_str, side=side
            )

            order_id = self.order_counter
            self.order_counter += 1

            order = self.fixtures.create_order(
                order_id=order_id,
                symbol=symbol_str,
                amount=amount_str,
                price=price_str,
                side=side,
                order_type=order_type,
            )

            self.orders[order_id] = order
            return True, order.to_dict()

        except Exception as e:
            return False, str(e)

    async def cancel_order(self, order_id: str, symbol=None) -> dict[str, Any]:
        """Mock cancel order operation."""
        self._record_operation(
            "cancel_order", order_id=order_id, symbol=str(symbol) if symbol else None
        )
        await self._simulate_delay()

        order_id_int = int(order_id)

        if order_id_int in self.orders:
            order = self.orders[order_id_int]
            if order.status == "CANCELED":
                raise Exception(f"Order {order_id} is already canceled")
            if order.status == "ACTIVE":
                canceled_order = order.mark_canceled()
                self.orders[order_id_int] = canceled_order
                return canceled_order.to_dict()
            else:
                raise Exception(f"Order {order_id} cannot be canceled (status: {order.status})")
        else:
            raise Exception(f"Order {order_id} not found")

    def cancel_order_sync(self, order_id: str, symbol=None) -> tuple[bool, dict[str, Any]]:
        """Sync version of cancel_order for compatibility."""
        try:
            self._record_operation(
                "cancel_order", order_id=order_id, symbol=str(symbol) if symbol else None
            )

            order_id_int = int(order_id)

            if order_id_int in self.orders:
                order = self.orders[order_id_int]
                if order.status == "CANCELED":
                    return False, f"Order {order_id} is already canceled"
                if order.status == "ACTIVE":
                    canceled_order = order.mark_canceled()
                    self.orders[order_id_int] = canceled_order
                    return True, canceled_order.to_dict()
                else:
                    return False, f"Order {order_id} cannot be canceled (status: {order.status})"
            else:
                return False, f"Order {order_id} not found"

        except Exception as e:
            return False, str(e)

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
            if order.status == "ACTIVE" and (symbol is None or order.symbol == str(symbol)):
                active_orders.append(order.to_dict())

        return active_orders

    def get_orders(self, symbol=None) -> list[dict[str, Any]]:
        """Sync get orders operation for compatibility."""
        self._record_operation("get_orders", symbol=str(symbol) if symbol else None)

        orders = []
        for order in self.orders.values():
            if symbol is None or order.symbol == str(symbol):
                orders.append(order.to_dict())

        return orders

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
            if order.status == "ACTIVE" and (symbol is None or order.symbol == str(symbol)):
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
                    "available": balance * 0.95,
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
