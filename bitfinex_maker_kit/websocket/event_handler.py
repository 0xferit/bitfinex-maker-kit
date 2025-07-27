"""
WebSocket event handler for automated market making.

Handles real-time order updates, fills, and other WebSocket events,
separated from business logic and UI concerns for better testability.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from ..bitfinex_client import Notification, Order

logger = logging.getLogger(__name__)


class WebSocketEventHandler:
    """
    Handles WebSocket events for automated market making.

    Responsibilities:
    - Setup WebSocket event handlers
    - Process order updates and fills
    - Trigger order adjustments based on fills
    - Handle authentication and notifications
    - Provide callbacks to business logic layer
    """

    def __init__(self, order_manager: Any, client: Any):
        """
        Initialize WebSocket event handler.

        Args:
            order_manager: OrderManager instance for order tracking
            client: Bitfinex client with WebSocket access
        """
        self.order_manager = order_manager
        self.client = client

        # Callback functions (set by orchestrator)
        self.on_order_fill_callback: Callable | None = None
        self.on_order_cancelled_callback: Callable | None = None
        self.ui_callback: Callable | None = None

        # Event tracking
        self._authenticated = False
        self._handlers_setup = False

    def setup_handlers(self) -> None:
        """Setup all WebSocket event handlers."""
        if self._handlers_setup:
            logger.warning("WebSocket handlers already setup")
            return

        wss = self.client.wss

        # Order update handler
        @wss.on("order_update")
        def on_order_update(order: Order) -> None:
            self._handle_order_update(order)

        # New order handler
        @wss.on("order_new")
        def on_order_new(order: Order) -> None:
            self._handle_order_new(order)

        # Authentication handler
        @wss.on("authenticated")
        async def on_authenticated(_: Any) -> None:
            self._handle_authenticated()

        # Notification handler
        @wss.on("on-req-notification")
        def on_notification(notification: Notification) -> None:
            self._handle_notification(notification)

        self._handlers_setup = True
        logger.info("WebSocket event handlers setup complete")

    def _handle_order_update(self, order: Order) -> None:
        """Handle order update events."""
        order_id = order.id

        # Check if this is one of our tracked orders
        original_order = self.order_manager.order_tracker.get_tracked_order(order_id)
        if not original_order:
            # Not our order, ignore
            return

        try:
            if "EXECUTED" in order.order_status:
                self._handle_order_execution(order, original_order)
            elif "PARTIALLY FILLED" in order.order_status:
                self._handle_partial_fill(order, original_order)
            elif "CANCELED" in order.order_status:
                self._handle_order_cancellation(order, original_order)
        except Exception as e:
            logger.error(f"Error handling order update for order {order_id}: {e}")
            if self.ui_callback:
                self.ui_callback(f"❌ Error processing order update: {e}", "error")

    def _handle_order_execution(self, order: Order, original_order: dict[str, Any]) -> None:
        """Handle full order execution."""
        fill_price = float(order.price)

        if self.ui_callback:
            self.ui_callback(
                f"🎉 Our order FULLY EXECUTED! {original_order['side'].upper()} {original_order['amount']} @ ${fill_price:.6f}",
                "success",
            )

        # Remove from tracking
        self.order_manager.remove_order_from_tracking(order.id)

        # Trigger order adjustment callback
        if self.on_order_fill_callback:
            try:
                task = asyncio.create_task(self.on_order_fill_callback(fill_price, "full"))
                # Store reference to prevent garbage collection
                if not hasattr(self, "_callback_tasks"):
                    self._callback_tasks = set()
                self._callback_tasks.add(task)
                task.add_done_callback(self._callback_tasks.discard)
            except Exception as e:
                logger.error(f"Error in order fill callback: {e}")

        logger.info(f"Order {order.id} fully executed at ${fill_price:.6f}")

    def _handle_partial_fill(self, order: Order, original_order: dict[str, Any]) -> None:
        """Handle partial order fill."""
        remaining = abs(float(order.amount))
        filled_amount = original_order["amount"] - remaining
        fill_price = float(order.price)

        if self.ui_callback:
            self.ui_callback(
                f"📊 Our order PARTIALLY FILLED! {original_order['side'].upper()} {filled_amount:.1f}/{original_order['amount']} @ ${fill_price:.6f}",
                "info",
            )
            self.ui_callback(f"   Remaining: {remaining:.1f}", "info")

        # Check if significant fill (50% or more)
        fill_percentage = filled_amount / original_order["amount"]

        if fill_percentage >= 0.5:  # 50% or more filled
            if self.ui_callback:
                self.ui_callback("   🎯 Significant fill (≥50%) - adjusting center price", "info")

            # Trigger order adjustment callback
            if self.on_order_fill_callback:
                try:
                    task = asyncio.create_task(
                        self.on_order_fill_callback(fill_price, "significant")
                    )
                    # Store reference to prevent garbage collection
                    if not hasattr(self, "_callback_tasks"):
                        self._callback_tasks = set()
                    self._callback_tasks.add(task)
                    task.add_done_callback(self._callback_tasks.discard)
                except Exception as e:
                    logger.error(f"Error in order fill callback: {e}")
        else:
            if self.ui_callback:
                self.ui_callback("   ⏳ Waiting for more fills before adjusting", "info")

        logger.info(
            f"Order {order.id} partially filled: {filled_amount:.1f}/{original_order['amount']} at ${fill_price:.6f}"
        )

    def _handle_order_cancellation(self, order: Order, original_order: dict[str, Any]) -> None:
        """Handle order cancellation."""
        if self.ui_callback:
            self.ui_callback(f"❌ Our order {order.id} was cancelled", "warning")

        # Remove from tracking
        self.order_manager.remove_order_from_tracking(order.id)

        # Trigger cancellation callback
        if self.on_order_cancelled_callback:
            try:
                self.on_order_cancelled_callback(order.id, original_order)
            except Exception as e:
                logger.error(f"Error in order cancellation callback: {e}")

        logger.info(f"Order {order.id} was cancelled")

    def _handle_order_new(self, order: Order) -> None:
        """Handle new order creation events."""
        if self.ui_callback:
            self.ui_callback(f"🆕 New order created: {order.id}", "debug")

        logger.debug(f"New order created: {order.id}")

    def _handle_authenticated(self) -> None:
        """Handle WebSocket authentication."""
        self._authenticated = True

        if self.ui_callback:
            self.ui_callback("✅ WebSocket authenticated - monitoring order fills", "success")

        logger.info("WebSocket authenticated successfully")

    def _handle_notification(self, notification: Notification) -> None:
        """Handle general notifications."""
        if notification.status == "ERROR":
            if self.ui_callback:
                self.ui_callback(f"❌ Order error: {notification.text}", "error")

            logger.error(f"WebSocket notification error: {notification.text}")
        else:
            logger.debug(f"WebSocket notification: {notification.text}")

    def set_order_fill_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback for order fills.

        Args:
            callback: Function to call when orders are filled.
                     Signature: callback(fill_price: float, fill_type: str)
        """
        self.on_order_fill_callback = callback

    def set_order_cancelled_callback(self, callback: Callable[[Any, dict], None]) -> None:
        """
        Set callback for order cancellations.

        Args:
            callback: Function to call when orders are cancelled.
                     Signature: callback(order_id: Any, order_info: Dict)
        """
        self.on_order_cancelled_callback = callback

    def set_ui_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Set callback for UI updates.

        Args:
            callback: Function to call for UI updates.
                     Signature: callback(message: str, level: str)
        """
        self.ui_callback = callback

    def is_authenticated(self) -> bool:
        """Check if WebSocket is authenticated."""
        return self._authenticated

    def is_setup(self) -> bool:
        """Check if handlers are setup."""
        return self._handlers_setup

    def get_connection_info(self) -> dict[str, Any]:
        """
        Get information about the WebSocket connection.

        Returns:
            Dictionary with connection information
        """
        return {
            "authenticated": self._authenticated,
            "handlers_setup": self._handlers_setup,
            "client_available": self.client is not None,
            "wss_available": hasattr(self.client, "wss") if self.client else False,
        }
