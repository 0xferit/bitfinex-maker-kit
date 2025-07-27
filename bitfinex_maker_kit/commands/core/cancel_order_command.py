"""
Cancel order command implementation.

Implements the command pattern for order cancellation operations
with validation and execution capabilities.
"""

from typing import Any

from ...domain.order_id import OrderId
from ...domain.symbol import Symbol
from .base_command import BatchCommand, CommandContext, TransactionalCommand
from .command_result import CommandResult, ValidationResult


class CancelOrderCommand(TransactionalCommand):
    """
    Command for cancelling a single order by ID.

    Provides validation and execution for order cancellation
    with proper error handling.
    """

    def __init__(self, order_id: int | str) -> None:
        """
        Initialize cancel order command.

        Args:
            order_id: Order ID to cancel
        """
        super().__init__(
            name="cancel_order",
            description=f"Cancel order {order_id}",
            supports_undo=False,  # Cannot undo cancellation
        )

        self.order_id_input = order_id
        self.order_id_obj: OrderId | None = None
        self.cancelled_order_data: dict | None = None

    def validate(self, context: CommandContext) -> ValidationResult:
        """
        Validate order ID and check if order exists.

        Args:
            context: Command execution context

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult.success()

        try:
            # Create order ID domain object
            self.order_id_obj = OrderId(self.order_id_input)

            # Check for placeholder orders
            if self.order_id_obj.is_placeholder_id():
                result.add_error("Cannot cancel placeholder orders")
                return result

        except ValueError as e:
            result.add_error(f"Invalid order ID: {e!s}")
            return result

        # Check if order exists
        try:
            orders = context.trading_service.get_orders()
            order_exists = any(
                hasattr(order, "id") and str(order.id) == str(self.order_id_obj.value)
                for order in orders
            )

            if not order_exists:
                result.add_warning(
                    f"Order {self.order_id_obj} not found in active orders (may have been filled or already cancelled)"
                )

        except Exception as e:
            result.add_warning(f"Could not verify order existence: {e!s}")

        return result

    def execute(self, context: CommandContext) -> CommandResult:
        """
        Execute the order cancellation.

        Args:
            context: Command execution context

        Returns:
            CommandResult with execution outcome
        """
        # Validate order ID object is available
        if self.order_id_obj is None:
            return CommandResult.failure("Order ID object not initialized - run validation first")

        try:
            # Cancel order using trading service
            success, result_data = context.trading_service.cancel_order(self.order_id_obj)

            if success:
                self.cancelled_order_data = result_data
                self.logger.info(f"Order {self.order_id_obj} cancelled successfully")

                return CommandResult.success(
                    data={
                        "cancelled_order_id": str(self.order_id_obj),
                        "cancellation_result": result_data,
                    }
                )
            else:
                # Handle specific error cases
                error_msg = str(result_data).lower()
                if "not found" in error_msg:
                    return CommandResult.failure(
                        f"Order {self.order_id_obj} not found (may have been filled or already cancelled)"
                    )
                else:
                    return CommandResult.failure(f"Cancellation failed: {result_data}")

        except Exception as e:
            self.logger.error(f"Error cancelling order {self.order_id_obj}: {e}")
            return CommandResult.failure(f"Cancellation error: {e!s}")

    def get_preview(self, context: CommandContext) -> str:
        """Get a preview of the cancellation operation."""
        return f"Cancel order {self.order_id_input}"

    def get_confirmation_message(self, context: CommandContext) -> str:
        """Get confirmation message for user prompt."""
        return f"Do you want to cancel order {self.order_id_input}?"


class CancelOrdersByCriteriaCommand(BatchCommand):
    """
    Command for cancelling multiple orders based on criteria.

    Supports filtering by symbol, side, price range, and size
    with batch execution and partial failure handling.
    """

    def __init__(
        self,
        symbol: str | None = None,
        side: str | None = None,
        price_below: float | None = None,
        price_above: float | None = None,
        size: float | None = None,
        fail_fast: bool = False,
    ) -> None:
        """
        Initialize cancel orders by criteria command.

        Args:
            symbol: Symbol filter (optional)
            side: Side filter ('buy' or 'sell', optional)
            price_below: Cancel orders with price below this value
            price_above: Cancel orders with price above this value
            size: Size filter (optional)
            fail_fast: Whether to stop on first failure
        """
        # Build description
        criteria_parts = []
        if symbol:
            criteria_parts.append(f"symbol {symbol}")
        if side:
            criteria_parts.append(f"side {side.upper()}")
        if price_below:
            criteria_parts.append(f"price < ${price_below:.6f}")
        if price_above:
            criteria_parts.append(f"price > ${price_above:.6f}")
        if size:
            criteria_parts.append(f"size {size}")

        criteria_desc = " and ".join(criteria_parts) if criteria_parts else "all orders"

        super().__init__(
            name="cancel_orders_by_criteria",
            description=f"Cancel orders matching: {criteria_desc}",
            fail_fast=fail_fast,
        )

        self.symbol_filter = symbol
        self.side_filter = side.lower() if side else None
        self.price_below = price_below
        self.price_above = price_above
        self.size_filter = size

        self.matching_orders: list[Any] = []

    def validate(self, context: CommandContext) -> ValidationResult:
        """
        Validate criteria and find matching orders.

        Args:
            context: Command execution context

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult.success()

        # Validate side filter
        if self.side_filter and self.side_filter not in ["buy", "sell"]:
            result.add_error(f"Invalid side filter: {self.side_filter}")

        # Validate price ranges
        if self.price_below is not None and self.price_below <= 0:
            result.add_error("Price below must be positive")

        if self.price_above is not None and self.price_above <= 0:
            result.add_error("Price above must be positive")

        if (
            self.price_below is not None
            and self.price_above is not None
            and self.price_below <= self.price_above
        ):
            result.add_error("Price below must be greater than price above")

        # Validate size
        if self.size_filter is not None and self.size_filter <= 0:
            result.add_error("Size filter must be positive")

        if result.has_errors():
            return result

        # Find matching orders
        try:
            symbol_obj = Symbol(self.symbol_filter) if self.symbol_filter else None
            all_orders = context.trading_service.get_orders(symbol_obj)

            self.matching_orders = self._filter_orders(all_orders)

            if not self.matching_orders:
                result.add_warning("No orders match the specified criteria")
            else:
                self.logger.info(f"Found {len(self.matching_orders)} orders matching criteria")

        except Exception as e:
            result.add_error(f"Error finding matching orders: {e!s}")

        return result

    def execute(self, context: CommandContext) -> CommandResult:
        """
        Execute batch cancellation of matching orders.

        Args:
            context: Command execution context

        Returns:
            CommandResult with batch execution outcome
        """
        if not self.matching_orders:
            return CommandResult.success(
                data={
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "message": "No orders to cancel",
                }
            )

        # Execute batch cancellation
        return self.execute_batch_operation(self.matching_orders, context)

    def _execute_single_operation(self, order: Any, context: CommandContext) -> CommandResult:
        """
        Cancel a single order within the batch.

        Args:
            order: Order object to cancel
            context: Command execution context

        Returns:
            CommandResult for the single cancellation
        """
        try:
            order_id = OrderId(order.id)
            success, result = context.trading_service.cancel_order(order_id)

            if success:
                return CommandResult.success(
                    data={
                        "cancelled_order_id": str(order_id),
                        "order_info": {
                            "symbol": order.symbol,
                            "side": "BUY" if float(order.amount) > 0 else "SELL",
                            "amount": abs(float(order.amount)),
                            "price": float(order.price) if hasattr(order, "price") else None,
                        },
                    }
                )
            else:
                return CommandResult.failure(f"Failed to cancel order {order_id}: {result}")

        except Exception as e:
            return CommandResult.failure(f"Error cancelling order: {e!s}")

    def _filter_orders(self, orders: list[Any]) -> list[Any]:
        """
        Filter orders based on criteria.

        Args:
            orders: List of order objects

        Returns:
            Filtered list of orders
        """
        filtered = []

        for order in orders:
            # Symbol filter
            if self.symbol_filter and order.symbol != self.symbol_filter:
                continue

            # Side filter
            if self.side_filter:
                order_side = "buy" if float(order.amount) > 0 else "sell"
                if order_side != self.side_filter:
                    continue

            # Size filter
            if self.size_filter is not None:
                order_size = abs(float(order.amount))
                if order_size != self.size_filter:
                    continue

            # Price filters
            if hasattr(order, "price") and order.price:
                order_price = float(order.price)

                if self.price_below is not None and order_price >= self.price_below:
                    continue

                if self.price_above is not None and order_price <= self.price_above:
                    continue

            filtered.append(order)

        return filtered

    def get_preview(self, context: CommandContext) -> str:
        """Get a preview of the batch cancellation operation."""
        if not self.matching_orders:
            return "Cancel 0 orders (no matches found)"

        return f"Cancel {len(self.matching_orders)} orders matching criteria"

    def get_confirmation_message(self, context: CommandContext) -> str:
        """Get confirmation message for batch cancellation."""
        return f"Do you want to {self.get_preview(context)}?"
