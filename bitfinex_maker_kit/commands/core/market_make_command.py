"""
Market making command implementation.

Implements the command pattern for market making operations
with order generation, validation, and batch execution.
"""

from decimal import Decimal

from ...domain.amount import Amount
from ...domain.price import Price
from ...domain.symbol import Symbol
from ...strategies.order_generator import OrderGenerator
from .base_command import BatchCommand, CommandContext
from .command_result import CommandResult, ValidationResult
from .place_order_command import PlaceOrderCommand


class MarketMakeCommand(BatchCommand):
    """
    Command for creating staircase market making orders.

    Generates multiple limit orders at different price levels
    around a center price with configurable spread and size.
    """

    def __init__(
        self,
        symbol: str,
        center_price: float,
        levels: int,
        spread_pct: float,
        size: float,
        side_filter: str | None = None,
    ) -> None:
        """
        Initialize market making command.

        Args:
            symbol: Trading symbol
            center_price: Center price for order generation
            levels: Number of price levels on each side
            spread_pct: Spread percentage per level
            size: Order size for each level
            side_filter: Optional side filter ('buy' or 'sell')
        """
        side_desc = f" ({side_filter.upper()}-only)" if side_filter else ""

        super().__init__(
            name="market_make",
            description=f"Create {levels} levels of market making orders for {symbol} @ ${center_price:.6f}{side_desc}",
            fail_fast=False,  # Continue placing orders even if some fail
        )

        self.symbol_str = symbol
        self.center_price_float = center_price
        self.levels = levels
        self.spread_pct = spread_pct
        self.size_float = size
        self.side_filter = side_filter.lower() if side_filter else None

        # Domain objects (set during validation)
        self.symbol_obj: Symbol | None = None
        self.center_price_obj: Price | None = None
        self.size_obj: Amount | None = None

        # Order generator and generated orders
        self.order_generator: OrderGenerator | None = None
        self.generated_orders: list[tuple[str, float, float]] = []
        self.place_order_commands: list[PlaceOrderCommand] = []

    def validate(self, context: CommandContext) -> ValidationResult:
        """
        Validate market making parameters and generate orders.

        Args:
            context: Command execution context

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult.success()

        try:
            # Create and validate domain objects
            self.symbol_obj = Symbol(self.symbol_str)
            self.center_price_obj = Price(Decimal(str(self.center_price_float)))
            self.size_obj = Amount(Decimal(str(self.size_float)))

        except ValueError as e:
            result.add_error(f"Invalid domain object: {e!s}")
            return result

        # Validate parameters
        if self.levels <= 0:
            result.add_error("Number of levels must be positive")

        if self.levels > 20:
            result.add_warning("High number of levels may result in many orders")

        if self.spread_pct <= 0:
            result.add_error("Spread percentage must be positive")

        if self.spread_pct > 10:
            result.add_warning("Large spread percentage may create orders far from market")

        if self.side_filter and self.side_filter not in ["buy", "sell"]:
            result.add_error(f"Invalid side filter: {self.side_filter}")

        if result.has_errors():
            return result

        # Create order generator and generate orders
        try:
            self.order_generator = OrderGenerator(
                self.levels, self.spread_pct, self.size_float, self.side_filter
            )
            self.generated_orders = self.order_generator.generate_orders(self.center_price_float)

            if not self.generated_orders:
                result.add_error("No orders generated - check parameters")
                return result

            self.logger.info(f"Generated {len(self.generated_orders)} market making orders")

        except Exception as e:
            result.add_error(f"Error generating orders: {e!s}")
            return result

        # Validate each generated order
        for i, (side, amount, price) in enumerate(self.generated_orders):
            try:
                # Create place order command for validation
                place_cmd = PlaceOrderCommand(self.symbol_str, side, amount, price, "limit")
                cmd_validation = place_cmd.validate(context)

                if not cmd_validation.is_valid:
                    result.add_error(
                        f"Order {i + 1} validation failed: {cmd_validation.get_error_summary()}"
                    )

                # Add warnings from individual orders
                for warning in cmd_validation.warnings:
                    result.add_warning(f"Order {i + 1}: {warning}")

                self.place_order_commands.append(place_cmd)

            except Exception as e:
                result.add_error(f"Error validating order {i + 1}: {e!s}")

        # Market condition validation
        try:
            ticker = context.trading_service.get_ticker(self.symbol_obj)
            if ticker:
                bid = float(ticker.get("bid", 0))
                ask = float(ticker.get("ask", 0))

                if bid > 0 and ask > 0:
                    # Check if center price is reasonable
                    mid_price = (bid + ask) / 2
                    center_deviation = abs(self.center_price_float - mid_price) / mid_price * 100

                    if center_deviation > 5:  # 5% deviation
                        result.add_warning(
                            f"Center price deviates {center_deviation:.2f}% from mid price ${mid_price:.6f}"
                        )

                    # Check order price ranges
                    min_price = min(price for _, _, price in self.generated_orders)
                    max_price = max(price for _, _, price in self.generated_orders)

                    if min_price < bid * 0.5:
                        result.add_warning(
                            f"Some buy orders very far below market (min: ${min_price:.6f})"
                        )

                    if max_price > ask * 2:
                        result.add_warning(
                            f"Some sell orders very far above market (max: ${max_price:.6f})"
                        )

        except Exception as e:
            result.add_warning(f"Could not validate market conditions: {e!s}")

        # Capital requirement estimation
        try:
            capital_info = self.order_generator.calculate_total_capital_required(
                self.center_price_float
            )

            result.add_warning(
                f"Estimated capital required: "
                f"{capital_info['buy_capital_quote']:.2f} quote currency (for {capital_info['buy_orders']} buy orders), "
                f"{capital_info['sell_capital_base']:.2f} base currency (for {capital_info['sell_orders']} sell orders)"
            )

        except Exception as e:
            result.add_warning(f"Could not calculate capital requirements: {e!s}")

        return result

    def execute(self, context: CommandContext) -> CommandResult:
        """
        Execute batch placement of market making orders.

        Args:
            context: Command execution context

        Returns:
            CommandResult with batch execution outcome
        """
        if not self.place_order_commands:
            return CommandResult.failure("No orders to place")

        # Execute batch order placement
        return self.execute_batch_operation(self.place_order_commands, context)

    def _execute_single_operation(
        self, place_cmd: PlaceOrderCommand, context: CommandContext
    ) -> CommandResult:
        """
        Execute a single order placement within the batch.

        Args:
            place_cmd: PlaceOrderCommand to execute
            context: Command execution context

        Returns:
            CommandResult for the single order placement
        """
        return place_cmd.execute(context)

    def can_undo(self) -> bool:
        """Market making command supports undo by cancelling all placed orders."""
        return True

    def undo(self, context: CommandContext) -> CommandResult:
        """
        Undo market making by cancelling all successfully placed orders.

        Args:
            context: Command execution context

        Returns:
            CommandResult with undo outcome
        """
        if not self.partial_results:
            return CommandResult.failure("No orders were placed to cancel")

        # Find successfully placed orders
        orders_to_cancel = []
        for _i, result in enumerate(self.partial_results):
            if result.is_success() and result.data and "order_id" in result.data:
                order_id = result.data["order_id"]
                if order_id:
                    orders_to_cancel.append(order_id)

        if not orders_to_cancel:
            return CommandResult.failure("No order IDs found for cancellation")

        # Cancel orders
        cancelled_count = 0
        failed_cancellations = []

        for order_id in orders_to_cancel:
            try:
                from .cancel_order_command import CancelOrderCommand

                cancel_cmd = CancelOrderCommand(order_id)
                cancel_result = cancel_cmd.execute_with_validation(context)

                if cancel_result.is_success():
                    cancelled_count += 1
                else:
                    failed_cancellations.append(f"{order_id}: {cancel_result.error_message}")

            except Exception as e:
                failed_cancellations.append(f"{order_id}: {e!s}")

        # Prepare undo result
        undo_data = {
            "total_orders": len(orders_to_cancel),
            "cancelled_orders": cancelled_count,
            "failed_cancellations": failed_cancellations,
        }

        if cancelled_count == len(orders_to_cancel):
            return CommandResult.success(data=undo_data)
        elif cancelled_count > 0:
            result = CommandResult.failure(
                f"Partially cancelled: {cancelled_count}/{len(orders_to_cancel)} orders"
            )
            result.data = undo_data
            return result
        else:
            result = CommandResult.failure("Failed to cancel any orders")
            result.data = undo_data
            return result

    def get_preview(self, context: CommandContext) -> str:
        """Get a preview of the market making orders."""
        if not self.generated_orders:
            return f"Generate market making orders for {self.symbol_str}"

        side_desc = f" ({self.side_filter.upper()}-only)" if self.side_filter else ""
        return (
            f"Place {len(self.generated_orders)} market making orders: "
            f"{self.levels} levels @ {self.spread_pct}% spread, "
            f"size {self.size_float} each{side_desc}"
        )

    def get_confirmation_message(self, context: CommandContext) -> str:
        """Get confirmation message for market making."""
        return f"Do you want to {self.get_preview(context)}?"

    def get_order_preview_table(self) -> str:
        """
        Get a formatted table preview of the orders to be placed.

        Returns:
            Formatted string with order details
        """
        if not self.generated_orders:
            return "No orders generated"

        # Sort orders by price for better visualization
        sorted_orders = sorted(self.generated_orders, key=lambda x: x[2])

        lines = [
            "Market Making Orders Preview:",
            "─" * 55,
            f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Center':<20}",
            "─" * 55,
        ]

        for side, amount, price in sorted_orders:
            distance_pct = ((price - self.center_price_float) / self.center_price_float) * 100
            distance_str = f"{distance_pct:+.3f}%"
            lines.append(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")

        return "\n".join(lines)
