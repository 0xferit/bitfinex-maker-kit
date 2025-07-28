"""
Place order command implementation.

Implements the command pattern for order placement operations
with validation, execution, and undo capabilities.
"""

from decimal import Decimal

from ...domain.amount import Amount
from ...domain.order_id import OrderId
from ...domain.price import Price
from ...domain.symbol import Symbol
from .base_command import CommandContext, TransactionalCommand
from .command_result import CommandResult, ValidationResult


class PlaceOrderCommand(TransactionalCommand):
    """
    Command for placing a single order with full validation.

    Supports both limit and market orders with POST_ONLY enforcement
    for limit orders to maintain maker status.
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float | None = None,
        order_type: str = "limit",
    ) -> None:
        """
        Initialize place order command.

        Args:
            symbol: Trading symbol (e.g., 'tBTCUSD')
            side: Order side ('buy' or 'sell')
            amount: Order amount in base currency
            price: Order price (None for market orders)
            order_type: Order type ('limit' or 'market')
        """
        order_desc = f"{side.upper()} {amount} {symbol}"
        if price:
            order_desc += f" @ ${price:.6f}"
        else:
            order_desc += " at market price"

        super().__init__(
            name="place_order",
            description=f"Place order: {order_desc}",
            supports_undo=True,  # Can cancel the placed order
        )

        self.symbol_str = symbol
        self.side = side.lower()
        self.amount_float = amount
        self.price_float = price
        self.order_type = order_type.lower()

        # Will be set during validation
        self.symbol_obj: Symbol | None = None
        self.amount_obj: Amount | None = None
        self.price_obj: Price | None = None

        # Will be set during execution
        self.placed_order_id: OrderId | None = None
        self.placed_order_data: dict | None = None

    def validate(self, context: CommandContext) -> ValidationResult:
        """
        Validate order parameters and market conditions.

        Args:
            context: Command execution context

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult.success()

        try:
            # Validate and create domain objects
            self.symbol_obj = Symbol(self.symbol_str)
            self.amount_obj = Amount(Decimal(str(self.amount_float)))

            if self.price_float is not None:
                self.price_obj = Price(Decimal(str(self.price_float)))
            else:
                self.price_obj = None

        except ValueError as e:
            result.add_error(f"Invalid domain object: {e!s}")
            return result

        # Validate side
        if self.side not in ["buy", "sell"]:
            result.add_error(f"Invalid side: {self.side}. Must be 'buy' or 'sell'")

        # Validate order type
        if self.order_type not in ["limit", "market"]:
            result.add_error(f"Invalid order type: {self.order_type}. Must be 'limit' or 'market'")

        # Validate consistency
        if self.order_type == "market" and self.price_obj is not None:
            result.add_warning("Price specified for market order will be ignored")

        if self.order_type == "limit" and self.price_obj is None:
            result.add_error("Price required for limit orders")

        # Use trading service validation
        if not result.has_errors():
            is_valid, error_msg = context.trading_service.validate_order_parameters(
                self.symbol_obj, self.side, self.amount_obj, self.price_obj
            )

            if not is_valid:
                result.add_error(error_msg)

        # Market condition validations
        if not result.has_errors() and self.order_type == "limit" and self.price_obj is not None:
            ticker = context.trading_service.get_ticker(self.symbol_obj)
            if ticker:
                bid = float(ticker.get("bid", 0))
                ask = float(ticker.get("ask", 0))

                if bid > 0 and ask > 0:
                    price_val = float(self.price_obj.value)

                    # Warn about potentially problematic prices
                    if self.side == "buy" and price_val >= ask:
                        result.add_warning(
                            f"Buy price ${price_val:.6f} at or above ask ${ask:.6f} may execute immediately"
                        )
                    elif self.side == "sell" and price_val <= bid:
                        result.add_warning(
                            f"Sell price ${price_val:.6f} at or below bid ${bid:.6f} may execute immediately"
                        )

                    # Check for reasonable price ranges
                    spread_pct = ((ask - bid) / bid) * 100 if bid > 0 else 0
                    if spread_pct > 5.0:  # 5% spread
                        result.add_warning(
                            f"Wide spread detected: {spread_pct:.2f}% - verify price is correct"
                        )

        return result

    def execute(self, context: CommandContext) -> CommandResult:
        """
        Execute the order placement.

        Args:
            context: Command execution context

        Returns:
            CommandResult with execution outcome
        """
        # Validate required objects are available
        if self.symbol_obj is None:
            return CommandResult.failure("Symbol object not initialized - run validation first")

        if self.amount_obj is None:
            return CommandResult.failure("Amount object not initialized - run validation first")

        try:
            # Place order using trading service
            success, result_data = context.trading_service.place_order(
                self.symbol_obj, self.side, self.amount_obj, self.price_obj
            )

            if not success:
                return CommandResult.failure(f"Order placement failed: {result_data}")

            # Store order information for potential undo
            self.placed_order_data = result_data

            # Try to extract order ID
            if hasattr(result_data, "id"):
                self.placed_order_id = OrderId(result_data.id)
            elif isinstance(result_data, dict) and "id" in result_data:
                self.placed_order_id = OrderId(result_data["id"])
            elif isinstance(result_data, list) and len(result_data) > 0:
                # Handle array response format
                if hasattr(result_data[0], "id"):
                    self.placed_order_id = OrderId(result_data[0].id)
                elif isinstance(result_data[0], dict) and "id" in result_data[0]:
                    self.placed_order_id = OrderId(result_data[0]["id"])

            # Prepare result data
            result_info = {
                "order_id": str(self.placed_order_id) if self.placed_order_id else None,
                "symbol": str(self.symbol_obj) if self.symbol_obj else self.symbol_str,
                "side": self.side,
                "amount": float(self.amount_obj.value) if self.amount_obj else self.amount_float,
                "price": float(self.price_obj.value) if self.price_obj else None,
                "order_type": self.order_type,
                "raw_response": result_data,
            }

            self.logger.info(f"Order placed successfully: {self.placed_order_id}")
            return CommandResult.success(data=result_info)

        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return CommandResult.failure(f"Order placement error: {e!s}")

    def undo(self, context: CommandContext) -> CommandResult:
        """
        Undo order placement by cancelling the placed order.

        Args:
            context: Command execution context

        Returns:
            CommandResult with undo outcome
        """
        if self.placed_order_id is None:
            return CommandResult.failure("No order ID available for cancellation")

        try:
            # Cancel the placed order
            success, result = context.trading_service.cancel_order(self.placed_order_id)

            if success:
                self.logger.info(f"Order {self.placed_order_id} cancelled successfully (undo)")
                return CommandResult.success(
                    data={
                        "cancelled_order_id": str(self.placed_order_id),
                        "cancellation_result": result,
                    }
                )
            else:
                return CommandResult.failure(
                    f"Failed to cancel order {self.placed_order_id}: {result}"
                )

        except Exception as e:
            self.logger.error(f"Error cancelling order {self.placed_order_id}: {e}")
            return CommandResult.failure(f"Cancellation error: {e!s}")

    def get_preview(self, context: CommandContext) -> str:
        """Get a preview of the order to be placed."""
        preview = f"Place {self.side.upper()} order: {self.amount_float} {self.symbol_str}"

        if self.order_type == "limit" and self.price_float:
            preview += f" @ ${self.price_float:.6f} (POST-ONLY)"
        else:
            preview += " at MARKET price"

        return preview

    def get_confirmation_message(self, context: CommandContext) -> str:
        """Get confirmation message for user prompt."""
        return f"Do you want to {self.get_preview(context)}?"
