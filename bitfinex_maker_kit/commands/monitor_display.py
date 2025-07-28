"""
Display management for real-time market monitoring.

Handles terminal output, data formatting, and live updates
for the monitoring dashboard.
"""

import time
from collections import deque
from datetime import datetime
from typing import Any

from .. import __version__
from ..bitfinex_client import BitfinexClientWrapper


class OrderData:
    """Simple order data class for WebSocket order processing."""

    def __init__(self, id: int, symbol: str, amount: float, price: float, status: str):
        self.id = id
        self.symbol = symbol
        self.amount = amount  # positive = buy, negative = sell
        self.price = price
        self.status = status


class MonitorDisplay:
    """
    Real-time display manager for market monitoring.

    Handles terminal output, data formatting, and live updates
    for the monitoring dashboard.
    """

    def __init__(self, symbol: str, levels: int = 40, api_key: str = ""):
        """Initialize display with configuration."""
        self.symbol = symbol
        self.levels = levels
        self.start_time = time.time()
        self.api_key = api_key

        # Get terminal dimensions for responsive layout - try multiple methods
        try:
            import subprocess  # nosec B404

            cols_result = subprocess.run(["tput", "cols"], capture_output=True, text=True)  # nosec B603, B607
            lines_result = subprocess.run(["tput", "lines"], capture_output=True, text=True)  # nosec B603, B607
            self.terminal_width = (
                int(cols_result.stdout.strip()) if cols_result.returncode == 0 else 200
            )
            self.terminal_height = (
                int(lines_result.stdout.strip()) if lines_result.returncode == 0 else 50
            )
        except Exception:
            self.terminal_width = 200  # Default to wider display
            self.terminal_height = 50  # Default height

        # Ensure minimum width and reasonable maximum
        self.terminal_width = max(120, min(self.terminal_width, 300))
        self.terminal_height = max(25, min(self.terminal_height, 100))

        # Extract base currency from symbol (e.g., tBTCUSD -> BTC, tUSDCUSD -> USDC)
        if symbol.startswith("t") and symbol.endswith("USD"):
            # Handle all USD pairs: tBTCUSD -> BTC, tUSDCUSD -> USDC, tADAUSD -> ADA
            self.base_currency = symbol[1:-3]  # Remove 't' prefix and 'USD' suffix
        elif symbol.startswith("t") and len(symbol) >= 4:
            # Fallback for other formats: take everything after 't' and before quote currency
            self.base_currency = symbol[1:4]  # Default to first 3 chars
        else:
            # Final fallback for unknown formats
            self.base_currency = symbol.replace("t", "").replace("USD", "")[:3]

        # Data storage - all initially empty, populated by real WebSocket data
        self.order_book: dict[str, list[list[float]]] = {"bids": [], "asks": []}
        self.recent_trades: deque[dict[str, Any]] = deque(maxlen=10)
        self.user_orders: list[OrderData] = []

        # Calculate dynamic events log size based on terminal height
        # Available height = terminal_height - header(2) - footer(1) - margins(~5)
        available_height = self.terminal_height - 8
        self.events_log: deque[str] = deque(maxlen=max(15, available_height))

        # Store client reference for order fetching
        self.client: BitfinexClientWrapper | None = None
        self.connection_stats: dict[str, Any] = {
            "trades_channel": False,
            "book_channel": False,
            "authenticated": False,
            "ticker_channel": False,
            "last_trade_time": None,
            "last_book_update": None,
            "last_ticker_update": None,
            "total_trades": 0,
            "total_book_updates": 0,
            "user_orders_count": 0,
            "user_orders_in_range": 0,
        }

        # Market data
        self.last_price = 0.0
        self.mid_price = 0.0

    def add_event(self, message: str, event_type: str = "SYS") -> None:
        """Add event to display log with timestamp and categorization."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_event = f"[{event_type}] {timestamp} {message}"
        self.events_log.append(formatted_event)

    def add_debug_event(self, message: str) -> None:
        """Add debug event with [SYS] category."""
        self.add_event(message, "SYS")

    def get_spread(self) -> float:
        """Calculate current spread percentage."""
        if self.order_book["bids"] and self.order_book["asks"] and self.mid_price > 0:
            best_bid = float(self.order_book["bids"][0][0])
            best_ask = float(self.order_book["asks"][0][0])
            return ((best_ask - best_bid) / self.mid_price) * 100
        return 0.0

    def get_liquidity_2pct(self) -> tuple[float, float]:
        """Calculate liquidity within 2% of mid price in base currency."""
        if not self.mid_price or self.mid_price <= 0:
            return 0.0, 0.0

        threshold = self.mid_price * 0.02  # 2% threshold
        liq_bid = 0.0
        liq_ask = 0.0

        # Sum bid volumes within 2%
        for bid in self.order_book["bids"]:
            if len(bid) >= 2:
                bid_price = float(bid[0])
                if abs(bid_price - self.mid_price) <= threshold:
                    liq_bid += abs(float(bid[1]))  # Volume is always positive

        # Sum ask volumes within 2%
        for ask in self.order_book["asks"]:
            if len(ask) >= 2:
                ask_price = float(ask[0])
                if abs(ask_price - self.mid_price) <= threshold:
                    liq_ask += abs(float(ask[1]))  # Volume is always positive

        return liq_bid, liq_ask

    def process_ticker_update(self, ticker_data: list) -> None:
        """Process ticker update and extract last price."""
        if len(ticker_data) >= 7:
            self.last_price = float(ticker_data[6])  # LAST_PRICE
            self.connection_stats["last_ticker_update"] = time.time()

    def process_order_book_snapshot(self, book_data: list) -> None:
        """Process order book snapshot and organize by bids/asks."""
        bids = []
        asks = []

        for entry in book_data:
            if len(entry) >= 3:
                price = float(entry[0])
                count = int(entry[1])
                amount = float(entry[2])

                if count > 0:
                    if amount > 0:
                        bids.append([price, amount, count])
                    else:
                        asks.append([price, abs(amount), count])

        # Sort bids (highest first) and asks (lowest first)
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        self.order_book = {"bids": bids, "asks": asks}

        # Calculate mid price
        if bids and asks:
            self.mid_price = (bids[0][0] + asks[0][0]) / 2

        self.connection_stats["last_book_update"] = time.time()
        self.connection_stats["total_book_updates"] += 1

    def process_order_book_update(self, book_level: list) -> None:
        """Process incremental order book update."""
        if len(book_level) < 3:
            return

        price = float(book_level[0])
        count = int(book_level[1])
        amount = float(book_level[2])

        # Determine if this is a bid or ask
        is_bid = amount > 0

        if count == 0:
            # Remove level (count = 0 means remove)
            book_side_key = "bids" if is_bid else "asks"
            self.order_book[book_side_key] = [
                level for level in self.order_book[book_side_key] if level[0] != price
            ]
        else:
            # Add or update level
            new_level = [price, abs(amount), count]
            book_side_key = "bids" if is_bid else "asks"

            # Remove existing level at this price
            self.order_book[book_side_key] = [
                level for level in self.order_book[book_side_key] if level[0] != price
            ]

            # Add new level
            self.order_book[book_side_key].append(new_level)

            # Re-sort: bids highest first, asks lowest first
            if is_bid:
                self.order_book["bids"].sort(key=lambda x: x[0], reverse=True)
            else:
                self.order_book["asks"].sort(key=lambda x: x[0])

        # Update mid price
        if self.order_book["bids"] and self.order_book["asks"]:
            self.mid_price = (self.order_book["bids"][0][0] + self.order_book["asks"][0][0]) / 2

        self.connection_stats["last_book_update"] = time.time()
        self.connection_stats["total_book_updates"] += 1

    def process_trades_snapshot(self, trades_data: list) -> None:
        """Process trades snapshot from WebSocket."""
        for trade in trades_data:
            self.process_trade(trade)

    def process_trade(self, trade_data: list) -> None:
        """Process individual trade data."""
        if len(trade_data) >= 5:
            trade_info = {
                "id": trade_data[0],
                "timestamp": trade_data[1],
                "amount": float(trade_data[2]),
                "price": float(trade_data[3]),
                "side": "BUY" if float(trade_data[2]) > 0 else "SELL",
            }
            self.recent_trades.append(trade_info)
            self.connection_stats["last_trade_time"] = time.time()
            self.connection_stats["total_trades"] += 1

    def parse_order_data(self, order_data: list) -> OrderData | None:
        """Convert raw Bitfinex order array to OrderData object."""
        try:
            # Bitfinex order array format: [ID, GID, CID, SYMBOL, MTS_CREATE, MTS_UPDATE, AMOUNT, AMOUNT_ORIG, ORDER_TYPE, TYPE_PREV, MTS_TIF, PLACEHOLDER, FLAGS, STATUS, PLACEHOLDER, PLACEHOLDER, PRICE, ...]
            return OrderData(
                id=order_data[0],  # ID
                symbol=order_data[3],  # SYMBOL
                amount=order_data[6],  # AMOUNT
                price=order_data[16],  # PRICE
                status=order_data[13],  # STATUS
            )
        except (IndexError, TypeError) as e:
            self.add_event(f"Error parsing order data: {e}", "ERR")
            return None

    def process_user_orders_snapshot(self, orders_data: list) -> None:
        """Process user orders snapshot."""
        self.user_orders = []
        for order_data in orders_data:
            if order_data and len(order_data) >= 17:
                parsed_order = self.parse_order_data(order_data)
                if parsed_order and parsed_order.symbol == self.symbol:
                    self.user_orders.append(parsed_order)

        self.connection_stats["user_orders_count"] = len(self.user_orders)
        self.calculate_user_orders_in_range()

    def process_user_order_new(self, order_data: list) -> None:
        """Process new user order."""
        if order_data and len(order_data) >= 17:
            parsed_order = self.parse_order_data(order_data)
            if parsed_order and parsed_order.symbol == self.symbol:
                self.user_orders.append(parsed_order)
                self.connection_stats["user_orders_count"] = len(self.user_orders)
                self.calculate_user_orders_in_range()

    def process_user_order_update(self, order_data: list) -> None:
        """Process user order update."""
        if order_data and len(order_data) >= 17:
            parsed_order = self.parse_order_data(order_data)
            if parsed_order and parsed_order.symbol == self.symbol:
                # Find and update existing order
                for i, existing_order in enumerate(self.user_orders):
                    if existing_order.id == parsed_order.id:
                        self.user_orders[i] = parsed_order
                        break
                self.calculate_user_orders_in_range()

    def process_user_order_cancel(self, order_data: list) -> None:
        """Process user order cancellation."""
        if order_data and len(order_data) >= 1:
            order_id = order_data[0]
            # Remove order from list
            self.user_orders = [order for order in self.user_orders if order.id != order_id]
            self.connection_stats["user_orders_count"] = len(self.user_orders)
            self.calculate_user_orders_in_range()

    def calculate_user_orders_in_range(self) -> None:
        """Calculate how many user orders are within 2% of mid price."""
        if not self.mid_price or self.mid_price <= 0:
            self.connection_stats["user_orders_in_range"] = 0
            return

        threshold = self.mid_price * 0.02  # 2% threshold
        in_range = 0

        for order in self.user_orders:
            if abs(order.price - self.mid_price) <= threshold:
                in_range += 1

        self.connection_stats["user_orders_in_range"] = in_range

    def render_display(self) -> None:
        """Render the complete monitoring display."""
        # Clear screen and position cursor at top
        print("\033[H\033[J", end="")

        # Get dimensions for responsive layout
        total_parts = 7  # 2 + 2 + 3 = 7 parts total
        left_width = int(self.terminal_width * 2 / total_parts)  # 2/7 ≈ 29% for connection stats
        center_width = int(self.terminal_width * 2 / total_parts)  # 2/7 ≈ 29% for order book

        current_price = self.last_price if self.last_price > 0 else self.mid_price

        if current_price > 0:
            # Calculate liquidity within 2% and USD equivalents
            liq_2pct_bid, liq_2pct_ask = self.get_liquidity_2pct()

            # Calculate USD equivalents
            liq_2pct_bid_usd = 0.0
            liq_2pct_ask_usd = 0.0

            if self.mid_price > 0:
                threshold = self.mid_price * 0.02  # 2% threshold

                # Calculate USD for bids within 2%
                for bid in self.order_book["bids"]:
                    if len(bid) >= 2:
                        bid_price = float(bid[0])
                        if abs(bid_price - self.mid_price) <= threshold:
                            liq_2pct_bid_usd += float(bid[1]) * bid_price  # volume * price = USD

                # Calculate USD for asks within 2%
                for ask in self.order_book["asks"]:
                    if len(ask) >= 2:
                        ask_price = float(ask[0])
                        if abs(ask_price - self.mid_price) <= threshold:
                            liq_2pct_ask_usd += float(ask[1]) * ask_price  # volume * price = USD

            # Format USD amounts with appropriate units
            def format_usd(amount: float) -> str:
                if amount >= 1_000_000:
                    return f"${amount / 1_000_000:.1f}M"
                elif amount >= 1_000:
                    return f"${amount / 1_000:.0f}K"
                else:
                    return f"${amount:.0f}"

            liq_2pct_bid_usd_str = format_usd(liq_2pct_bid_usd)
            liq_2pct_ask_usd_str = format_usd(liq_2pct_ask_usd)

            spread = self.get_spread()

            # Create header with mathematical notation (no separators)
            header_left = f"{self.symbol}"
            header_right = f"{datetime.now().strftime('%H:%M:%S')}"

            # Calculate center content - key trading metrics with clean notation
            metrics = [
                f"LAST {current_price:.4f}",
                f"Δ ±{spread:.2f}%",
                f"LIQ2% {liq_2pct_bid:.1f}•{liq_2pct_ask:.1f} {self.base_currency}",
                f"≈ {liq_2pct_bid_usd_str}•{liq_2pct_ask_usd_str}",
            ]
            header_center = " ".join(metrics)

            # Calculate spacing for header alignment
            available_space = self.terminal_width - len(header_left) - len(header_right)
            center_padding = max(0, (available_space - len(header_center)) // 2)

            header = (
                header_left
                + " " * center_padding
                + header_center
                + " " * (available_space - center_padding - len(header_center))
                + header_right
            )

            print(header)
            print("=" * self.terminal_width)
        else:
            # Fallback header when no price data
            print(f"{self.symbol} • Real-time Monitor • {datetime.now().strftime('%H:%M:%S')}")
            print("=" * self.terminal_width)

        # Three-column layout: Connection Stats | Order Book | Events
        # Calculate available lines for content
        current_lines_used = 2  # Header takes 2 lines

        # Connection stats column
        connection_lines = [
            "CONNECTION STATS:",
            f"🔗 Book: {'✅' if self.connection_stats['book_channel'] else '❌'}",
            f"📈 Trades: {'✅' if self.connection_stats['trades_channel'] else '❌'}",
            f"🔐 Auth: {'✅' if self.connection_stats['authenticated'] else '❌'}",
            f"📊 Ticker: {'✅' if self.connection_stats['ticker_channel'] else '❌'}",
            "",
            "MARKET DATA:",
            f"📈 Trades: {self.connection_stats['total_trades']}",
            f"📚 Book Updates: {self.connection_stats['total_book_updates']}",
            f"💰 My Orders: {self.connection_stats['user_orders_count']}",
            f"🎯 In Range: {self.connection_stats['user_orders_in_range']}",
        ]

        # Order book column (Price:Volume:Count in 4:4:1 ratio)
        order_book_lines = ["ORDER LEVELS:"]
        if self.order_book["bids"] or self.order_book["asks"]:
            # Column headers
            available_width = center_width - 2  # Account for separating spaces
            col1_width = int(available_width * 4 / 9)  # 4/9 for Price
            col2_width = int(available_width * 4 / 9)  # 4/9 for Volume
            col3_width = available_width - col1_width - col2_width  # 1/9 for Count

            order_book_lines.append(
                f"{'Price':<{col1_width}} {'Volume':<{col2_width}} {'Cnt':<{col3_width}}"
            )
            order_book_lines.append("-" * available_width)

            # Show asks (lowest first, limited to display space)
            asks_to_show = self.order_book["asks"][: self.levels // 2]
            asks_to_show.reverse()  # Show highest asks first

            for ask in asks_to_show:
                price, volume, count = ask[0], ask[1], ask[2]
                price_str = f"{price:.4f}"
                volume_str = f"{volume:.3f}"
                line = (
                    f"{price_str:<{col1_width}} {volume_str:<{col2_width}} {count:<{col3_width}d}"
                )
                order_book_lines.append(line)

            # Separator line for mid price
            if self.mid_price > 0:
                mid_line = f"--- MID {self.mid_price:.4f} ---"
                order_book_lines.append(mid_line.center(available_width))

            # Show bids (highest first)
            bids_to_show = self.order_book["bids"][: self.levels // 2]
            for bid in bids_to_show:
                price, volume, count = bid[0], bid[1], bid[2]
                price_str = f"{price:.4f}"
                volume_str = f"{volume:.3f}"
                line = (
                    f"{price_str:<{col1_width}} {volume_str:<{col2_width}} {count:<{col3_width}d}"
                )
                order_book_lines.append(line)
        else:
            order_book_lines.append("Waiting for order book data...")

        # Events column - calculate how much space we have
        remaining_space = max(
            3, self.terminal_height - current_lines_used - 1
        )  # Reserve 1 line for footer
        events_to_show = min(len(self.events_log), remaining_space - 1)  # -1 for "EVENTS:" header

        events_lines = ["EVENTS:"]
        recent_events = list(self.events_log)[-events_to_show:] if events_to_show > 0 else []
        events_lines.extend(recent_events)

        # Combine all recent trades (market + user) and show as much as space allows
        all_trades = []

        # Add market trades
        for trade in list(self.recent_trades):
            trade_info = trade.copy()
            trade_info["is_user"] = False
            all_trades.append(trade_info)

        # Add user trades (if any)
        # Note: We don't have user trades in the current implementation,
        # but this is where they would be added if available

        # Sort by timestamp (most recent first)
        all_trades.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        # Add trades section after events
        if all_trades:
            available_lines_for_trades = remaining_space - len(events_lines)

            if available_lines_for_trades > 2:  # Need at least space for header + 1 trade
                events_lines.append("")
                events_lines.append("LATEST TRADES:")
                available_trade_lines = available_lines_for_trades - 2

                # Show as many trades as space allows
                trades_to_show = min(len(all_trades), available_trade_lines)

                for _i, trade in enumerate(all_trades[:trades_to_show]):
                    # Extract trade data
                    amount = trade.get("amount", 0)
                    price = trade.get("price", 0)
                    raw_timestamp = trade.get("timestamp", 0)
                    is_user = trade.get("is_user", False)

                    # Convert millisecond timestamp to readable format
                    if isinstance(raw_timestamp, int | float) and raw_timestamp > 0:
                        timestamp_dt = datetime.fromtimestamp(raw_timestamp / 1000)
                        timestamp = timestamp_dt.strftime("%H:%M:%S")
                    else:
                        timestamp = "??:??:??"

                    # Format trade line
                    side = "BUY" if amount > 0 else "SELL"
                    user_indicator = "*" if is_user else ""
                    trade_line = f"{timestamp} {side} {abs(amount):.3f}@{price:.4f}{user_indicator}"
                    events_lines.append(trade_line)

        # Render three-column layout
        max_lines = max(len(connection_lines), len(order_book_lines), len(events_lines))

        for i in range(max_lines):
            # Connection stats column
            if i < len(connection_lines):
                conn_text = connection_lines[i].ljust(left_width)[:left_width]
            else:
                conn_text = " " * left_width

            # Order book column
            if i < len(order_book_lines):
                book_text = order_book_lines[i].ljust(center_width)[:center_width]
            else:
                book_text = " " * center_width

            # Events column (takes remaining width)
            events_text = events_lines[i] if i < len(events_lines) else ""

            # Print combined line with separators
            print(f"{conn_text} | {book_text} | {events_text}")

        # Footer
        uptime = int(time.time() - self.start_time)
        uptime_str = f"{uptime // 60}:{uptime % 60:02d}"
        footer = f"v{__version__} | Uptime: {uptime_str} | ESC/Ctrl+C to exit"
        print(f"\n{footer}")
