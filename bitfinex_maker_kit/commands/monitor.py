"""
Real-time market monitoring command using WebSocket connections.

Provides a live dashboard showing order book, trades, user orders,
and connection statistics in real-time using WebSocket feeds.
"""

import asyncio
import contextlib
import os
import signal
import sys
import time
from collections import deque
from datetime import datetime
from typing import Any

from ..bitfinex_client import BitfinexClientWrapper
from ..utilities.auth import get_credentials
from ..utilities.constants import DEFAULT_SYMBOL


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
            term_size = os.get_terminal_size()
            self.terminal_width = term_size.columns
            self.terminal_height = term_size.lines
        except (AttributeError, OSError):
            try:
                import subprocess

                cols_result = subprocess.run(["tput", "cols"], capture_output=True, text=True)
                lines_result = subprocess.run(["tput", "lines"], capture_output=True, text=True)
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

        # Extract base currency from symbol (e.g., tBTCUSD -> BTC, tETHUSD -> ETH)
        if symbol.startswith("t") and len(symbol) >= 7:
            # Standard format: tBTCUSD, tETHUSD, etc.
            self.base_currency = symbol[1:4]  # BTC, ETH, etc.
        elif symbol.startswith("t") and "USD" in symbol:
            # Handle longer symbols like tADAUSD -> ADA
            self.base_currency = symbol[1 : symbol.find("USD")]
        else:
            # Fallback
            self.base_currency = symbol.replace("t", "").replace("USD", "")[:3]

        # Data storage - all initially empty, populated by real WebSocket data
        self.order_book = {"bids": [], "asks": []}
        self.recent_trades = deque(maxlen=10)
        self.user_orders = []

        # Calculate dynamic events log size based on terminal height
        # Available height = terminal_height - header(2) - footer(1) - margins(~5)
        available_height = self.terminal_height - 8
        self.events_log = deque(maxlen=max(15, available_height))

        # Store client reference for order fetching
        self.client = None
        self.connection_stats = {
            "trades_channel": False,
            "book_channel": False,
            "authenticated": False,
            "total_orders": 0,
            "user_orders_in_range": 0,
            "trades_events": 0,
            "book_events": 0,
        }

        # Market data - starts at zero, updated by real ticker data
        self.mid_price = 0.0
        self.spread = 0.0
        self.bid_liquidity = 0.0
        self.ask_liquidity = 0.0
        self.last_price = 0.0
        self.price_change = 0.0
        self.price_change_pct = 0.0
        self.volume = 0.0
        self.high = 0.0
        self.low = 0.0

    def clear_screen(self) -> None:
        """Clear terminal screen."""
        print("\033[2J\033[H", end="")

    def get_uptime(self) -> str:
        """Get formatted uptime string."""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        return f"{hours}h{minutes:02d}m"

    def add_event(self, message: str, event_type: str = "INFO") -> None:
        """Add event to events log with event type."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        self.events_log.append(f"{timestamp} [{event_type}] {message}")

    def add_debug_event(self, message: str) -> None:
        """Add debug event to events log."""
        self.add_event(f"DEBUG: {message}", "DEBUG")

    def update_market_data_from_ticker(self, ticker_data: list) -> None:
        """Update market data from real ticker WebSocket data."""
        try:
            if ticker_data and len(ticker_data) >= 10:
                # Bitfinex ticker format: [BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, DAILY_CHANGE_RELATIVE, LAST_PRICE, VOLUME, HIGH, LOW]
                self.last_price = float(ticker_data[6]) if ticker_data[6] else self.last_price
                bid_price = float(ticker_data[0]) if ticker_data[0] else 0
                ask_price = float(ticker_data[2]) if ticker_data[2] else 0

                if bid_price > 0 and ask_price > 0:
                    self.mid_price = (bid_price + ask_price) / 2
                    self.spread = ask_price - bid_price

                self.price_change_pct = float(ticker_data[5]) * 100 if ticker_data[5] else 0
                self.volume = float(ticker_data[7]) if ticker_data[7] else 0
                self.high = float(ticker_data[8]) if ticker_data[8] else 0
                self.low = float(ticker_data[9]) if ticker_data[9] else 0

                # Bid/ask sizes for liquidity
                self.bid_liquidity = float(ticker_data[1]) if ticker_data[1] else 0
                self.ask_liquidity = float(ticker_data[3]) if ticker_data[3] else 0

        except Exception as e:
            self.add_event(f"Error updating market data: {e}", "ERR")

    def update_order_book(self, book_data: dict[str, Any]) -> None:
        """Update order book data from real WebSocket feed."""
        if "bids" in book_data:
            self.order_book["bids"] = book_data["bids"][: self.levels]
        if "asks" in book_data:
            self.order_book["asks"] = book_data["asks"][: self.levels]

        # Calculate mid price and spread from real data
        if self.order_book["bids"] and self.order_book["asks"]:
            best_bid = float(self.order_book["bids"][0][0])
            best_ask = float(self.order_book["asks"][0][0])
            self.mid_price = (best_bid + best_ask) / 2
            self.spread = best_ask - best_bid

            # Calculate real liquidity
            self.bid_liquidity = sum(float(level[1]) for level in self.order_book["bids"])
            self.ask_liquidity = sum(float(level[1]) for level in self.order_book["asks"])

    def add_trade(self, trade_data: dict[str, Any]) -> None:
        """Add trade to recent trades from real WebSocket feed."""
        self.recent_trades.append(trade_data)

    def update_user_orders(self, orders: list[Any]) -> None:
        """Update user orders data from real WebSocket feed."""
        self.user_orders = orders

        # Count orders within 2% of mid price
        if self.mid_price > 0:
            in_range = 0
            for order in orders:
                price = float(getattr(order, "price", 0))
                if price > 0:
                    distance = abs(price - self.mid_price) / self.mid_price
                    if distance <= 0.02:  # Within 2%
                        in_range += 1
            self.connection_stats["user_orders_in_range"] = in_range

    def process_user_order_update(self, order_data: Any) -> None:
        """Process user order updates from WebSocket (NO REST API)."""
        try:
            # WebSocket order updates come as order objects
            # Check symbol matching with multiple property names and formats
            order_symbol = None
            if hasattr(order_data, "symbol"):
                order_symbol = order_data.symbol
            elif hasattr(order_data, "Symbol"):
                order_symbol = order_data.Symbol
            elif hasattr(order_data, "pair"):
                order_symbol = order_data.pair

            # Debug log
            self.add_event(f"Order update: symbol={order_symbol}, target={self.symbol}")

            # Match symbol - check exact match and also without 't' prefix
            if order_symbol and (
                order_symbol == self.symbol
                or order_symbol == self.symbol.replace("t", "")
                or f"t{order_symbol}" == self.symbol
            ):
                # Check if order already exists in our list
                order_id = getattr(order_data, "id", None) or getattr(order_data, "ID", None)
                existing_order = None
                for i, existing in enumerate(self.user_orders):
                    existing_id = getattr(existing, "id", None) or getattr(existing, "ID", None)
                    if existing_id == order_id:
                        existing_order = i
                        break

                # If order is active, add/update it
                order_status = getattr(order_data, "status", "") or getattr(
                    order_data, "STATUS", ""
                )
                if order_status in ["ACTIVE", "PARTIALLY FILLED", "PARTIALLY_FILLED"]:
                    if existing_order is not None:
                        self.user_orders[existing_order] = order_data
                        self.add_event(f"Order updated: {order_id} for {order_symbol}", "ORDER")
                    else:
                        self.user_orders.append(order_data)
                        self.add_event(f"Order added: {order_id} for {order_symbol}", "ORDER")
                else:
                    # Order canceled or filled, remove it
                    if existing_order is not None:
                        self.user_orders.pop(existing_order)
                        self.add_event(f"Order removed: {order_id} ({order_status})", "ORDER")

                # Update orders in range count
                self.update_orders_in_range()

        except Exception as e:
            self.add_event(f"Error processing order update: {e}", "ERR")

    def update_orders_in_range(self) -> None:
        """Update count of orders within 2% of mid price."""
        if self.mid_price > 0 and self.user_orders:
            in_range = 0
            for order in self.user_orders:
                price = float(getattr(order, "price", 0))
                if price > 0:
                    distance = abs(price - self.mid_price) / self.mid_price
                    if distance <= 0.02:  # Within 2%
                        in_range += 1
            self.connection_stats["user_orders_in_range"] = in_range
        else:
            self.connection_stats["user_orders_in_range"] = 0

    def parse_order_data(self, order_data: list) -> OrderData:
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

    def handle_order_snapshot(self, orders_array: list) -> None:
        """Process initial order snapshot from WebSocket."""
        self.add_event(f"Processing order snapshot: {len(orders_array)} orders")
        self.user_orders = []  # Clear existing orders

        matched_orders = 0
        symbols_seen = set()
        for order_data in orders_array:
            if len(order_data) > 16:  # Ensure order data is complete
                parsed_order = self.parse_order_data(order_data)
                if parsed_order:
                    symbols_seen.add(parsed_order.symbol)
                    # Check multiple symbol format variations
                    if (
                        parsed_order.symbol == self.symbol
                        or parsed_order.symbol == self.symbol.replace("t", "")
                        or f"t{parsed_order.symbol}" == self.symbol
                    ):
                        self.user_orders.append(parsed_order)
                        matched_orders += 1
                        self.add_event(
                            f"Matched order {parsed_order.id} for {parsed_order.symbol}", "ORDER"
                        )

        if symbols_seen:
            self.add_event(f"Symbols in snapshot: {', '.join(sorted(symbols_seen)[:5])}")
        self.add_event(f"Loaded {matched_orders} orders for {self.symbol} from snapshot")
        self.update_orders_in_range()

    def handle_order_new(self, order_data: list) -> None:
        """Process new order from WebSocket."""
        if len(order_data) > 16:
            parsed_order = self.parse_order_data(order_data)
            if (
                parsed_order
                and parsed_order.symbol == self.symbol
                and parsed_order.status == "ACTIVE"
            ):
                self.user_orders.append(parsed_order)
                self.add_event(f"New order: {parsed_order.id} for {parsed_order.symbol}")
                self.update_orders_in_range()

    def handle_order_update(self, order_data: list) -> None:
        """Process order update from WebSocket."""
        if len(order_data) > 16:
            parsed_order = self.parse_order_data(order_data)
            if parsed_order and parsed_order.symbol == self.symbol:
                # Find and update existing order
                for i, existing_order in enumerate(self.user_orders):
                    if existing_order.id == parsed_order.id:
                        if parsed_order.status in ["ACTIVE", "PARTIALLY FILLED"]:
                            self.user_orders[i] = parsed_order
                            self.add_event(f"Updated order: {parsed_order.id}")
                        else:
                            # Order cancelled/filled, remove it
                            self.user_orders.pop(i)
                            self.add_event(
                                f"Removed order: {parsed_order.id} ({parsed_order.status})"
                            )
                        break
                self.update_orders_in_range()

    def handle_order_cancel(self, order_data: list) -> None:
        """Process order cancellation from WebSocket."""
        if len(order_data) > 0:
            order_id = order_data[0]  # ID is first field
            # Remove order from user orders
            self.user_orders = [o for o in self.user_orders if o.id != order_id]
            self.add_event(f"Cancelled order: {order_id}")
            self.update_orders_in_range()

    def render_header(self) -> str:
        """Render header section with real market data."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Use real market data (fallback to zero if no data received)
        current_price = self.last_price if self.last_price > 0 else 0.0

        # Calculate spread percentage for header
        if self.order_book["bids"] and self.order_book["asks"]:
            best_bid = float(self.order_book["bids"][0][0])
            best_ask = float(self.order_book["asks"][0][0])
            spread = best_ask - best_bid
            spread_pct = spread / ((best_bid + best_ask) / 2) * 100
        else:
            spread_pct = 0.0

        # Dynamic column distribution based on terminal width - 2:2:3 ratio
        # Total 7 parts: metrics=2, orders=2, events=3

        if current_price > 0:
            # Calculate liquidity within 2% of mid price in USD equivalent
            liq_2pct_bid_usd = 0.0
            liq_2pct_ask_usd = 0.0
            if self.mid_price > 0:
                threshold = self.mid_price * 0.02  # 2% range

                # Count bid liquidity within 2% in USD
                for bid in self.order_book["bids"]:
                    bid_price = float(bid[0])
                    if abs(bid_price - self.mid_price) <= threshold:
                        liq_2pct_bid_usd += float(bid[1]) * bid_price  # volume * price = USD

                # Count ask liquidity within 2% in USD
                for ask in self.order_book["asks"]:
                    ask_price = float(ask[0])
                    if abs(ask_price - self.mid_price) <= threshold:
                        liq_2pct_ask_usd += float(ask[1]) * ask_price  # volume * price = USD

            # Format USD amounts with appropriate units
            def format_usd(amount):
                if amount >= 1_000_000:
                    return f"${amount / 1_000_000:.1f}M"
                elif amount >= 1_000:
                    return f"${amount / 1_000:.0f}K"
                else:
                    return f"${amount:.0f}"

            # Elegant center notation: Price • Liquidity±2% • Spread
            center_data = f"${current_price:.4f} • L±2%: {format_usd(liq_2pct_bid_usd)}/{format_usd(liq_2pct_ask_usd)} • Δ${self.spread:.4f}({spread_pct:.2f}%)"

            # Calculate spacing for center alignment
            total_width = self.terminal_width
            ticker_len = len(self.symbol)
            time_len = len(timestamp)
            center_len = len(center_data)

            # Available space for padding
            available_space = total_width - ticker_len - time_len - center_len
            if available_space > 0:
                left_pad = available_space // 2
                right_pad = available_space - left_pad
                header = f"{self.symbol}{' ' * left_pad}{center_data}{' ' * right_pad}{timestamp}"
            else:
                # Fallback if too long
                header = f"{self.symbol} {center_data} {timestamp}"
        else:
            # No data received yet - show waiting state
            center_data = "[Connecting to WebSocket...]"
            total_width = self.terminal_width
            ticker_len = len(self.symbol)
            time_len = len(timestamp)
            center_len = len(center_data)

            available_space = total_width - ticker_len - time_len - center_len
            if available_space > 0:
                left_pad = available_space // 2
                right_pad = available_space - left_pad
                header = f"{self.symbol}{' ' * left_pad}{center_data}{' ' * right_pad}{timestamp}"
            else:
                header = f"{self.symbol} {center_data} {timestamp}"

        return header

    def render_order_book(self) -> str:
        """Render order book section with real data only."""
        lines = []
        lines.append("BEST 40 ORDER LEVELS")
        center_width = int(self.terminal_width * 2 / 7)  # 2/7 ≈ 29% for order book column
        lines.append("─" * center_width)
        # Calculate column widths: 4-4-1 ratio accounting for separating spaces
        available_width = center_width - 2  # subtract 2 for the separating spaces
        min_count_width = 3  # Minimum for "Cnt" and numbers

        if available_width < 30:  # If too narrow, use minimum widths
            col3_width = min_count_width
            remaining = available_width - col3_width
            col1_width = int(remaining * 4 / 8)  # 4/(4+4) of remaining
            col2_width = remaining - col1_width
        else:
            # Use proper 4:4:1 ratio within available space
            total_parts = 9  # 4+4+1
            col1_width = int(available_width * 4 / total_parts)  # 4/9 for Price
            col2_width = int(available_width * 4 / total_parts)  # 4/9 for Volume
            col3_width = max(
                min_count_width, available_width - col1_width - col2_width
            )  # ensure minimum

        lines.append(f"{'Price':<{col1_width}} {'Volume':<{col2_width}} {'Cnt':<{col3_width}}")
        lines.append("─" * center_width)

        if not self.order_book["asks"] and not self.order_book["bids"]:
            # No order book data available
            lines.append("[No order book data available]")
            lines.append("")
            lines.append("Waiting for WebSocket book channel...")
            lines.append("")
            for _ in range(35):  # Fill remaining space
                lines.append("")
        else:
            # Show real asks (highest to lowest)
            asks = self.order_book["asks"][:20]
            for ask in reversed(asks):
                price, volume, count = float(ask[0]), float(ask[1]), int(ask[2])
                lines.append(
                    f"${price:<{col1_width - 1}.4f} {volume:<{col2_width},.3f} {count:<{col3_width}d}"
                )

            # Mid price line from real data
            if self.mid_price > 0:
                price_str = f"${self.mid_price:.6f}"
                remaining_width = center_width - len(price_str)
                dashes = "─" * max(0, remaining_width)
                mid_line = f"{price_str}{dashes}"
                lines.append(mid_line)

            # Show real bids (highest to lowest)
            bids = self.order_book["bids"][:20]
            for bid in bids:
                price, volume, count = float(bid[0]), float(bid[1]), int(bid[2])
                lines.append(
                    f"${price:<{col1_width - 1}.4f} {volume:<{col2_width},.3f} {count:<{col3_width}d}"
                )

        lines.append("─" * center_width)
        lines.append("Showing: 20 Ask + 20 Bid levels (Best 40)")

        return "\n".join(lines)

    def render_left_panel(self) -> str:
        """Render left panel with real connection stats and trades."""
        lines = []

        # Connection & Exchange section - real data only
        lines.append("CONNECTION & EXCHANGE")
        left_width = int(self.terminal_width * 2 / 7)  # 2/7 ≈ 29% for metrics column
        lines.append("─" * left_width)

        # Calculate real market data from order book + user orders
        if self.order_book["bids"] and self.order_book["asks"]:
            user_order_count = len(self.user_orders)

            # Calculate market orders from order book (aggregated view)
            market_order_count = sum(int(level[2]) for level in self.order_book["bids"]) + sum(
                int(level[2]) for level in self.order_book["asks"]
            )

            # Total includes your orders + other market orders
            # Note: Your orders might be partially included in market_order_count if they're at best levels
            # But we'll add them to give a more complete picture
            total_orders = market_order_count + user_order_count

            # Show the breakdown
            lines.append(f"Market Orders: {market_order_count}")
            lines.append(f"Your Orders: {user_order_count}")
            lines.append(f"Total Orders: {total_orders}")

            # Count orders within ±2% of mid price (market + user orders)
            if self.mid_price > 0:
                orders_in_range = 0
                threshold = self.mid_price * 0.02  # 2% range

                # Count market orders in range
                for bid in self.order_book["bids"]:
                    bid_price = float(bid[0])
                    if abs(bid_price - self.mid_price) <= threshold:
                        orders_in_range += int(bid[2])

                for ask in self.order_book["asks"]:
                    ask_price = float(ask[0])
                    if abs(ask_price - self.mid_price) <= threshold:
                        orders_in_range += int(ask[2])

                # Add user orders in range
                orders_in_range += self.connection_stats.get("user_orders_in_range", 0)
            else:
                orders_in_range = 0
        else:
            orders_in_range = 0
            user_order_count = len(self.user_orders)
            market_order_count = 0
            total_orders = user_order_count

            lines.append("Market Orders: 0")
            lines.append(f"Your Orders: {user_order_count}")
            lines.append(f"Total Orders: {total_orders}")

        lines.append(f"Market (±2%): {orders_in_range}")

        # Always calculate spread from current order book data
        if self.order_book["bids"] and self.order_book["asks"]:
            best_bid = float(self.order_book["bids"][0][0])
            best_ask = float(self.order_book["asks"][0][0])
            spread = best_ask - best_bid
            spread_pct = spread / ((best_bid + best_ask) / 2) * 100
            lines.append(f"Spread: ${spread:.6f} ({spread_pct:.2f}%)")
        else:
            lines.append("Spread: [No data]")

        # Calculate real bid/ask liquidity from order book
        if self.order_book["bids"] and self.order_book["asks"] and self.last_price > 0:
            # Sum up actual bid liquidity from order book
            bid_liquidity_pnk = sum(float(bid[1]) for bid in self.order_book["bids"])
            bid_usd = bid_liquidity_pnk * self.last_price
            lines.append(
                f"Bid Liquidity: {bid_liquidity_pnk:,.0f} {self.base_currency} ({bid_usd:,.0f} USD)"
            )

            # Sum up actual ask liquidity from order book
            ask_liquidity_pnk = sum(float(ask[1]) for ask in self.order_book["asks"])
            ask_usd = ask_liquidity_pnk * self.last_price
            lines.append(
                f"Ask Liquidity: {ask_liquidity_pnk:,.0f} {self.base_currency} ({ask_usd:,.0f} USD)"
            )
        else:
            lines.append("Bid Liquidity: [No data]")
            lines.append("Ask Liquidity: [No data]")
        lines.append("")

        # Your Metrics section - real data only
        lines.append("YOUR METRICS")
        lines.append("─" * left_width)

        # Real user metrics from actual orders
        user_order_count = len(self.user_orders)
        user_orders_in_range = self.connection_stats.get("user_orders_in_range", 0)

        lines.append(f"Your Orders: {user_order_count}")
        lines.append(f"Your Orders (±2%): {user_orders_in_range}")

        # Calculate user spread and liquidity from actual orders
        if user_order_count > 0:
            # Calculate from real order data
            user_bids = [o for o in self.user_orders if getattr(o, "amount", 0) > 0]
            user_asks = [o for o in self.user_orders if getattr(o, "amount", 0) < 0]

            if user_bids and user_asks:
                user_best_bid = max(float(getattr(o, "price", 0)) for o in user_bids)
                user_best_ask = min(float(getattr(o, "price", 0)) for o in user_asks)
                user_spread = user_best_ask - user_best_bid
                user_spread_pct = (
                    (user_spread / ((user_best_bid + user_best_ask) / 2) * 100)
                    if user_best_bid > 0 and user_best_ask > 0
                    else 0
                )
                lines.append(f"Your Spread: ${user_spread:.6f} ({user_spread_pct:.2f}%)")
            else:
                lines.append("Your Spread: [No bid/ask pairs]")

            # Calculate liquidity from real orders
            user_bid_liq = sum(abs(float(getattr(o, "amount", 0))) for o in user_bids)
            user_ask_liq = sum(abs(float(getattr(o, "amount", 0))) for o in user_asks)

            if self.last_price > 0:
                lines.append(
                    f"Your Bid Liq: {user_bid_liq:,.2f} {self.base_currency} ({user_bid_liq * self.last_price:,.2f} USD)"
                )
                lines.append(
                    f"Your Ask Liq: {user_ask_liq:,.2f} {self.base_currency} ({user_ask_liq * self.last_price:,.2f} USD)"
                )
            else:
                lines.append(f"Your Bid Liq: {user_bid_liq:,.2f} {self.base_currency} ([No price])")
                lines.append(f"Your Ask Liq: {user_ask_liq:,.2f} {self.base_currency} ([No price])")
        else:
            lines.append("Your Spread: [No orders]")
            lines.append("Your Bid Liq: [No orders]")
            lines.append("Your Ask Liq: [No orders]")
        lines.append("")

        # Combined trades section - market and user trades
        lines.append("LATEST TRADES (MARKET + MINE)")
        lines.append("─" * left_width)

        # Calculate how many trades we can show based on available space
        current_lines_used = len(lines)
        available_height = self.terminal_height - 8  # Reserve space for header/footer
        remaining_space = max(3, available_height - current_lines_used)  # At least 3 trades

        # Real trade data from WebSocket
        if self.recent_trades:
            # Show as many trades as fit in the remaining space
            displayed_trades = list(self.recent_trades)[-remaining_space:]
            for trade in displayed_trades:
                raw_timestamp = trade.get("timestamp", 0)
                # Convert millisecond timestamp to readable format
                if isinstance(raw_timestamp, int | float) and raw_timestamp > 0:
                    timestamp_dt = datetime.fromtimestamp(raw_timestamp / 1000)
                    timestamp = timestamp_dt.strftime("%H:%M:%S")
                else:
                    timestamp = "Unknown"

                amount = abs(float(trade.get("amount", 0)))
                price = float(trade.get("price", 0))
                side = "BUY" if float(trade.get("amount", 0)) > 0 else "SELL"

                # Check if this is a user trade (placeholder logic - would need actual user trade detection)
                is_user_trade = False  # TODO: Implement user trade detection when user trades occur
                marker = "*" if is_user_trade else ""

                lines.append(f"{timestamp} | {side} | {amount:.4f} @ ${price:.6f}{marker}")
        else:
            lines.append("[No recent trades]")
            lines.append("Waiting for WebSocket trade data...")

        lines.append("")

        return "\n".join(lines)

    def render_right_panel(self) -> str:
        """Render right panel with real-time events only."""
        lines = []
        lines.append("REAL-TIME EVENTS")
        right_width = (
            self.terminal_width
            - int(self.terminal_width * 2 / 7)
            - int(self.terminal_width * 2 / 7)
            - 2
        )  # 3/7 ≈ 42% for events
        lines.append("─" * right_width)

        # Calculate how many events we can show based on available vertical space
        # Available space = terminal height - header(2) - footer(1) - panel headers(~8)
        max_events_to_show = max(10, self.terminal_height - 15)

        # Show recent events with better formatting - REAL EVENTS ONLY
        recent_events = list(self.events_log)[-max_events_to_show:]
        for event in recent_events:
            # Ensure events fit within column width (right_width calculated elsewhere)
            max_event_width = min(60, right_width - 2) if "right_width" in locals() else 56
            if len(event) > max_event_width:
                event = event[: max_event_width - 3] + "..."
            lines.append(event)

        # Only show real events - no hardcoded demo data
        # If no recent events, show appropriate status messages
        if len(recent_events) == 0:
            lines.append("[Waiting for WebSocket events...]")
            lines.append("")
            lines.append("Monitor is running in real-time mode.")
            lines.append("Events will appear as they occur.")

        # Fill remaining space with empty lines to use full height
        target_lines = max_events_to_show + 4  # +4 for header and status lines
        while len(lines) < target_lines:
            lines.append("")

        return "\n".join(lines)

    def render_footer(self) -> str:
        """Render footer with status information."""
        uptime = self.get_uptime()

        # Real connection status with masked API key
        if self.api_key and len(self.api_key) >= 8:
            masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
            key_info = f"Key: {masked_key}"
        else:
            key_info = "Key: ****...****"
        ws_status = f"trades({self.connection_stats['trades_events']}), book({self.connection_stats['book_events']})"
        status = "♥ Up-to-date" if self.connection_stats["authenticated"] else "⚠ Disconnected"
        market_status = "Market: Active" if self.last_price > 0 else "Market: No Data"

        footer = f"v4.2.44 │ {key_info} │ WebSocket: {ws_status} │ {status} │ {market_status} │ Uptime: {uptime} │ Press Ctrl+C to exit"
        return footer

    def render_full_display(self) -> None:
        """Render complete display with real data only."""
        self.clear_screen()

        # Header with dynamic width separator
        header = self.render_header()
        separator = "═" * self.terminal_width

        print(header)
        print(separator)

        # Main content in three columns with dynamic widths
        left_panel = self.render_left_panel().split("\n")
        order_book = self.render_order_book().split("\n")
        right_panel = self.render_right_panel().split("\n")

        # Calculate column widths based on terminal size - 1:1:2 ratio
        # Total 4 parts: metrics=1, orders=1, events=2
        left_width = int(self.terminal_width * 2 / 7)  # 2/7 ≈ 29% for connection stats
        center_width = int(self.terminal_width * 2 / 7)  # 2/7 ≈ 29% for order book
        right_width = self.terminal_width - left_width - center_width - 2  # 3/7 ≈ 42% for events

        # Render columns side by side with dynamic spacing
        max_lines = max(len(left_panel), len(order_book), len(right_panel))

        for i in range(max_lines):
            left = left_panel[i] if i < len(left_panel) else ""
            center = order_book[i] if i < len(order_book) else ""
            right = right_panel[i] if i < len(right_panel) else ""

            # Dynamic column widths for full screen utilization
            left_col = f"{left:<{left_width}}"[:left_width]
            center_col = f"{center:<{center_width}}"[:center_width]
            right_col = f"{right:<{right_width}}"[:right_width]

            line = f"{left_col}│{center_col}│{right_col}"
            print(line)

        print(separator)
        print(self.render_footer())


