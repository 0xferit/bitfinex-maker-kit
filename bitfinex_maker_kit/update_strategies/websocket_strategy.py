"""
WebSocket-based atomic order update strategy.

Implements atomic order updates using WebSocket or REST API, which is safer
than cancel-and-recreate because the order is either updated successfully
or remains unchanged.
"""

import json
import logging
import time
from decimal import Decimal
from typing import Any

from ..utilities.constants import OrderSubmissionError
from .base import OrderUpdateRequest, OrderUpdateResult, OrderUpdateStrategy

logger = logging.getLogger(__name__)


class WebSocketUpdateStrategy(OrderUpdateStrategy):
    """
    WebSocket atomic update strategy.

    Uses REST API update_order method (preferred) or WebSocket atomic updates
    as fallback. This approach is safer than cancel-and-recreate because
    the order is either updated successfully or remains unchanged.
    """

    def can_handle_request(self, request: OrderUpdateRequest) -> bool:
        """WebSocket strategy can handle any update request."""
        return True

    def get_strategy_name(self) -> str:
        """Get strategy name."""
        return "WebSocket Atomic Update"

    def get_risk_level(self) -> str:
        """WebSocket updates are low risk."""
        return "low"

    def execute_update(
        self, request: OrderUpdateRequest, current_order: Any, client: Any
    ) -> OrderUpdateResult:
        """
        Execute atomic update using REST API or WebSocket.

        Tries multiple approaches in order of preference:
        1. REST API update_order method (most reliable)
        2. WebSocket API update method
        3. Direct WebSocket message (requires active connection)
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

        # Convert amount for Bitfinex API (negative for sell orders)
        bitfinex_amount = -new_amount if is_sell_order else new_amount

        logger.info(f"Attempting atomic update for order {request.order_id}")
        logger.debug(f"New price: ${new_price:.6f}, New amount: {new_amount}")

        # Try REST API first
        rest_result = self._try_rest_update(request.order_id, new_price, bitfinex_amount, client)
        if rest_result.success:
            return rest_result

        # Fallback to WebSocket
        return self._try_websocket_update(request.order_id, new_price, bitfinex_amount, client)

    def _try_rest_update(
        self, order_id: int, price: float, amount: float, client: Any
    ) -> OrderUpdateResult:
        """Try updating via REST API."""
        try:
            if hasattr(client.client.rest.auth, "update_order"):
                logger.debug("Using REST API atomic update")
                result = client.client.rest.auth.update_order(
                    id=order_id, price=price, amount=amount
                )

                return OrderUpdateResult(
                    success=True,
                    method="rest_atomic",
                    order_id=order_id,
                    message=f"Order {order_id} updated via REST API",
                    response_data={"result": result},
                )
            else:
                return OrderUpdateResult(
                    success=False,
                    method="rest_atomic",
                    order_id=order_id,
                    message="REST API update_order method not available",
                )

        except Exception as e:
            logger.warning(f"REST API update failed: {e}")
            return OrderUpdateResult(
                success=False,
                method="rest_atomic",
                order_id=order_id,
                message=f"REST API update failed: {e}",
            )

    def _try_websocket_update(
        self, order_id: int, price: float, amount: float, client: Any
    ) -> OrderUpdateResult:
        """Try updating via WebSocket."""
        try:
            wss = client.client.wss

            # Try using library's built-in WebSocket update method
            if hasattr(wss, "update_order"):
                logger.debug("Using WebSocket API atomic update")
                result = wss.update_order(id=order_id, price=str(price), amount=str(amount))

                return OrderUpdateResult(
                    success=True,
                    method="websocket_atomic",
                    order_id=order_id,
                    message=f"Order {order_id} updated via WebSocket API",
                    response_data={"result": result},
                )
            else:
                # Try direct WebSocket message
                return self._try_direct_websocket_message(order_id, price, amount, wss)

        except Exception as e:
            logger.error(f"WebSocket update failed: {e}")
            return self._create_failure_result(order_id, e)

    def _try_direct_websocket_message(
        self, order_id: int, price: float, amount: float, wss: Any
    ) -> OrderUpdateResult:
        """Try sending direct WebSocket message."""
        try:
            # Check if we have an active WebSocket connection
            is_connected = self._check_websocket_connection(wss)

            if not is_connected:
                raise OrderSubmissionError("No WebSocket connection available")

            logger.debug("Using direct WebSocket message")

            # Send the update message directly
            update_data = {"id": order_id, "price": str(price), "amount": str(amount)}

            update_message = [0, "ou", None, update_data]

            if hasattr(wss, "send"):
                wss.send(json.dumps(update_message))
            elif hasattr(wss, "_send_message"):
                wss._send_message(update_message)
            else:
                raise OrderSubmissionError("WebSocket send method not available")

            # Brief wait for processing
            time.sleep(2)

            return OrderUpdateResult(
                success=True,
                method="websocket_direct",
                order_id=order_id,
                message=f"Order {order_id} update message sent via direct WebSocket",
                response_data={"update_data": update_data},
            )

        except Exception as e:
            logger.error(f"Direct WebSocket message failed: {e}")
            return self._create_failure_result(order_id, e)

    def _check_websocket_connection(self, wss: Any) -> bool:
        """Check if WebSocket connection is active."""
        try:
            if hasattr(wss, "is_open") and callable(wss.is_open):
                result = wss.is_open()
                return bool(result)  # Ensure we return a bool
            elif hasattr(wss, "_connected"):
                return bool(wss._connected)
            elif hasattr(wss, "connected"):
                return bool(wss.connected)
        except Exception:
            pass  # nosec B110 - Expected behavior: gracefully handle any websocket state check errors

        return False

    def _create_failure_result(self, order_id: int, error: Exception) -> OrderUpdateResult:
        """Create a failure result with helpful error message."""
        error_msg = str(error)

        # Provide helpful suggestions based on error type
        if "not available" in error_msg.lower() or "connection" in error_msg.lower():
            message = (
                f"Atomic update failed: {error}\n"
                "   💡 This may be due to API limitations or connection issues\n"
                "   💡 Suggestion: Use --use-cancel-recreate flag as an alternative"
            )
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            message = (
                f"Atomic update failed: {error}\n"
                "   💡 Rate limited - wait 15 seconds and try again\n"
                "   💡 Or use --use-cancel-recreate flag as an alternative"
            )
        else:
            message = (
                f"Atomic update failed: {error}\n"
                "   💡 Suggestion: Use --use-cancel-recreate flag as an alternative"
            )

        return OrderUpdateResult(
            success=False, method="websocket_atomic", order_id=order_id, message=message
        )
