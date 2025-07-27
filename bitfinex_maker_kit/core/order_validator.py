"""
Order update validation logic.

Extracted from BitfinexClientWrapper to provide focused validation
of order update requests with clear error messages.
"""

import logging
from decimal import Decimal
from typing import Any

from ..update_strategies.base import OrderUpdateRequest

logger = logging.getLogger(__name__)


class OrderUpdateValidator:
    """
    Validates order update requests with comprehensive error checking.

    Provides centralized validation logic that was previously embedded
    in the large update_order method.
    """

    def validate_update_request(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
    ) -> OrderUpdateRequest:
        """
        Validate and create an OrderUpdateRequest.

        Args:
            order_id: ID of the order to update
            price: New price for the order
            amount: New absolute amount for the order
            delta: Amount to add/subtract from current amount

        Returns:
            Validated OrderUpdateRequest

        Raises:
            ValueError: If validation fails
        """
        logger.debug(f"Validating update request for order {order_id}")

        try:
            # Convert to Decimal for precise validation
            decimal_price = Decimal(str(price)) if price is not None else None
            decimal_amount = Decimal(str(amount)) if amount is not None else None
            decimal_delta = Decimal(str(delta)) if delta is not None else None

            # Create and validate the request (validation happens in __post_init__)
            request = OrderUpdateRequest(
                order_id=order_id, price=decimal_price, amount=decimal_amount, delta=decimal_delta
            )

            logger.debug(f"Update request validated successfully for order {order_id}")
            return request

        except (ValueError, TypeError) as e:
            logger.error(f"Update request validation failed for order {order_id}: {e}")
            raise ValueError(f"Invalid update parameters: {e}") from e

    def validate_order_exists(self, order_id: int, order_list: list[Any]) -> Any:
        """
        Validate that an order exists in the given order list.

        Args:
            order_id: ID of the order to find
            order_list: List of orders from the API

        Returns:
            The order object if found

        Raises:
            ValueError: If order is not found
        """
        logger.debug(f"Searching for order {order_id} in {len(order_list)} orders")

        for order in order_list:
            if order.id == order_id:
                logger.debug(f"Found order {order_id}")
                return order

        logger.warning(f"Order {order_id} not found in active orders")
        raise ValueError(f"Order {order_id} not found")

    def validate_order_state(self, order: Any) -> None:
        """
        Validate that an order is in a state that allows updates.

        Args:
            order: Order object from API

        Raises:
            ValueError: If order cannot be updated
        """
        logger.debug(f"Validating state of order {order.id}")

        # Check if order has required attributes
        if not hasattr(order, "amount"):
            raise ValueError(f"Order {order.id} missing amount attribute")

        if not hasattr(order, "price"):
            raise ValueError(f"Order {order.id} missing price attribute")

        # Validate order amount
        try:
            current_amount = float(order.amount)
            if current_amount == 0:
                raise ValueError(f"Order {order.id} has zero amount, cannot update")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Order {order.id} has invalid amount: {order.amount}") from e

        # Validate order price (can be None for market orders)
        if order.price is not None:
            try:
                current_price = float(order.price)
                if current_price <= 0:
                    raise ValueError(f"Order {order.id} has invalid price: {order.price}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Order {order.id} has invalid price format: {order.price}") from e

        logger.debug(f"Order {order.id} state validation passed")

    def validate_new_amount_calculation(
        self, request: OrderUpdateRequest, current_order: Any
    ) -> Decimal:
        """
        Validate and calculate the new amount for the order.

        Args:
            request: The update request
            current_order: Current order from API

        Returns:
            New amount (positive)

        Raises:
            ValueError: If calculation results in invalid amount
        """
        try:
            current_amount = Decimal(str(current_order.amount))
            new_amount = request.calculate_new_amount(current_amount)

            if new_amount <= 0:
                raise ValueError(f"Calculated new amount is not positive: {new_amount}")

            logger.debug(f"New amount calculated: {new_amount}")
            return new_amount

        except (ValueError, TypeError) as e:
            logger.error(f"Amount calculation failed for order {request.order_id}: {e}")
            raise ValueError(f"Failed to calculate new amount: {e}") from e

    def validate_new_price(self, request: OrderUpdateRequest, current_order: Any) -> float | None:
        """
        Validate and determine the new price for the order.

        Args:
            request: The update request
            current_order: Current order from API

        Returns:
            New price, or None if no price change

        Raises:
            ValueError: If price is invalid
        """
        if request.has_price_update():
            if request.price is None:
                raise ValueError("Price update requested but price is None")
            new_price = float(request.price)
            if new_price <= 0:
                raise ValueError(f"New price must be positive: {new_price}")
            logger.debug(f"New price: ${new_price:.6f}")
            return new_price
        else:
            # Keep existing price
            current_price = float(current_order.price) if current_order.price else None
            logger.debug(
                f"Keeping existing price: ${current_price:.6f}"
                if current_price
                else "No price (market order)"
            )
            return current_price
