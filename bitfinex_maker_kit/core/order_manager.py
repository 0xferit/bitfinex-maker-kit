"""
Order management for automated market making.

Handles the lifecycle of orders including generation, placement, tracking,
cancellation, and replenishment. Extracted from AutoMarketMaker to provide
focused order management without UI or WebSocket concerns.
"""

import logging
from collections.abc import Callable
from typing import Any

from ..utilities.orders import submit_order
from ..utilities.response_parser import OrderTracker

logger = logging.getLogger(__name__)


class OrderManager:
    """
    Manages the complete lifecycle of market making orders.

    Responsibilities:
    - Generate orders based on market making parameters
    - Place initial orders and track responses
    - Cancel all tracked orders
    - Check for cancelled orders and replenish them
    - Maintain order state and tracking
    """

    def __init__(
        self,
        symbol: str,
        levels: int,
        spread_pct: float,
        size: float,
        side_filter: str | None = None,
        client: Any = None,
    ) -> None:
        """
        Initialize order manager.

        Args:
            symbol: Trading symbol
            levels: Number of price levels on each side
            spread_pct: Spread percentage per level
            size: Order size for each level
            side_filter: Optional side filter ('buy' or 'sell')
            client: Bitfinex client for API operations
        """
        self.symbol = symbol
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter
        self.client = client

        # Order tracking
        self.order_tracker = OrderTracker()

        # Statistics
        self._check_count = 0

    def generate_orders(self, center_price: float) -> list[tuple[str, float, float]]:
        """
        Generate order list for current center price.

        Args:
            center_price: Center price for order generation

        Returns:
            List of (side, amount, price) tuples
        """
        orders = []

        for i in range(1, self.levels + 1):
            # Buy orders below center price
            if self.side_filter != "sell":
                buy_price = center_price * (1 - (self.spread_pct * i / 100))
                orders.append(("buy", self.size, buy_price))

            # Sell orders above center price
            if self.side_filter != "buy":
                sell_price = center_price * (1 + (self.spread_pct * i / 100))
                orders.append(("sell", self.size, sell_price))

        logger.debug(f"Generated {len(orders)} orders around center price ${center_price:.6f}")
        return orders

    def place_initial_orders(
        self, center_price: float, ui_callback: Callable[[str, str], None] | None = None
    ) -> int:
        """
        Place initial set of orders.

        Args:
            center_price: Center price for order placement
            ui_callback: Optional callback for UI updates (ui_callback(message, level))

        Returns:
            Number of orders successfully placed
        """
        if ui_callback:
            ui_callback(
                f"🚀 Placing initial orders around center price ${center_price:.6f}", "info"
            )

        orders_to_place = self.generate_orders(center_price)
        orders_to_place.sort(key=lambda x: x[2])  # Sort by price

        successful_orders = 0

        for side, amount, price in orders_to_place:
            try:
                # Use centralized order submission function
                response = submit_order(self.symbol, side, amount, price)

                if ui_callback:
                    ui_callback(
                        f"✅ {side.upper()} POST-ONLY order placed: {amount} @ ${price:.6f}",
                        "success",
                    )

                # Use centralized order tracking
                order_id = self.order_tracker.track_order_from_response(
                    response, side, amount, price, self.symbol
                )

                if ui_callback:
                    ui_callback(f"📋 Tracking order ID: {order_id}", "debug")

                successful_orders += 1

            except Exception as e:
                if "would have matched" in str(e).lower():
                    if ui_callback:
                        ui_callback(
                            f"⚠️  {side.upper()} POST-ONLY order @ ${price:.6f} cancelled (would have matched existing order)",
                            "warning",
                        )
                else:
                    if ui_callback:
                        ui_callback(f"❌ Failed to place {side.upper()} order: {e}", "error")
                    logger.error(f"Failed to place {side} order at ${price:.6f}: {e}")

        logger.info(f"Successfully placed {successful_orders}/{len(orders_to_place)} orders")
        return successful_orders

    def cancel_all_orders(self, ui_callback: Callable[[str, str], None] | None = None) -> None:
        """
        Cancel all tracked orders.

        Args:
            ui_callback: Optional callback for UI updates
        """
        tracked_orders = self.order_tracker.get_all_tracked_orders()
        if not tracked_orders:
            return

        if ui_callback:
            ui_callback(f"🗑️  Cancelling {len(tracked_orders)} tracked orders...", "info")

        # Extract order IDs for bulk cancellation (excluding placeholder IDs)
        order_ids = []
        placeholder_count = 0

        for order_id, order_info in tracked_orders.items():
            if order_info.get("is_placeholder", False):
                # This is a placeholder ID, can't cancel via API
                placeholder_count += 1
            else:
                # This is a real order ID
                order_ids.append(order_id)

        # Cancel real orders using bulk API
        if order_ids and self.client:
            try:
                self.client.cancel_order_multi(order_ids)
                if ui_callback:
                    ui_callback(
                        f"✅ Successfully submitted bulk cancellation for {len(order_ids)} orders",
                        "success",
                    )
                logger.info(f"Successfully cancelled {len(order_ids)} orders")
            except Exception as e:
                if ui_callback:
                    ui_callback(f"❌ Failed to cancel orders in bulk: {e}", "error")
                logger.error(f"Failed to cancel orders in bulk: {e}")

        # Handle placeholder orders (just remove from tracking)
        if placeholder_count > 0 and ui_callback:
            ui_callback(f"🧹 Removing {placeholder_count} placeholder orders from tracking", "info")

        # Clear all tracking
        self.order_tracker.clear_all_tracked_orders()
        if ui_callback:
            ui_callback("🧹 Order tracking cleared", "info")

        logger.info("All orders cancelled and tracking cleared")

    def check_and_replenish_orders(
        self, ui_callback: Callable[[str, str], None] | None = None
    ) -> int:
        """
        Check for cancelled orders and replenish them.

        Args:
            ui_callback: Optional callback for UI updates

        Returns:
            Number of orders replenished
        """
        tracked_orders = self.order_tracker.get_all_tracked_orders()
        if not tracked_orders:
            return 0

        if not self.client:
            logger.warning("No client available for order replenishment")
            return 0

        try:
            # Get current active orders from exchange
            all_orders = self.client.get_orders()
            current_orders = [order for order in all_orders if order.symbol == self.symbol]

            # Create set of currently active order IDs on exchange
            active_order_ids = {order.id for order in current_orders}

            # Find orders that we're tracking but are no longer active
            missing_orders = []
            for order_id, order_info in list(tracked_orders.items()):
                # Skip placeholder orders - they can't be checked on exchange
                if order_info.get("is_placeholder", False):
                    continue

                if order_id not in active_order_ids:
                    missing_orders.append((order_id, order_info))
                    # Remove from our tracking
                    self.order_tracker.remove_tracked_order(order_id)

            if missing_orders:
                if ui_callback:
                    ui_callback(
                        f"🔄 Found {len(missing_orders)} cancelled orders - replenishing...", "info"
                    )

                replenished_count = 0

                # Replenish each missing order
                for _order_id, order_info in missing_orders:
                    side = order_info["side"]
                    amount = order_info["amount"]
                    price = order_info["price"]

                    if ui_callback:
                        ui_callback(
                            f"   Replenishing {side.upper()} order: {amount} @ ${price:.6f}", "info"
                        )

                    try:
                        # Use centralized order submission function
                        response = submit_order(self.symbol, side, amount, price)

                        # Use centralized order tracking
                        new_order_id = self.order_tracker.track_order_from_response(
                            response, side, amount, price, self.symbol
                        )

                        if ui_callback:
                            ui_callback(
                                f"   ✅ Replenished: {side.upper()} POST-ONLY {amount} @ ${price:.6f} (ID: {new_order_id})",
                                "success",
                            )

                        replenished_count += 1

                    except Exception as e:
                        if "would have matched" in str(e).lower():
                            if ui_callback:
                                ui_callback(
                                    f"   ⚠️  {side.upper()} POST-ONLY replenishment @ ${price:.6f} cancelled (would have matched existing order)",
                                    "warning",
                                )
                        else:
                            if ui_callback:
                                ui_callback(
                                    f"   ❌ Failed to replenish {side.upper()} order: {e}", "error"
                                )
                            logger.error(f"Failed to replenish {side} order at ${price:.6f}: {e}")

                logger.info(f"Replenished {replenished_count}/{len(missing_orders)} orders")
                return replenished_count
            else:
                # Only show status occasionally to avoid spam
                self._check_count += 1
                if self._check_count % 10 == 0:  # Every 10th check (5 minutes)
                    tracked_count = len(tracked_orders)
                    if ui_callback:
                        ui_callback(
                            f"✅ Order check #{self._check_count}: All {tracked_count} orders still active",
                            "info",
                        )

                return 0

        except Exception as e:
            if ui_callback:
                ui_callback(f"❌ Error during order replenishment: {e}", "error")
            logger.error(f"Error during order replenishment: {e}")
            return 0

    def get_order_count(self) -> int:
        """Get the number of currently tracked orders."""
        return len(self.order_tracker.get_all_tracked_orders())

    def get_tracked_orders(self) -> dict[Any, dict[str, Any]]:
        """Get all currently tracked orders."""
        return self.order_tracker.get_all_tracked_orders()

    def is_order_tracked(self, order_id: Any) -> bool:
        """Check if an order is currently being tracked."""
        return self.order_tracker.get_tracked_order(order_id) is not None

    def remove_order_from_tracking(self, order_id: Any) -> bool:
        """
        Remove a specific order from tracking.

        Args:
            order_id: Order ID to remove

        Returns:
            True if order was found and removed
        """
        return self.order_tracker.remove_tracked_order(order_id)

    def get_order_statistics(self) -> dict[str, Any]:
        """
        Get statistics about managed orders.

        Returns:
            Dictionary with order statistics
        """
        tracked_orders = self.order_tracker.get_all_tracked_orders()

        stats = {
            "total_orders": len(tracked_orders),
            "real_orders": 0,
            "placeholder_orders": 0,
            "buy_orders": 0,
            "sell_orders": 0,
            "check_count": self._check_count,
        }

        for order_info in tracked_orders.values():
            if order_info.get("is_placeholder", False):
                stats["placeholder_orders"] += 1
            else:
                stats["real_orders"] += 1

            if order_info.get("side") == "buy":
                stats["buy_orders"] += 1
            elif order_info.get("side") == "sell":
                stats["sell_orders"] += 1

        return stats
