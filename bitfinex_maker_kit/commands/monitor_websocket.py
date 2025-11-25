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
            """Handle ticker updates. Receives TradingPairTicker dataclass."""
            if ticker_data:
                try:
                    self.display.connection_stats["ticker_channel"] = True
                    self.display.process_ticker_update(ticker_data)
                except Exception as e:
                    self.display.add_event(f"Error processing ticker: {e}", "ERR")

        def on_book_snapshot(subscription: Any, book_data: Any) -> None:
            """Handle order book snapshot. Receives list of TradingPairBook dataclasses."""
            if book_data:
                try:
                    self.display.connection_stats["book_channel"] = True
                    self.display.process_order_book_snapshot(book_data)
                    self.display.add_event("Order book snapshot received", "BOOK")
                except Exception as e:
                    self.display.add_event(f"Error processing order book snapshot: {e}", "ERR")

        def on_book_update(subscription: Any, book_level: Any) -> None:
            """Handle incremental order book updates. Receives TradingPairBook dataclass."""
            if book_level:
                try:
                    self.display.connection_stats["book_channel"] = True
                    self.display.process_order_book_update(book_level)
                except Exception as e:
                    self.display.add_event(f"Error processing book update: {e}", "ERR")

        def on_trades_snapshot(subscription: Any, trades_data: Any) -> None:
            """Handle trades snapshot. Receives list of TradingPairTrade dataclasses."""
            if trades_data:
                try:
                    self.display.connection_stats["trades_channel"] = True
                    self.display.process_trades_snapshot(trades_data)
                    self.display.add_event(f"Trades snapshot: {len(trades_data)} trades", "TRADE")
                except Exception as e:
                    self.display.add_event(f"Error processing trades snapshot: {e}", "ERR")

        def on_trade_execution(subscription: Any, trade_data: Any) -> None:
            """Handle individual trade execution. Receives TradingPairTrade dataclass."""
            if trade_data:
                try:
                    self.display.connection_stats["trades_channel"] = True
                    self.display.process_trade(trade_data)
                except Exception as e:
                    self.display.add_event(f"Error processing trade: {e}", "ERR")

        def on_trade_execution_update(subscription: Any, trade_data: Any) -> None:
            """Handle trade execution updates. Receives TradingPairTrade dataclass."""
            if trade_data:
                try:
                    self.display.process_trade(trade_data)
                except Exception as e:
                    self.display.add_event(f"Error processing trade update: {e}", "ERR")

        def on_disconnected() -> None:
            self.display.add_event("WebSocket disconnected", "DISC")

        def on_order_snapshot(orders_data: Any) -> None:
            """Handle user orders snapshot. Receives list of Order dataclasses."""
            if orders_data:
                try:
                    self.display.process_user_orders_snapshot(orders_data)
                    count = len(orders_data) if hasattr(orders_data, "__len__") else 0
                    self.display.add_event(f"Orders snapshot: {count} orders", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing orders snapshot: {e}", "ERR")

        def on_order_new(order_data: Any) -> None:
            """Handle new user order. Receives Order dataclass."""
            if order_data:
                try:
                    self.display.process_user_order_new(order_data)
                    symbol = getattr(order_data, "symbol", "Unknown")
                    if symbol == self.symbol:
                        self.display.add_event(f"New order: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing new order: {e}", "ERR")

        def on_order_update(order_data: Any) -> None:
            """Handle user order update. Receives Order dataclass."""
            if order_data:
                try:
                    self.display.process_user_order_update(order_data)
                    symbol = getattr(order_data, "symbol", "Unknown")
                    if symbol == self.symbol:
                        self.display.add_event(f"Order updated: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing order update: {e}", "ERR")

        def on_order_cancel(order_data: Any) -> None:
            """Handle user order cancellation. Receives Order dataclass."""
            if order_data:
                try:
                    self.display.process_user_order_cancel(order_data)
                    symbol = getattr(order_data, "symbol", "Unknown")
                    if symbol == self.symbol:
                        self.display.add_event(f"Order cancelled: {symbol}", "ORDER")
                except Exception as e:
                    self.display.add_event(f"Error processing order cancellation: {e}", "ERR")

        # Register all handlers
        wss.on("open", on_open)
        wss.on("authenticated", on_authenticated)

        # Market data handlers (use t_ prefix for trading pairs)
        wss.on("t_ticker_update", on_ticker_update)
        wss.on("t_book_snapshot", on_book_snapshot)
        wss.on("t_book_update", on_book_update)
        wss.on("t_trades_snapshot", on_trades_snapshot)
        wss.on("t_trade_execution", on_trade_execution)
        wss.on("t_trade_execution_update", on_trade_execution_update)

        # Connection handlers
        wss.on("disconnected", on_disconnected)

        # Authenticated user data handlers
        wss.on("order_snapshot", on_order_snapshot)
        wss.on("order_new", on_order_new)
        wss.on("order_update", on_order_update)
        wss.on("order_cancel", on_order_cancel)
