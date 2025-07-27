"""
Market data fixtures for testing.

Provides realistic market data scenarios for comprehensive testing
of market data processing, caching, and trading operations.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class TickerDataFixture:
    """Fixture for ticker data."""

    symbol: str
    bid: float
    ask: float
    last_price: float
    bid_size: float = 1.0
    ask_size: float = 1.0
    volume: float = 1000.0
    high: float = 0.0
    low: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Calculate derived fields."""
        if self.high == 0.0:
            self.high = max(self.bid, self.ask, self.last_price) * 1.02
        if self.low == 0.0:
            self.low = min(self.bid, self.ask, self.last_price) * 0.98

        # Calculate change from midpoint
        mid_price = (self.bid + self.ask) / 2
        self.change = self.last_price - mid_price
        if mid_price > 0:
            self.change_pct = (self.change / mid_price) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "last_price": self.last_price,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "volume": self.volume,
            "high": self.high,
            "low": self.low,
            "change": self.change,
            "change_pct": self.change_pct,
            "timestamp": self.timestamp,
        }

    def with_spread_pct(self, spread_pct: float) -> "TickerDataFixture":
        """Create ticker with specific spread percentage."""
        mid_price = self.last_price
        spread = mid_price * (spread_pct / 100)

        return TickerDataFixture(
            symbol=self.symbol,
            bid=mid_price - spread / 2,
            ask=mid_price + spread / 2,
            last_price=self.last_price,
            bid_size=self.bid_size,
            ask_size=self.ask_size,
            volume=self.volume,
            timestamp=self.timestamp,
        )


