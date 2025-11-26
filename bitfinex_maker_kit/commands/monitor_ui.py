"""
Rich-based terminal UI for the market monitor.

Provides a professional trading terminal interface with:
- Visual order book depth with colored bars
- Real-time trade feed
- Connection status indicators
- User orders panel
"""

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .. import __version__

if TYPE_CHECKING:
    from .monitor_display import MonitorDisplay


class MonitorUI:
    """Rich-based terminal UI for market monitoring."""

    COLORS: ClassVar[dict[str, str]] = {
        "bid": "#00d26a",  # Bright green for bids
        "bid_bar": "#00a854",  # Darker green for depth bars
        "ask": "#ff6b6b",  # Bright red for asks
        "ask_bar": "#cc5555",  # Darker red for depth bars
        "price": "#ffd93d",  # Yellow for prices
        "header": "#00d4ff",  # Cyan for headers
        "muted": "#6c757d",  # Gray for secondary text
        "success": "#00d26a",  # Green checkmark
        "error": "#ff6b6b",  # Red X
        "warning": "#ffa500",  # Orange for warnings
    }

    def __init__(self, display: "MonitorDisplay"):
        self.display = display
        self.console = Console()
        self.live: Live | None = None

    def start(self) -> Live:
        """Start the live display."""
        self.live = Live(
            self._build_layout(),
            console=self.console,
            refresh_per_second=10,
            screen=True,
        )
        return self.live

    def refresh(self) -> None:
        """Refresh the display with current data."""
        if self.live:
            self.live.update(self._build_layout())

    def _build_layout(self) -> Layout:
        """Build the complete UI layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )

        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="center", ratio=2),
            Layout(name="right", ratio=1),
        )

        layout["header"].update(self._build_header())
        layout["left"].update(self._build_status_panel())
        layout["center"].update(self._build_order_book())
        layout["right"].update(self._build_trades_panel())
        layout["footer"].update(self._build_footer())

        return layout

    def _build_header(self) -> Panel:
        """Build the header panel with price and market metrics."""
        d = self.display
        price = d.last_price if d.last_price > 0 else d.mid_price
        spread = d.get_spread()
        liq_bid, liq_ask = d.get_liquidity_2pct()

        # Calculate USD values
        liq_bid_usd = liq_ask_usd = 0.0
        if d.mid_price > 0:
            threshold = d.mid_price * 0.02
            for bid in d.order_book["bids"]:
                if len(bid) >= 2 and abs(float(bid[0]) - d.mid_price) <= threshold:
                    liq_bid_usd += float(bid[1]) * float(bid[0])
            for ask in d.order_book["asks"]:
                if len(ask) >= 2 and abs(float(ask[0]) - d.mid_price) <= threshold:
                    liq_ask_usd += float(ask[1]) * float(ask[0])

        header_text = Text()
        header_text.append(f"  {d.symbol}  ", style=f"bold {self.COLORS['header']}")
        header_text.append("│ ", style=self.COLORS["muted"])

        if price > 0:
            header_text.append("LAST ", style=self.COLORS["muted"])
            header_text.append(f"{price:,.4f}", style=f"bold {self.COLORS['price']}")
            header_text.append("  │ ", style=self.COLORS["muted"])
            header_text.append("SPREAD ", style=self.COLORS["muted"])
            header_text.append(f"{spread:.3f}%", style=self.COLORS["price"])
            header_text.append("  │ ", style=self.COLORS["muted"])
            header_text.append("LIQ±2% ", style=self.COLORS["muted"])
            header_text.append(f"{liq_bid:.1f}", style=self.COLORS["bid"])
            header_text.append("/", style=self.COLORS["muted"])
            header_text.append(f"{liq_ask:.1f}", style=self.COLORS["ask"])
            header_text.append(f" {d.base_currency} ", style=self.COLORS["muted"])
            header_text.append("(", style=self.COLORS["muted"])
            header_text.append(self._fmt_usd(liq_bid_usd), style=self.COLORS["bid"])
            header_text.append("/", style=self.COLORS["muted"])
            header_text.append(self._fmt_usd(liq_ask_usd), style=self.COLORS["ask"])
            header_text.append(")", style=self.COLORS["muted"])
        else:
            header_text.append("Waiting for data...", style=self.COLORS["muted"])

        time_text = Text(datetime.now().strftime("%H:%M:%S"), style=self.COLORS["muted"])

        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=1)
        table.add_column(justify="right")
        table.add_row(header_text, time_text)

        return Panel(table, style=self.COLORS["header"], border_style=self.COLORS["header"])

    def _build_status_panel(self) -> Panel:
        """Build connection status panel."""
        stats = self.display.connection_stats

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style=self.COLORS["muted"])
        table.add_column("Status", justify="right")

        # Connection indicators
        connections = [
            ("Book", stats["book_channel"]),
            ("Trades", stats["trades_channel"]),
            ("Ticker", stats["ticker_channel"]),
            ("Auth", stats["authenticated"]),
        ]

        for label, connected in connections:
            icon = "●" if connected else "○"
            color = self.COLORS["success"] if connected else self.COLORS["error"]
            table.add_row(label, Text(icon, style=color))

        table.add_row("", "")  # spacer

        # Stats
        table.add_row("Trades", Text(str(stats["total_trades"]), style="white"))
        table.add_row("Book Upd", Text(str(stats["total_book_updates"]), style="white"))
        table.add_row(
            "My Orders", Text(str(stats["user_orders_count"]), style=self.COLORS["price"])
        )
        table.add_row(
            "In Range", Text(str(stats["user_orders_in_range"]), style=self.COLORS["bid"])
        )

        return Panel(table, title="[bold]STATUS", border_style=self.COLORS["muted"])

    def _build_order_book(self) -> Panel:
        """Build the order book panel with visual depth bars."""
        d = self.display
        bids = d.order_book.get("bids", [])
        asks = d.order_book.get("asks", [])

        if not bids and not asks:
            return Panel(
                Align.center(Text("Waiting for order book...", style=self.COLORS["muted"])),
                title="[bold]ORDER BOOK",
                border_style=self.COLORS["muted"],
            )

        # Find max volume for scaling bars
        max_vol = 1.0
        for order in bids[:20] + asks[:20]:
            if len(order) >= 2:
                max_vol = max(max_vol, abs(float(order[1])))

        # Build order book table
        table = Table(box=None, show_header=True, header_style=self.COLORS["muted"], padding=(0, 1))
        table.add_column("Bid Vol", justify="right", width=10)
        table.add_column("Bid", justify="center", width=6)
        table.add_column("Price", justify="center", width=12, style=self.COLORS["price"])
        table.add_column("Ask", justify="center", width=6)
        table.add_column("Ask Vol", justify="left", width=10)

        # Show top 15 levels each side
        levels = min(15, max(len(bids), len(asks)))

        # Reverse asks so highest ask is at top
        asks_display = asks[:levels]

        for i in range(levels):
            bid = bids[i] if i < len(bids) else None
            ask = asks_display[i] if i < len(asks_display) else None

            bid_vol_str = ""
            bid_bar = ""
            price_str = ""
            ask_bar = ""
            ask_vol_str = ""

            if bid:
                bid_vol = abs(float(bid[1]))
                bid_vol_str = f"{bid_vol:.3f}"
                bar_len = int((bid_vol / max_vol) * 6)
                bid_bar = "█" * bar_len

            if ask:
                ask_vol = abs(float(ask[1]))
                ask_vol_str = f"{ask_vol:.3f}"
                bar_len = int((ask_vol / max_vol) * 6)
                ask_bar = "█" * bar_len

            # Price column shows mid price in the middle
            if bid and ask:
                if i == levels // 2 and d.mid_price > 0:
                    price_str = f"─{d.mid_price:,.2f}─"
                else:
                    price_str = f"{float(bid[0]):,.2f}" if bid else ""
            elif bid:
                price_str = f"{float(bid[0]):,.2f}"
            elif ask:
                price_str = f"{float(ask[0]):,.2f}"

            table.add_row(
                Text(bid_vol_str, style=self.COLORS["bid"]),
                Text(bid_bar, style=self.COLORS["bid_bar"]),
                price_str,
                Text(ask_bar, style=self.COLORS["ask_bar"]),
                Text(ask_vol_str, style=self.COLORS["ask"]),
            )

        return Panel(table, title="[bold]ORDER BOOK", border_style=self.COLORS["muted"])

    def _build_trades_panel(self) -> Panel:
        """Build recent trades panel."""
        trades = list(self.display.recent_trades)

        if not trades:
            return Panel(
                Align.center(Text("Waiting for trades...", style=self.COLORS["muted"])),
                title="[bold]TRADES",
                border_style=self.COLORS["muted"],
            )

        table = Table(box=None, show_header=True, header_style=self.COLORS["muted"], padding=(0, 1))
        table.add_column("Time", width=8)
        table.add_column("Side", width=4)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Price", justify="right", width=10)

        # Show most recent trades first (up to 12)
        for trade in reversed(trades[-12:]):
            amount = trade.get("amount", 0)
            price = trade.get("price", 0)
            timestamp = trade.get("timestamp", 0)

            # Format timestamp
            if isinstance(timestamp, int | float) and timestamp > 0:
                time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%H:%M:%S")
            else:
                time_str = "--:--:--"

            is_buy = amount > 0
            side_str = "BUY" if is_buy else "SELL"
            color = self.COLORS["bid"] if is_buy else self.COLORS["ask"]

            table.add_row(
                Text(time_str, style=self.COLORS["muted"]),
                Text(side_str, style=color),
                Text(f"{abs(amount):.4f}", style=color),
                Text(f"{price:,.2f}", style=self.COLORS["price"]),
            )

        return Panel(table, title="[bold]TRADES", border_style=self.COLORS["muted"])

    def _build_footer(self) -> Text:
        """Build footer with version and controls."""
        import time

        uptime = int(time.time() - self.display.start_time)
        uptime_str = f"{uptime // 60}m {uptime % 60}s"

        footer = Text()
        footer.append(f" v{__version__}", style=self.COLORS["muted"])
        footer.append(" │ ", style=self.COLORS["muted"])
        footer.append(f"Uptime: {uptime_str}", style=self.COLORS["muted"])
        footer.append(" │ ", style=self.COLORS["muted"])
        footer.append("Ctrl+C", style=self.COLORS["warning"])
        footer.append(" to exit", style=self.COLORS["muted"])

        return footer

    def _fmt_usd(self, amount: float) -> str:
        """Format USD amount with K/M suffix."""
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        if amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        return f"${amount:.0f}"


def create_simple_display(display: "MonitorDisplay") -> Group:
    """Create a simple Rich display for non-live rendering fallback."""
    ui = MonitorUI(display)
    return Group(ui._build_layout())
