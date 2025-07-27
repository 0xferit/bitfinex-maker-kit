"""
Cancel-and-recreate order update strategy.

Implements order updates by cancelling the existing order and creating a new one.
This is riskier than atomic updates because there's a possibility of cancelling
an order without being able to recreate it.
"""

import logging
import time
from decimal import Decimal
from typing import Any

from ..utilities.constants import OrderSubmissionError
from .base import OrderUpdateRequest, OrderUpdateResult, OrderUpdateStrategy

logger = logging.getLogger(__name__)


class CancelRecreateStrategy(OrderUpdateStrategy):
    """
    Cancel-and-recreate update strategy.

    Updates an order by cancelling it and creating a new one with the updated
    parameters. This is riskier than atomic updates because of the gap between
    cancellation and recreation where the order doesn't exist.
    """

    def can_handle_request(self, request: OrderUpdateRequest) -> bool:
        """Cancel-recreate can handle any update request."""
        return True

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "Cancel and Recreate"

    def get_risk_level(self) -> str:
        """Cancel-recreate is high risk."""
        return "high"

    def execute_update(
        self, request: OrderUpdateRequest, current_order: Any, client: Any
    ) -> OrderUpdateResult:
        """
        Execute update by cancelling and recreating the order.

        Steps:
        1. Validate parameters
        2. Cancel the original order
        3. Wait briefly to ensure cancellation processes
        4. Create new order with updated parameters
        5. Return result with new order information
        """
        # Calculate new values
        is_sell_order = float(current_order.amount) < 0
        current_price = float(current_order.price) if current_order.price else None

        new_price = float(request.price) if request.price else current_price
        new_amount = float(request.calculate_new_amount(Decimal(str(current_order.amount))))

        # Validate that we have a valid price
        if new_price is None:
            return OrderUpdateResult(
                success=False,
                method="validation_error",
                order_id=request.order_id,
                message="Cannot update order: no price specified and current order has no price",
            )

        symbol = current_order.symbol
        side = "sell" if is_sell_order else "buy"

        logger.info(f"Starting cancel-and-recreate for order {request.order_id}")
        logger.debug(
            f"Original: {side.upper()} {abs(float(current_order.amount))} @ ${current_price}"
        )
        logger.debug(f"New: {side.upper()} {new_amount} @ ${new_price:.6f}")

        try:
            # Step 1: Validate inputs
            self._validate_recreation_parameters(symbol, side, new_amount, new_price)

            # Step 2: Cancel the original order
            cancel_result = self._cancel_original_order(request.order_id, client)
            if not cancel_result:
                raise OrderSubmissionError("Failed to cancel original order")

            # Step 3: Create new order
            new_order = self._create_new_order(symbol, side, new_amount, new_price, client)

            return OrderUpdateResult(
                success=True,
                method="cancel_recreate",
                order_id=request.order_id,
                message=f"Order {request.order_id} cancelled and recreated with new parameters",
                response_data={"new_order": new_order},
                new_order_id=getattr(new_order, "id", None),
            )

        except Exception as e:
            logger.error(f"Cancel-and-recreate failed for order {request.order_id}: {e}")
            return OrderUpdateResult(
                success=False,
                method="cancel_recreate",
                order_id=request.order_id,
                message=f"Cancel-and-recreate update failed: {e}",
            )

    def _validate_recreation_parameters(
        self, symbol: str, side: str, amount: float, price: float
    ) -> None:
        """Validate parameters before attempting recreation."""
        if not symbol or not symbol.strip():
            raise ValueError(f"Invalid symbol: {symbol}")

        if amount <= 0:
            raise ValueError(f"Amount must be positive, got: {amount}")

        if price <= 0:
            raise ValueError(f"Price must be positive, got: {price}")

        if side.lower() not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}")

    def _cancel_original_order(self, order_id: int, client: Any) -> bool:
        """Cancel the original order with retry logic."""
        max_retries = 3
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                # Add delay before cancellation to prevent nonce issues
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.debug(f"Retry {attempt}, waiting {delay}s before cancel attempt")
                    time.sleep(delay)
                else:
                    time.sleep(base_delay)

                logger.debug(f"Cancelling original order {order_id} (attempt {attempt + 1})")
                client.cancel_order(order_id)

                logger.info(f"Successfully cancelled order {order_id}")
                return True

            except Exception as e:
                error_msg = str(e).lower()

                if "not found" in error_msg:
                    # Order already cancelled or filled
                    logger.warning(f"Order {order_id} not found (may be already cancelled/filled)")
                    return True
                elif "nonce" in error_msg and "small" in error_msg and attempt < max_retries - 1:
                    # Nonce error, retry with longer delay
                    logger.warning(f"Nonce error on cancel attempt {attempt + 1}, will retry")
                    continue
                else:
                    # Other error or final attempt
                    if attempt == max_retries - 1:
                        raise OrderSubmissionError(
                            f"Failed to cancel order after {max_retries} attempts: {e}"
                        ) from e
                    else:
                        logger.warning(f"Cancel attempt {attempt + 1} failed: {e}")

        return False

    def _create_new_order(
        self, symbol: str, side: str, amount: float, price: float, client: Any
    ) -> Any:
        """Create the new order with retry logic."""
        max_retries = 3
        base_delay = 1.0

        # Add delay between cancel and recreate to prevent nonce issues
        time.sleep(base_delay)

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (1.5**attempt)  # Exponential backoff
                    logger.debug(f"Retry {attempt}, waiting {delay}s before create attempt")
                    time.sleep(delay)

                logger.debug(
                    f"Creating new order: {side.upper()} {amount} @ ${price:.6f} (attempt {attempt + 1})"
                )

                # Submit new order with same flags (POST_ONLY preserved through client wrapper)
                new_order = client.submit_order(symbol, side, amount, price)

                logger.info(
                    f"Successfully created new order: {side.upper()} {amount} @ ${price:.6f}"
                )
                return new_order

            except Exception as e:
                error_msg = str(e).lower()

                if "nonce" in error_msg and "small" in error_msg and attempt < max_retries - 1:
                    # Nonce error, retry with longer delay
                    logger.warning(f"Nonce error on create attempt {attempt + 1}, will retry")
                    continue
                else:
                    # Other error or final attempt
                    if attempt == max_retries - 1:
                        raise OrderSubmissionError(
                            f"Order recreation failed after {max_retries} attempts: {e}"
                        ) from e
                    else:
                        logger.warning(f"Create attempt {attempt + 1} failed: {e}")

        raise OrderSubmissionError("Failed to create new order after all retries")
