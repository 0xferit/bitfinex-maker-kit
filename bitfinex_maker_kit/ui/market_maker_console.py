"""
Console UI for automated market making.

Handles all user interface concerns including output formatting,
user prompts, progress reporting, and order preview display.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MarketMakerUI:
    """
    Console user interface for automated market making.

    Responsibilities:
    - Format and display order previews
    - Handle user confirmation prompts
    - Display progress and status messages
    - Format order tables and summaries
    - Provide consistent console output
    """

    def __init__(
        self,
        symbol: str,
        center_price: float,
        levels: int,
        spread_pct: float,
        size: float,
        side_filter: str | None = None,
    ):
        """
        Initialize market maker UI.

        Args:
            symbol: Trading symbol
            center_price: Center price for orders
            levels: Number of price levels
            spread_pct: Spread percentage per level
            size: Order size
            side_filter: Optional side filter
        """
        self.symbol = symbol
        self.center_price = center_price
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter

    def display_startup_info(self, test_only: bool = False) -> None:
        """Display startup information."""
        print("\n🤖 Starting Auto Market Maker")
        print(f"   Symbol: {self.symbol}")
        print(f"   Initial Center: ${self.center_price:.6f}")
        print(f"   Levels: {self.levels}")
        print(f"   Spread: {self.spread_pct:.3f}%")
        print(f"   Size: {self.size}")
        print("   Order Type: POST-ONLY LIMIT (Maker)")

        if self.side_filter:
            print(f"   Side Filter: {self.side_filter.upper()}-ONLY")

        if test_only:
            print("   Mode: TEST ONLY")

    def display_order_preview(
        self, orders: list[tuple[str, float, float]], title: str = "Orders to place"
    ) -> None:
        """
        Display a preview of orders to be placed.

        Args:
            orders: List of (side, amount, price) tuples
            title: Table title
        """
        # Sort orders by price for better visualization
        sorted_orders = sorted(orders, key=lambda x: x[2])

        print(f"\n📋 {title} (sorted by price):")
        print(f"{'Side':<4} {'Amount':<12} {'Price':<15} {'Distance from Center':<20}")
        print("─" * 55)

        for side, amount, price in sorted_orders:
            distance_pct = ((price - self.center_price) / self.center_price) * 100
            distance_str = f"{distance_pct:+.3f}%"
            print(f"{side.upper():<4} {amount:<12.6f} ${price:<14.6f} {distance_str:<20}")

    def display_order_adjustment_preview(
        self, new_center: float, orders: list[tuple[str, float, float]]
    ) -> None:
        """Display preview of order adjustment."""
        print(f"\n🎯 Adjusting orders to new center price ${new_center:.6f}")
        print(f"   Previous center: ${self.center_price:.6f}")

        # Update center price for distance calculations
        self.center_price = new_center

        # Display new orders
        self.display_order_preview(orders, "New orders to place")

        print()  # Add spacing before placement results

    def confirm_startup(
        self, orders: list[tuple[str, float, float]], test_only: bool = False, yes: bool = False
    ) -> bool:
        """
        Confirm startup with user.

        Args:
            orders: Orders to be placed
            test_only: Test mode flag
            yes: Auto-confirm flag

        Returns:
            True if user confirms, False otherwise
        """
        # Display order preview
        self.display_order_preview(orders, "Initial orders to place")

        # Determine order type description
        order_type = "orders"
        if self.side_filter == "buy":
            order_type = "BUY orders"
        elif self.side_filter == "sell":
            order_type = "SELL orders"

        print("\n⚠️  Auto-market-maker will:")
        print(f"   • Place these {len(orders)} {order_type} (POST-ONLY)")

        if not test_only:
            print("   • Monitor for fills via WebSocket")
            print("   • Automatically adjust center price when orders fill")
            print("   • Replenish cancelled orders every 30 seconds")
            print("   • Continue running until Ctrl+C")
        else:
            print("   • Exit immediately (test mode)")

        if not test_only and not yes:
            response = input("\nDo you want to start auto-market-making? (y/N): ")
            return response.lower() == "y"

        return True

    def display_placement_complete(self, successful_orders: int, total_orders: int) -> None:
        """Display order placement completion."""
        print(f"\n📊 Successfully placed {successful_orders}/{total_orders} orders")

        if successful_orders == 0:
            print("❌ No orders were placed successfully. Exiting.")
        elif successful_orders < total_orders:
            print(f"⚠️  {total_orders - successful_orders} orders failed to place")

    def display_test_complete(self) -> None:
        """Display test mode completion."""
        print("🧪 Test mode - exiting without WebSocket monitoring")
        print("✅ Auto-market-make order placement test successful!")

    def display_websocket_status(self) -> None:
        """Display WebSocket monitoring status."""
        print("\n👂 Listening for order fills... (Press Ctrl+C to stop)")

    def display_replenishment_start(self) -> None:
        """Display replenishment start message."""
        print("🔄 Started periodic order replenishment (every 30 seconds)")

    def display_shutdown_start(self) -> None:
        """Display shutdown start message."""
        print("\n\n🛑 Shutting down market maker...")

    def display_shutdown_complete(self) -> None:
        """Display shutdown completion."""
        print("✅ Auto market maker stopped successfully")

    def log_message(self, message: str, level: str = "info") -> None:
        """
        Log a message with appropriate formatting.

        Args:
            message: Message to display
            level: Message level (info, success, warning, error, debug)
        """
        # Map levels to appropriate display
        if level == "success" or level == "warning" or level == "error" or level == "info":
            print(message)
        elif level == "debug":
            # Only show debug messages if verbose logging
            logger.debug(message)
        else:
            print(message)

    def display_statistics(self, stats: dict[str, Any]) -> None:
        """
        Display order statistics.

        Args:
            stats: Statistics dictionary from OrderManager
        """
        print("\n📊 Order Statistics:")
        print(f"   Total Orders: {stats.get('total_orders', 0)}")
        print(f"   Real Orders: {stats.get('real_orders', 0)}")
        print(f"   Placeholder Orders: {stats.get('placeholder_orders', 0)}")
        print(f"   Buy Orders: {stats.get('buy_orders', 0)}")
        print(f"   Sell Orders: {stats.get('sell_orders', 0)}")
        print(f"   Check Count: {stats.get('check_count', 0)}")

    def display_order_table(self, orders: list[Any], title: str = "Active Orders") -> None:
        """
        Display a formatted table of orders.

        Args:
            orders: List of order objects
            title: Table title
        """
        if not orders:
            print(f"\n{title}: No orders found")
            return

        print(f"\n{title}:")
        print("─" * 80)
        print(f"{'ID':<12} {'Symbol':<10} {'Type':<15} {'Side':<4} {'Amount':<15} {'Price':<15}")
        print("─" * 80)

        for order in orders:
            order_id = getattr(order, "id", "N/A")
            symbol = getattr(order, "symbol", "N/A")
            order_type = getattr(order, "order_type", "N/A")
            amount = getattr(order, "amount", 0)
            side = "BUY" if float(amount) > 0 else "SELL"
            amount_abs = abs(float(amount))
            price = getattr(order, "price", None)
            price_str = f"${float(price):.6f}" if price else "MARKET"

            print(
                f"{order_id:<12} {symbol:<10} {order_type:<15} {side:<4} {amount_abs:<15.6f} {price_str:<15}"
            )

    def format_price_distance(self, price: float, center: float) -> str:
        """
        Format price distance from center.

        Args:
            price: Order price
            center: Center price

        Returns:
            Formatted distance string
        """
        distance_pct = ((price - center) / center) * 100
        return f"{distance_pct:+.3f}%"

    def clear_screen(self) -> None:
        """Clear the console screen (optional)."""
        # Could implement screen clearing if desired
        # For now, just add some spacing
        print("\n" * 2)

    def display_error(self, error: str, context: str = "") -> None:
        """
        Display an error message with context.

        Args:
            error: Error message
            context: Optional context information
        """
        if context:
            print(f"❌ Error in {context}: {error}")
        else:
            print(f"❌ Error: {error}")

    def display_warning(self, warning: str, context: str = "") -> None:
        """
        Display a warning message with context.

        Args:
            warning: Warning message
            context: Optional context information
        """
        if context:
            print(f"⚠️  Warning in {context}: {warning}")
        else:
            print(f"⚠️  Warning: {warning}")