async def monitor_command(symbol: str = DEFAULT_SYMBOL, levels: int = 40) -> None:
    """
    Start real-time market monitoring using WebSocket connections.

    Args:
        symbol: Trading symbol to monitor
        levels: Number of order book levels to display
    """
    try:
        # Get credentials and create client
        api_key, api_secret = get_credentials()
        client = BitfinexClientWrapper(api_key, api_secret)

        # Initialize display with API key for footer display
        display = MonitorDisplay(symbol, levels, api_key)
        display.client = client  # Pass client for order fetching
        display.add_event("Starting market monitor...", "SYS")
        display.add_debug_event(
            f"Terminal size: {display.terminal_width}x{display.terminal_height} (cols x rows)"
        )
        display.add_debug_event(f"Events log capacity: {display.events_log.maxlen} entries")

        # Setup signal handlers for graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(signum: int, frame: Any) -> None:
            """Handle shutdown signals."""
            display.add_event("Shutdown signal received", "INFO")
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        display.add_event("Client created", "SYS")
        display.add_event("Accessing WebSocket interface...")
        print("🔌 Connecting to Bitfinex WebSocket...")

        # Access WebSocket through client
        wss = client.wss
        display.add_event("WebSocket interface accessed")

        # Set up WebSocket event handlers BEFORE starting connection
        display.add_event("Setting up WebSocket event handlers...")

        @wss.on("open")
        def on_open():
            display.add_event("WebSocket connection opened", "CONN")
            print("🔌 WebSocket connection established")

        @wss.on("authenticated")
        async def on_authenticated(data):
            display.add_event("WebSocket authentication successful", "CONN")
            display.connection_stats["authenticated"] = True
            print("🔐 WebSocket authenticated successfully")

            try:
                # Now it's safe to subscribe to channels
                print("📊 Subscribing to market data channels...")
                await wss.subscribe("ticker", symbol=symbol)
                display.add_event(f"Subscribed to ticker for {symbol}", "CONN")
                display.connection_stats["book_channel"] = True  # Ticker provides market data

                await wss.subscribe("book", symbol=symbol, prec="P0", freq="F0", len="25")
                display.add_event(f"Subscribed to order book for {symbol}", "CONN")

                await wss.subscribe("trades", symbol=symbol)
                display.add_event(f"Subscribed to trades for {symbol}", "CONN")
                display.connection_stats["trades_channel"] = True

                # WebSocket-only user order tracking - no REST API
                print("📡 Using WebSocket-only for user orders - no REST API")
                display.add_event("WebSocket-only user order tracking enabled", "SYS")

                print("✅ All WebSocket subscriptions active")

            except Exception as e:
                display.add_event(f"Subscription error: {e}", "ERR")
                print(f"❌ Subscription error: {e}")

        @wss.on("t_ticker_update")
        def on_ticker_update(subscription, ticker_data):
            display.add_event("Ticker data received", "TICK")
            display.connection_stats["book_events"] += 1  # Count ticker as market data
            # Convert ticker object to list format expected by display
            if hasattr(ticker_data, "bid"):
                # It's a ticker object, convert to list format
                ticker_list = [
                    ticker_data.bid,
                    ticker_data.bid_size,
                    ticker_data.ask,
                    ticker_data.ask_size,
                    ticker_data.daily_change,
                    ticker_data.daily_change_relative,
                    ticker_data.last_price,
                    ticker_data.volume,
                    ticker_data.high,
                    ticker_data.low,
                ]
                display.update_market_data_from_ticker(ticker_list)
            else:
                # It's already a list or different format
                display.update_market_data_from_ticker(ticker_data)

        @wss.on("t_book_snapshot")
        def on_book_snapshot(subscription, book_data):
            display.add_event("Order book snapshot received", "BOOK")
            display.connection_stats["book_events"] += 1
            # Convert snapshot data to format expected by display
            bids = []
            asks = []
            for level in book_data:
                # Access object properties instead of array indexing
                price = level.price
                count = level.count
                amount = level.amount
                if amount > 0:  # Bid
                    bids.append([price, amount, count])
                else:  # Ask
                    asks.append([price, abs(amount), count])

            # Sort bids (highest first) and asks (lowest first)
            bids.sort(key=lambda x: float(x[0]), reverse=True)
            asks.sort(key=lambda x: float(x[0]))

            display.update_order_book({"bids": bids, "asks": asks})

        @wss.on("t_book_update")
        def on_book_update(subscription, book_level):
            display.connection_stats["book_events"] += 1

            # Process incremental order book update
            try:
                price = book_level.price
                count = book_level.count
                amount = book_level.amount

                # Determine if it's a bid or ask
                is_bid = amount > 0
                side = "bids" if is_bid else "asks"
                level_amount = abs(amount)

                # Get current book state
                current_book = display.order_book[side]

                if count == 0:
                    # Remove price level
                    display.order_book[side] = [
                        level for level in current_book if float(level[0]) != price
                    ]
                    display.add_event(f"Removed {side[:-1]} level at ${price:.6f}", "BOOK")
                else:
                    # Add or update price level
                    level_data = [price, level_amount, count]

                    # Find existing level
                    updated = False
                    for i, existing_level in enumerate(current_book):
                        if float(existing_level[0]) == price:
                            # Update existing level
                            current_book[i] = level_data
                            updated = True
                            display.add_event(f"Updated {side[:-1]} level at ${price:.6f}", "BOOK")
                            break

                    if not updated:
                        # Add new level and sort
                        current_book.append(level_data)
                        if is_bid:
                            # Sort bids highest to lowest
                            current_book.sort(key=lambda x: float(x[0]), reverse=True)
                        else:
                            # Sort asks lowest to highest
                            current_book.sort(key=lambda x: float(x[0]))

                        # Keep only top levels
                        display.order_book[side] = current_book[: display.levels]
                        display.add_event(f"Added {side[:-1]} level at ${price:.6f}", "BOOK")

                # Recalculate mid price and spread
                if display.order_book["bids"] and display.order_book["asks"]:
                    best_bid = float(display.order_book["bids"][0][0])
                    best_ask = float(display.order_book["asks"][0][0])
                    display.mid_price = (best_bid + best_ask) / 2
                    display.spread = best_ask - best_bid

                    # Update liquidity
                    display.bid_liquidity = sum(
                        float(level[1]) for level in display.order_book["bids"]
                    )
                    display.ask_liquidity = sum(
                        float(level[1]) for level in display.order_book["asks"]
                    )

            except Exception as e:
                display.add_event(f"Error processing book update: {e}", "ERR")

        @wss.on("t_trades_snapshot")
        def on_trades_snapshot(subscription, trades_data):
            display.add_event(f"Trades snapshot received: {len(trades_data)} trades", "TRADE")
            display.connection_stats["trades_events"] += 1
            # Add recent trades to display
            for trade_obj in trades_data[-5:]:  # Last 5 trades
                # Access object properties with correct names
                trade_dict = {
                    "timestamp": trade_obj.mts,  # Use mts for timestamp
                    "amount": trade_obj.amount,
                    "price": trade_obj.price,
                    "id": trade_obj.id,  # Use id not trade_id
                }
                display.add_trade(trade_dict)

        @wss.on("t_trade_execution")
        def on_trade_execution(subscription, trade_data):
            display.add_event("New trade executed", "TRADE")
            display.connection_stats["trades_events"] += 1
            # Access object properties with correct names
            trade_dict = {
                "timestamp": trade_data.mts,  # Use mts for timestamp
                "amount": trade_data.amount,
                "price": trade_data.price,
                "id": trade_data.id,  # Use id not trade_id
            }
            display.add_trade(trade_dict)

        @wss.on("t_trade_execution_update")
        def on_trade_execution_update(subscription, trade_data):
            display.add_event("Trade execution update", "TRADE")
            display.connection_stats["trades_events"] += 1
            # Access object properties with correct names
            trade_dict = {
                "timestamp": trade_data.mts,  # Use mts for timestamp
                "amount": trade_data.amount,
                "price": trade_data.price,
                "id": trade_data.id,  # Use id not trade_id
            }
            display.add_trade(trade_dict)

        @wss.on("disconnected")
        def on_disconnected():
            display.add_event("WebSocket disconnected", "DISC")
            print("⚠️ WebSocket disconnected")

        # Handle authenticated order events using proper WebSocket event names
        @wss.on("order_snapshot")  # Full order snapshot
        def on_auth_order_snapshot(orders_data):
            """Handle order snapshot from authenticated WebSocket."""
            display.add_event(
                f"Order snapshot: {len(orders_data) if hasattr(orders_data, '__len__') else '?'} orders"
            )

            if isinstance(orders_data, list):
                # Convert Order objects to raw data for display processing
                raw_orders = []
                symbols_in_snapshot = set()
                for order in orders_data:
                    if hasattr(order, "__dict__"):
                        # Log symbol for debugging
                        symbols_in_snapshot.add(getattr(order, "symbol", "Unknown"))
                        # Convert Order object to list format [ID, GID, CID, SYMBOL, ...]
                        raw_orders.append(
                            [
                                getattr(order, "id", 0),
                                getattr(order, "gid", 0),
                                getattr(order, "cid", 0),
                                getattr(order, "symbol", ""),
                                getattr(order, "mts_create", 0),
                                getattr(order, "mts_update", 0),
                                getattr(order, "amount", 0),
                                getattr(order, "amount_orig", 0),
                                getattr(order, "type", ""),
                                getattr(order, "type_prev", ""),
                                getattr(order, "mts_tif", 0),
                                None,
                                getattr(order, "flags", 0),
                                getattr(order, "status", ""),
                                None,
                                None,
                                getattr(order, "price", 0),
                            ]
                        )
                    else:
                        raw_orders.append(order)

                # Debug symbols found
                if symbols_in_snapshot:
                    display.add_event(
                        f"Order symbols found: {', '.join(sorted(symbols_in_snapshot))}"
                    )
                    display.add_event(f"Looking for: {symbol}")

                display.handle_order_snapshot(raw_orders)
            else:
                display.add_event(f"Unexpected order_snapshot format: {type(orders_data)}")

        @wss.on("order_new")  # New order created
        def on_auth_order_new(order_data):
            """Handle new order from authenticated WebSocket."""
            display.add_event(f"New order: {getattr(order_data, 'symbol', 'Unknown')}")

            if hasattr(order_data, "__dict__"):
                # Convert Order object to list format using getattr for safety
                raw_order = [
                    getattr(order_data, "id", 0),
                    getattr(order_data, "gid", 0),
                    getattr(order_data, "cid", 0),
                    getattr(order_data, "symbol", ""),
                    getattr(order_data, "mts_create", 0),
                    getattr(order_data, "mts_update", 0),
                    getattr(order_data, "amount", 0),
                    getattr(order_data, "amount_orig", 0),
                    getattr(order_data, "type", ""),
                    getattr(order_data, "type_prev", ""),
                    getattr(order_data, "mts_tif", 0),
                    None,
                    getattr(order_data, "flags", 0),
                    getattr(order_data, "status", ""),
                    None,
                    None,
                    getattr(order_data, "price", 0),
                ]
                display.handle_order_new(raw_order)
            elif isinstance(order_data, list):
                display.handle_order_new(order_data)
            else:
                display.add_event(f"Unexpected order_new format: {type(order_data)}")

        @wss.on("order_update")  # Order updated
        def on_auth_order_update(order_data):
            """Handle order update from authenticated WebSocket."""
            display.add_event(f"Order update: {getattr(order_data, 'symbol', 'Unknown')}")

            if hasattr(order_data, "__dict__"):
                # Convert Order object to list format using getattr for safety
                raw_order = [
                    getattr(order_data, "id", 0),
                    getattr(order_data, "gid", 0),
                    getattr(order_data, "cid", 0),
                    getattr(order_data, "symbol", ""),
                    getattr(order_data, "mts_create", 0),
                    getattr(order_data, "mts_update", 0),
                    getattr(order_data, "amount", 0),
                    getattr(order_data, "amount_orig", 0),
                    getattr(order_data, "type", ""),
                    getattr(order_data, "type_prev", ""),
                    getattr(order_data, "mts_tif", 0),
                    None,
                    getattr(order_data, "flags", 0),
                    getattr(order_data, "status", ""),
                    None,
                    None,
                    getattr(order_data, "price", 0),
                ]
                display.handle_order_update(raw_order)
            elif isinstance(order_data, list):
                display.handle_order_update(order_data)
            else:
                display.add_event(f"Unexpected order_update format: {type(order_data)}")

        @wss.on("order_cancel")  # Order cancelled
        def on_auth_order_cancel(order_data):
            """Handle order cancel from authenticated WebSocket."""
            display.add_event(f"Order cancel: {getattr(order_data, 'symbol', 'Unknown')}")

            if hasattr(order_data, "__dict__"):
                # Convert Order object to list format using getattr for safety
                raw_order = [
                    getattr(order_data, "id", 0),
                    getattr(order_data, "gid", 0),
                    getattr(order_data, "cid", 0),
                    getattr(order_data, "symbol", ""),
                    getattr(order_data, "mts_create", 0),
                    getattr(order_data, "mts_update", 0),
                    getattr(order_data, "amount", 0),
                    getattr(order_data, "amount_orig", 0),
                    getattr(order_data, "type", ""),
                    getattr(order_data, "type_prev", ""),
                    getattr(order_data, "mts_tif", 0),
                    None,
                    getattr(order_data, "flags", 0),
                    getattr(order_data, "status", ""),
                    None,
                    None,
                    getattr(order_data, "price", 0),
                ]
                display.handle_order_cancel(raw_order)
            elif isinstance(order_data, list):
                display.handle_order_cancel(order_data)
            else:
                display.add_event(f"Unexpected order_cancel format: {type(order_data)}")

        @wss.on("wallet_snapshot")  # Wallet snapshot
        def on_wallet_snapshot(wallet_data: Any) -> None:
            display.add_event("Wallet snapshot received", "WALLET")

        @wss.on("wallet_update")  # Wallet update
        def on_wallet_update(wallet_data: Any) -> None:
            display.add_event("Wallet update received", "WALLET")

        # Start WebSocket as a background task to avoid blocking
        display.add_event("Starting WebSocket connection...", "CONN")
        print("🚀 Starting WebSocket connection...")

        # Create background task for WebSocket
        websocket_task = asyncio.create_task(wss.start())
        display.add_event("WebSocket task created - running in background")
        print("📡 WebSocket running in background...")

        display.add_event("Monitor started - WebSocket ready for data!", "SYS")
        print("🎯 Monitor started - WebSocket configured for real-time data!")
        print("📺 Displaying live market data...")
        print()

        # Wait a moment for initial data to arrive
        await asyncio.sleep(1.0)

        # Show initial display
        display.render_full_display()

        # Main monitoring loop - WebSocket only, no REST API calls
        last_render = asyncio.get_event_loop().time()

        while not shutdown_event.is_set():
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=0.1)
                break
            except TimeoutError:
                current_time = asyncio.get_event_loop().time()

                # Render display every 500ms for more responsive UI
                if current_time - last_render >= 0.5:
                    display.render_full_display()
                    last_render = current_time
                continue

    except KeyboardInterrupt:
        display.add_event("Keyboard interrupt received", "SYS")
    except Exception as e:
        display.add_event(f"Monitor error: {e}", "ERR")
        print(f"❌ Monitor error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        try:
            # Cancel the WebSocket background task
            if "websocket_task" in locals() and not websocket_task.done():
                websocket_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await websocket_task

            # Close WebSocket connection
            if "wss" in locals():
                await wss.close()
        except Exception:
            pass
        print("\n✅ Market monitor stopped")


def monitor_command_sync(symbol: str = DEFAULT_SYMBOL, levels: int = 40) -> None:
    """
    Synchronous wrapper for monitor command.

    Args:
        symbol: Trading symbol to monitor
        levels: Number of order book levels to display
    """
    try:
        asyncio.run(monitor_command(symbol, levels))
    except KeyboardInterrupt:
        print("\n✅ Market monitor stopped")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
        sys.exit(1)
