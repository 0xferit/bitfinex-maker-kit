"""
WebSocket event handlers for real-time market monitoring.

Handles WebSocket connection setup, authentication, and event processing
for the monitoring dashboard.
"""

from typing import Any

from .monitor_display import MonitorDisplay


class MonitorWebSocketHandlers:
    """WebSocket event handlers for market monitoring."""

    def __init__(self, display: MonitorDisplay, symbol: str):
        self.display = display
        self.symbol = symbol

    def setup_websocket_handlers(self, wss: Any) -> None:
        """Set up all WebSocket event handlers."""

        def on_open() -> None:
            self.display.add_event("WebSocket connection established", "CONN")

        async def on_authenticated(data: Any) -> None:
            self.display.connection_stats["authenticated"] = True
            self.display.add_event("WebSocket authenticated", "CONN")

            # Subscribe to required channels after authentication
            channels = [
                {"channel": "ticker", "symbol": self.symbol},
                {"channel": "book", "symbol": self.symbol, "prec": "P0", "freq": "F0", "len": "25"},
                {"channel": "trades", "symbol": self.symbol},
            ]

            for channel_config in channels:
                try:
                    await wss.subscribe(**channel_config)
                    channel_name = channel_config["channel"]
                    self.display.add_event(f"Subscribed to {channel_name} channel", "CONN")
                except Exception as e:
                    self.display.add_event(
                        f"Failed to subscribe to {channel_config['channel']}: {e}", "ERR"
                    )

        def on_ticker_update(subscription: Any, ticker_data: Any) -> None:
            """Handle ticker updates."""
            if ticker_data and hasattr(ticker_data, "__getitem__"):
                try:
                    self.display.connection_stats["ticker_channel"] = True
                    self.display.process_ticker_update(ticker_data)
                except Exception as e:
                    self.display.add_event(f"Error processing ticker: {e}", "ERR")

        def on_book_snapshot(subscription: Any, book_data: Any) -> None:
            """Handle order book snapshot."""
            if book_data:
                try:
                    self.display.connection_stats["book_channel"] = True
                    self.display.process_order_book_snapshot(book_data)
                    self.display.add_event("Order book snapshot received", "BOOK")
                except Exception as e:
                    self.display.add_event(f"Error processing order book snapshot: {e}", "ERR")

        def on_book_update(subscription: Any, book_level: Any) -> None:
            """Handle incremental order book updates."""
            if book_level:
                try:
                    self.display.connection_stats["book_channel"] = True
                    self.display.process_order_book_update(book_level)
                    # Don't log every book update to avoid spam
                except Exception as e:
                    self.display.add_event(f"Error processing book update: {e}", "ERR")

        def on_trades_snapshot(subscription: Any, trades_data: Any) -> None:
            """Handle trades snapshot."""
            if trades_data:
                try:
                    self.display.connection_stats["trades_channel"] = True
                    self.display.process_trades_snapshot(trades_data)
                    self.display.add_event(f"Trades snapshot: {len(trades_data)} trades", "TRADE")
                except Exception as e:
                    self.display.add_event(f"Error processing trades snapshot: {e}", "ERR")

        def on_trade_execution(subscription: Any, trade_data: Any) -> None:
            """Handle individual trade execution."""
            if trade_data:
                try:
                    self.display.connection_stats["trades_channel"] = True
                    self.display.process_trade(trade_data)
                    # Don't log every trade to avoid spam in high-volume periods
                except Exception as e:
                    self.display.add_event(f"Error processing trade: {e}", "ERR")

        def on_trade_execution_update(subscription: Any, trade_data: Any) -> None:
            """Handle trade execution updates."""
            if trade_data:
                try:
                    self.display.process_trade(trade_data)
                except Exception as e:
                    self.display.add_event(f"Error processing trade update: {e}", "ERR")

        def on_disconnected() -> None:
            self.display.add_event("WebSocket disconnected", "DISC")

        def on_auth_order_snapshot(orders_data: Any) -> None:
            """Handle authenticated user orders snapshot."""
            if orders_data:
                try:
                    self.display.process_user_orders_snapshot(orders_data)
                    count = len(orders_data) if hasattr(orders_data, "__len__") else 0
                    self.display.add_event(f"Orders snapshot: {count} orders", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing orders snapshot: {e}", "ERR")

        def on_auth_order_new(order_data: Any) -> None:
            """Handle new authenticated user order."""
            if order_data:
                try:
                    self.display.process_user_order_new(order_data)
                    if hasattr(order_data, "__getitem__") and len(order_data) > 3:
                        symbol = order_data[3] if len(order_data) > 3 else "Unknown"
                        if symbol == self.symbol:
                            self.display.add_event(f"New order: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing new order: {e}", "ERR")

        def on_auth_order_update(order_data: Any) -> None:
            """Handle authenticated user order update."""
            if order_data:
                try:
                    self.display.process_user_order_update(order_data)
                    if hasattr(order_data, "__getitem__") and len(order_data) > 3:
                        symbol = order_data[3] if len(order_data) > 3 else "Unknown"
                        if symbol == self.symbol:
                            self.display.add_event(f"Order updated: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing order update: {e}", "ERR")

        def on_auth_order_cancel(order_data: Any) -> None:
            """Handle authenticated user order cancellation."""
            if order_data:
                try:
                    self.display.process_user_order_cancel(order_data)
                    if hasattr(order_data, "__getitem__") and len(order_data) > 3:
                        symbol = order_data[3] if len(order_data) > 3 else "Unknown"
                        if symbol == self.symbol:
                            self.display.add_event(f"Order cancelled: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing order cancellation: {e}", "ERR")

        # Register all handlers
        wss.on("open", on_open)
        wss.on("authenticated", on_authenticated)

        # Market data handlers
        wss.on("ticker", on_ticker_update)
        wss.on("book_snapshot", on_book_snapshot)
        wss.on("book_update", on_book_update)
        wss.on("trades_snapshot", on_trades_snapshot)
        wss.on("trade_execution", on_trade_execution)
        wss.on("trade_execution_update", on_trade_execution_update)

        # Connection handlers
        wss.on("disconnected", on_disconnected)

        # Authenticated user data handlers
        wss.on("auth_order_snapshot", on_auth_order_snapshot)
        wss.on("auth_order_new", on_auth_order_new)
        wss.on("auth_order_update", on_auth_order_update)
        wss.on("auth_order_cancel", on_auth_order_cancel)
