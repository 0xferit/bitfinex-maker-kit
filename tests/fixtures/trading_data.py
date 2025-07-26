"""
Trading data fixtures for testing.

Provides realistic trading scenarios, order data, and portfolio
states for comprehensive trading system testing.
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrderStatus(Enum):
    """Order status enumeration."""

    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderFixture:
    """Fixture for order data."""

    id: int
    symbol: str
    amount: str
    price: str
    side: str
    order_type: str = "EXCHANGE LIMIT"
    status: str = "ACTIVE"
    timestamp: float = field(default_factory=time.time)
    flags: int = 512  # POST_ONLY flag
    amount_orig: str | None = None
    executed_amount: str = "0.0"
    avg_execution_price: str | None = None
    client_order_id: str | None = None

    def __post_init__(self):
        """Initialize derived fields."""
        if self.amount_orig is None:
            self.amount_orig = self.amount

        # Generate client order ID if not provided
        if self.client_order_id is None:
            self.client_order_id = f"client_{self.id}_{int(self.timestamp)}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "amount": self.amount,
            "price": self.price,
            "side": self.side,
            "type": self.order_type,
            "status": self.status,
            "timestamp": self.timestamp,
            "flags": self.flags,
            "amount_orig": self.amount_orig,
            "executed_amount": self.executed_amount,
            "avg_execution_price": self.avg_execution_price,
            "client_order_id": self.client_order_id,
        }

    def mark_executed(self, execution_price: str | None = None) -> "OrderFixture":
        """Mark order as executed."""
        return OrderFixture(
            id=self.id,
            symbol=self.symbol,
            amount=self.amount,
            price=self.price,
            side=self.side,
            order_type=self.order_type,
            status=OrderStatus.EXECUTED.value,
            timestamp=self.timestamp,
            flags=self.flags,
            amount_orig=self.amount_orig,
            executed_amount=self.amount_orig,
            avg_execution_price=execution_price or self.price,
            client_order_id=self.client_order_id,
        )

    def mark_partially_filled(self, filled_amount: str, execution_price: str) -> "OrderFixture":
        """Mark order as partially filled."""
        remaining_amount = str(float(self.amount) - float(filled_amount))

        return OrderFixture(
            id=self.id,
            symbol=self.symbol,
            amount=remaining_amount,
            price=self.price,
            side=self.side,
            order_type=self.order_type,
            status=OrderStatus.PARTIALLY_FILLED.value,
            timestamp=self.timestamp,
            flags=self.flags,
            amount_orig=self.amount_orig,
            executed_amount=filled_amount,
            avg_execution_price=execution_price,
            client_order_id=self.client_order_id,
        )

    def mark_canceled(self) -> "OrderFixture":
        """Mark order as canceled."""
        return OrderFixture(
            id=self.id,
            symbol=self.symbol,
            amount=self.amount,
            price=self.price,
            side=self.side,
            order_type=self.order_type,
            status=OrderStatus.CANCELED.value,
            timestamp=self.timestamp,
            flags=self.flags,
            amount_orig=self.amount_orig,
            executed_amount=self.executed_amount,
            avg_execution_price=self.avg_execution_price,
            client_order_id=self.client_order_id,
        )


@dataclass
class BalanceFixture:
    """Fixture for account balance data."""

    currency: str
    balance_type: str = "exchange"
    balance: float = 0.0
    available: float = 0.0

    def __post_init__(self):
        """Initialize available balance if not set."""
        if self.available == 0.0 and self.balance > 0.0:
            # Available is typically 95% of total balance
            self.available = self.balance * 0.95

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "currency": self.currency,
            "type": self.balance_type,
            "balance": self.balance,
            "available": self.available,
        }

    def with_reserved(self, reserved_amount: float) -> "BalanceFixture":
        """Create balance with reserved amount."""
        return BalanceFixture(
            currency=self.currency,
            balance_type=self.balance_type,
            balance=self.balance,
            available=max(0.0, self.balance - reserved_amount),
        )


@dataclass
class PortfolioFixture:
    """Fixture for portfolio data."""

    balances: list[BalanceFixture] = field(default_factory=list)
    orders: list[OrderFixture] = field(default_factory=list)
    total_value_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "balances": [balance.to_dict() for balance in self.balances],
            "orders": [order.to_dict() for order in self.orders],
            "total_value_usd": self.total_value_usd,
        }

    def get_balance(self, currency: str) -> BalanceFixture | None:
        """Get balance for specific currency."""
        for balance in self.balances:
            if balance.currency == currency:
                return balance
        return None

    def get_orders_by_symbol(self, symbol: str) -> list[OrderFixture]:
        """Get orders for specific symbol."""
        return [order for order in self.orders if order.symbol == symbol]

    def get_active_orders(self) -> list[OrderFixture]:
        """Get active orders."""
        return [order for order in self.orders if order.status == OrderStatus.ACTIVE.value]


class TradingFixtures:
    """
    Factory class for creating comprehensive trading data fixtures.

    Provides realistic trading scenarios for testing order management,
    portfolio tracking, and trading strategies.
    """

    @classmethod
    def create_order(
        cls, order_id: int | None = None, symbol: str = "tBTCUSD", side: str = "buy", **kwargs
    ) -> OrderFixture:
        """Create order fixture."""
        if order_id is None:
            order_id = random.randint(10000000, 99999999)

        # Default values based on side
        if side == "buy":
            defaults = {"amount": "0.1", "price": "49000.0"}
        else:  # sell
            defaults = {"amount": "0.1", "price": "51000.0"}

        defaults.update({"id": order_id, "symbol": symbol, "side": side})
        defaults.update(kwargs)

        return OrderFixture(**defaults)

    @classmethod
    def create_balance(
        cls, currency: str = "USD", balance: float = 10000.0, **kwargs
    ) -> BalanceFixture:
        """Create balance fixture."""
        defaults = {"currency": currency, "balance": balance}
        defaults.update(kwargs)

        return BalanceFixture(**defaults)

    @classmethod
    def create_portfolio(cls, currencies: list[str] | None = None) -> PortfolioFixture:
        """Create portfolio fixture."""
        if currencies is None:
            currencies = ["USD", "BTC", "ETH", "PNK"]

        balances = []

        # Default balances
        balance_defaults = {"USD": 10000.0, "BTC": 1.0, "ETH": 10.0, "PNK": 1000.0}

        for currency in currencies:
            balance_amount = balance_defaults.get(currency, 100.0)
            balances.append(cls.create_balance(currency, balance_amount))

        return PortfolioFixture(balances=balances)

    @classmethod
    def create_market_making_orders(
        cls,
        symbol: str = "tBTCUSD",
        center_price: float = 50000.0,
        levels: int = 3,
        spread_pct: float = 0.1,
    ) -> list[OrderFixture]:
        """Create market making order set."""
        orders = []
        order_id = random.randint(10000000, 99999999)

        for level in range(1, levels + 1):
            # Buy orders (below center)
            buy_price = center_price * (1 - (spread_pct / 100) * level)
            buy_order = cls.create_order(
                order_id=order_id, symbol=symbol, side="buy", amount="0.1", price=f"{buy_price:.2f}"
            )
            orders.append(buy_order)
            order_id += 1

            # Sell orders (above center)
            sell_price = center_price * (1 + (spread_pct / 100) * level)
            sell_order = cls.create_order(
                order_id=order_id,
                symbol=symbol,
                side="sell",
                amount="0.1",
                price=f"{sell_price:.2f}",
            )
            orders.append(sell_order)
            order_id += 1

        return orders

    @classmethod
    def create_order_execution_scenario(cls) -> dict[str, list[OrderFixture]]:
        """Create order execution scenario."""
        base_order = cls.create_order(12345678, "tBTCUSD", "buy", amount="1.0", price="50000.0")

        return {
            "pending": [base_order],
            "partially_filled": [base_order.mark_partially_filled("0.3", "49995.0")],
            "executed": [base_order.mark_executed("49990.0")],
            "canceled": [base_order.mark_canceled()],
        }

    @classmethod
    def create_trading_history(cls, symbol: str = "tBTCUSD", days: int = 7) -> list[OrderFixture]:
        """Create trading history fixture."""
        orders = []
        current_time = time.time()
        order_id = 10000000

        # Generate orders over the specified period
        for day in range(days):
            day_start = current_time - (day * 24 * 3600)

            # Generate 5-10 orders per day
            daily_orders = random.randint(5, 10)

            for _ in range(daily_orders):
                # Random order parameters
                side = random.choice(["buy", "sell"])
                amount = round(random.uniform(0.01, 1.0), 6)
                base_price = 50000.0 + random.uniform(-5000, 5000)

                # Random execution status
                status = random.choices(
                    [OrderStatus.EXECUTED, OrderStatus.CANCELED, OrderStatus.PARTIALLY_FILLED],
                    weights=[70, 20, 10],
                )[0]

                order = cls.create_order(
                    order_id=order_id,
                    symbol=symbol,
                    side=side,
                    amount=str(amount),
                    price=f"{base_price:.2f}",
                    status=status.value,
                    timestamp=day_start + random.uniform(0, 24 * 3600),
                )

                # Set execution details for executed/partially filled orders
                if status == OrderStatus.EXECUTED:
                    order.executed_amount = order.amount_orig
                    order.avg_execution_price = order.price
                elif status == OrderStatus.PARTIALLY_FILLED:
                    filled_pct = random.uniform(0.1, 0.9)
                    order.executed_amount = str(float(order.amount_orig) * filled_pct)
                    order.avg_execution_price = order.price

                orders.append(order)
                order_id += 1

        return sorted(orders, key=lambda x: x.timestamp, reverse=True)

    @classmethod
    def create_stress_test_scenario(cls) -> dict[str, Any]:
        """Create stress test scenario with many orders."""
        return {
            "high_frequency_orders": [
                cls.create_order(
                    order_id=1000000 + i,
                    symbol="tBTCUSD",
                    side=random.choice(["buy", "sell"]),
                    amount=str(random.uniform(0.001, 0.1)),
                    price=str(50000 + random.uniform(-1000, 1000)),
                )
                for i in range(1000)
            ],
            "large_orders": [
                cls.create_order(
                    order_id=2000000 + i,
                    symbol="tBTCUSD",
                    side=random.choice(["buy", "sell"]),
                    amount=str(random.uniform(10, 100)),
                    price=str(50000 + random.uniform(-5000, 5000)),
                )
                for i in range(50)
            ],
            "multi_symbol_orders": [
                cls.create_order(
                    order_id=3000000 + i,
                    symbol=random.choice(["tBTCUSD", "tETHUSD", "tPNKUSD"]),
                    side=random.choice(["buy", "sell"]),
                    amount=str(random.uniform(0.1, 5.0)),
                    price=str(random.uniform(100, 60000)),
                )
                for i in range(200)
            ],
        }

    @classmethod
    def create_edge_case_orders(cls) -> dict[str, OrderFixture]:
        """Create edge case order scenarios."""
        return {
            "minimum_amount": cls.create_order(
                symbol="tBTCUSD",
                amount="0.00000001",  # Minimum amount
                price="50000.0",
            ),
            "maximum_amount": cls.create_order(
                symbol="tBTCUSD",
                amount="1000.0",  # Large amount
                price="50000.0",
            ),
            "very_low_price": cls.create_order(symbol="tBTCUSD", amount="0.1", price="0.01"),
            "very_high_price": cls.create_order(symbol="tBTCUSD", amount="0.1", price="1000000.0"),
            "old_order": cls.create_order(
                symbol="tBTCUSD",
                timestamp=time.time() - 86400,  # 24 hours old
            ),
        }