@dataclass
class OrderBookFixture:
    """Fixture for order book data."""

    symbol: str
    bids: list[list[float]] = field(default_factory=list)
    asks: list[list[float]] = field(default_factory=list)
    precision: str = "P0"
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Generate realistic order book if empty."""
        if not self.bids and not self.asks:
            self._generate_realistic_book()

    def _generate_realistic_book(self, base_price: float = 50000.0, levels: int = 10):
        """Generate realistic order book data."""
        # Generate bids (decreasing prices)
        self.bids = []
        for i in range(levels):
            price = base_price * (1 - (i + 1) * 0.0001)  # 0.01% spread per level
            amount = random.uniform(0.1, 5.0)
            self.bids.append([price, amount])

        # Generate asks (increasing prices)
        self.asks = []
        for i in range(levels):
            price = base_price * (1 + (i + 1) * 0.0001)  # 0.01% spread per level
            amount = random.uniform(0.1, 5.0)
            self.asks.append([price, amount])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "symbol": self.symbol,
            "bids": self.bids,
            "asks": self.asks,
            "precision": self.precision,
            "timestamp": self.timestamp,
        }

    def get_best_bid(self) -> float | None:
        """Get best bid price."""
        return self.bids[0][0] if self.bids else None

    def get_best_ask(self) -> float | None:
        """Get best ask price."""
        return self.asks[0][0] if self.asks else None

    def get_spread(self) -> float | None:
        """Get bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None

    def get_mid_price(self) -> float | None:
        """Get mid price."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None


@dataclass
class TradeHistoryFixture:
    """Fixture for trade history data."""

    symbol: str
    trades: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Generate realistic trade history if empty."""
        if not self.trades:
            self._generate_realistic_trades()

    def _generate_realistic_trades(self, count: int = 50, base_price: float = 50000.0):
        """Generate realistic trade history."""
        current_time = time.time()
        current_price = base_price

        for i in range(count):
            # Random price movement
            price_change = random.uniform(-0.001, 0.001)  # ±0.1% per trade
            current_price *= 1 + price_change

            # Random trade size and side
            amount = random.uniform(0.01, 2.0)
            side = random.choice(["buy", "sell"])
            if side == "sell":
                amount = -amount

            trade = {
                "id": 1000000 + i,
                "timestamp": current_time - (count - i) * 60,  # 1 minute intervals
                "price": round(current_price, 2),
                "amount": round(amount, 6),
                "side": side,
            }
            self.trades.append(trade)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {"symbol": self.symbol, "trades": self.trades}

    def get_recent_trades(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most recent trades."""
        return sorted(self.trades, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_volume_weighted_price(self, duration: float = 3600.0) -> float | None:
        """Calculate VWAP for specified duration."""
        cutoff_time = time.time() - duration
        recent_trades = [t for t in self.trades if t["timestamp"] >= cutoff_time]

        if not recent_trades:
            return None

        total_value = sum(t["price"] * abs(t["amount"]) for t in recent_trades)
        total_volume = sum(abs(t["amount"]) for t in recent_trades)

        return total_value / total_volume if total_volume > 0 else None


class MarketDataFixtures:
    """
    Factory class for creating comprehensive market data fixtures.

    Provides realistic market data scenarios for testing various
    market conditions and edge cases.
    """

    SYMBOLS: ClassVar[list[str]] = ["tBTCUSD", "tETHUSD", "tPNKUSD", "tLTCUSD", "tXRPUSD"]

    BASE_PRICES: ClassVar[dict[str, float]] = {
        "tBTCUSD": 50000.0,
        "tETHUSD": 3000.0,
        "tPNKUSD": 0.5,
        "tLTCUSD": 150.0,
        "tXRPUSD": 0.6,
    }

    @classmethod
    def create_ticker(cls, symbol: str = "tBTCUSD", **kwargs) -> TickerDataFixture:
        """Create ticker data fixture."""
        base_price = cls.BASE_PRICES.get(symbol, 1000.0)

        defaults = {
            "symbol": symbol,
            "last_price": base_price,
            "bid": base_price * 0.9995,
            "ask": base_price * 1.0005,
            "volume": random.uniform(500, 5000),
        }
        defaults.update(kwargs)

        return TickerDataFixture(**defaults)

    @classmethod
    def create_orderbook(cls, symbol: str = "tBTCUSD", **kwargs) -> OrderBookFixture:
        """Create order book fixture."""
        defaults = {"symbol": symbol}
        defaults.update(kwargs)

        fixture = OrderBookFixture(**defaults)

        # Generate realistic book based on symbol
        if symbol in cls.BASE_PRICES:
            base_price = cls.BASE_PRICES[symbol]
            fixture._generate_realistic_book(base_price)

        return fixture

    @classmethod
    def create_trade_history(cls, symbol: str = "tBTCUSD", **kwargs) -> TradeHistoryFixture:
        """Create trade history fixture."""
        defaults = {"symbol": symbol}
        defaults.update(kwargs)

        fixture = TradeHistoryFixture(**defaults)

        # Generate realistic trades based on symbol
        if symbol in cls.BASE_PRICES:
            base_price = cls.BASE_PRICES[symbol]
            fixture._generate_realistic_trades(base_price=base_price)

        return fixture

    @classmethod
    def create_market_snapshot(cls, symbol: str = "tBTCUSD") -> dict[str, Any]:
        """Create complete market data snapshot."""
        ticker = cls.create_ticker(symbol)
        orderbook = cls.create_orderbook(symbol)
        trades = cls.create_trade_history(symbol)

        return {
            "ticker": ticker.to_dict(),
            "orderbook": orderbook.to_dict(),
            "trades": trades.to_dict(),
            "timestamp": time.time(),
        }

    @classmethod
    def create_multi_symbol_snapshot(
        cls, symbols: list[str] | None = None
    ) -> dict[str, dict[str, Any]]:
        """Create market snapshot for multiple symbols."""
        if symbols is None:
            symbols = cls.SYMBOLS

        snapshot = {}
        for symbol in symbols:
            snapshot[symbol] = cls.create_market_snapshot(symbol)

        return snapshot

    @classmethod
    def create_volatile_market(
        cls, symbol: str = "tBTCUSD", volatility: float = 0.02
    ) -> TickerDataFixture:
        """Create ticker data with high volatility."""
        ticker = cls.create_ticker(symbol)

        # Increase spread based on volatility
        spread_pct = volatility * 100  # Convert to percentage
        return ticker.with_spread_pct(spread_pct)

    @classmethod
    def create_thin_orderbook(cls, symbol: str = "tBTCUSD", levels: int = 3) -> OrderBookFixture:
        """Create thin order book (low liquidity)."""
        orderbook = cls.create_orderbook(symbol)
        orderbook._generate_realistic_book(levels=levels)

        # Reduce amounts to simulate thin book
        for bid in orderbook.bids:
            bid[1] *= 0.1  # Reduce amounts by 90%
        for ask in orderbook.asks:
            ask[1] *= 0.1

        return orderbook

    @classmethod
    def create_market_stress_scenario(cls) -> dict[str, Any]:
        """Create market stress scenario for testing."""
        return {
            "high_volatility": cls.create_volatile_market("tBTCUSD", volatility=0.05),
            "thin_orderbook": cls.create_thin_orderbook("tETHUSD", levels=2),
            "wide_spread": cls.create_ticker("tPNKUSD").with_spread_pct(2.0),
            "low_volume": cls.create_ticker("tLTCUSD", volume=10.0),
            "timestamp": time.time(),
        }
