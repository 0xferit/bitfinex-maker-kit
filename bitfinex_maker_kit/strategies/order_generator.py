"""
Order generation strategies for market making.

Pure business logic for calculating order prices and generating
order specifications without side effects or external dependencies.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OrderGenerator:
    """
    Generates orders for market making strategies.

    Responsibilities:
    - Calculate order prices based on center price and spread
    - Generate symmetric order levels
    - Apply side filters for directional strategies
    - Provide pure business logic without side effects
    """

    def __init__(self, levels: int, spread_pct: float, size: float, side_filter: str | None = None):
        """
        Initialize order generator.

        Args:
            levels: Number of price levels on each side
            spread_pct: Spread percentage per level
            size: Order size for each level
            side_filter: Optional side filter ('buy' or 'sell')
        """
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter

        # Validation
        if levels <= 0:
            raise ValueError("Levels must be positive")
        if spread_pct <= 0:
            raise ValueError("Spread percentage must be positive")
        if size <= 0:
            raise ValueError("Size must be positive")
        if side_filter and side_filter not in ["buy", "sell"]:
            raise ValueError("Side filter must be 'buy', 'sell', or None")

    def generate_orders(self, center_price: float) -> list[tuple[str, float, float]]:
        """
        Generate orders around a center price.

        Args:
            center_price: Center price for order generation

        Returns:
            List of (side, amount, price) tuples

        Raises:
            ValueError: If center price is invalid
        """
        if center_price <= 0:
            raise ValueError("Center price must be positive")

        orders = []

        for i in range(1, self.levels + 1):
            # Calculate prices for this level
            level_spread = self.spread_pct * i / 100

            # Buy orders below center price
            if self.side_filter != "sell":
                buy_price = center_price * (1 - level_spread)
                orders.append(("buy", self.size, buy_price))

            # Sell orders above center price
            if self.side_filter != "buy":
                sell_price = center_price * (1 + level_spread)
                orders.append(("sell", self.size, sell_price))

        logger.debug(f"Generated {len(orders)} orders around center price ${center_price:.6f}")
        return orders

    def generate_orders_with_details(self, center_price: float) -> list[dict[str, Any]]:
        """
        Generate orders with detailed information.

        Args:
            center_price: Center price for order generation

        Returns:
            List of order dictionaries with detailed information
        """
        orders = []

        for i in range(1, self.levels + 1):
            level_spread = self.spread_pct * i / 100

            # Buy orders below center price
            if self.side_filter != "sell":
                buy_price = center_price * (1 - level_spread)
                distance_pct = -self.spread_pct * i

                orders.append(
                    {
                        "side": "buy",
                        "amount": self.size,
                        "price": buy_price,
                        "level": i,
                        "spread_pct": level_spread * 100,
                        "distance_from_center": distance_pct,
                        "center_price": center_price,
                    }
                )

            # Sell orders above center price
            if self.side_filter != "buy":
                sell_price = center_price * (1 + level_spread)
                distance_pct = self.spread_pct * i

                orders.append(
                    {
                        "side": "sell",
                        "amount": self.size,
                        "price": sell_price,
                        "level": i,
                        "spread_pct": level_spread * 100,
                        "distance_from_center": distance_pct,
                        "center_price": center_price,
                    }
                )

        return orders

    def calculate_level_prices(self, center_price: float, level: int) -> tuple[float, float]:
        """
        Calculate buy and sell prices for a specific level.

        Args:
            center_price: Center price
            level: Level number (1-based)

        Returns:
            Tuple of (buy_price, sell_price)
        """
        if level <= 0 or level > self.levels:
            raise ValueError(f"Level must be between 1 and {self.levels}")

        level_spread = self.spread_pct * level / 100
        buy_price = center_price * (1 - level_spread)
        sell_price = center_price * (1 + level_spread)

        return buy_price, sell_price

    def get_price_range(self, center_price: float) -> tuple[float, float]:
        """
        Get the full price range covered by all levels.

        Args:
            center_price: Center price

        Returns:
            Tuple of (lowest_buy_price, highest_sell_price)
        """
        max_spread = self.spread_pct * self.levels / 100
        lowest_price = center_price * (1 - max_spread)
        highest_price = center_price * (1 + max_spread)

        return lowest_price, highest_price

    def validate_center_price_range(
        self, center_price: float, min_price: float, max_price: float
    ) -> bool:
        """
        Validate that all generated orders would be within price bounds.

        Args:
            center_price: Center price to validate
            min_price: Minimum allowed price
            max_price: Maximum allowed price

        Returns:
            True if all orders would be within bounds
        """
        lowest_price, highest_price = self.get_price_range(center_price)
        return lowest_price >= min_price and highest_price <= max_price

    def suggest_center_price(self, bid: float, ask: float, preference: str = "mid") -> float:
        """
        Suggest an appropriate center price based on market data.

        Args:
            bid: Best bid price
            ask: Best ask price
            preference: Preference for center calculation ('mid', 'bid', 'ask')

        Returns:
            Suggested center price
        """
        if bid <= 0 or ask <= 0 or bid >= ask:
            raise ValueError("Invalid bid/ask prices")

        if preference == "mid":
            return (bid + ask) / 2
        elif preference == "bid":
            # Slightly above bid
            return bid * 1.001
        elif preference == "ask":
            # Slightly below ask
            return ask * 0.999
        else:
            raise ValueError("Preference must be 'mid', 'bid', or 'ask'")

    def calculate_total_capital_required(self, center_price: float) -> dict[str, float]:
        """
        Calculate total capital required for all orders.

        Args:
            center_price: Center price

        Returns:
            Dictionary with capital requirements
        """
        orders = self.generate_orders(center_price)

        buy_capital = 0.0
        sell_capital = 0.0
        buy_count = 0
        sell_count = 0

        for side, amount, price in orders:
            if side == "buy":
                buy_capital += amount * price
                buy_count += 1
            else:  # sell
                sell_capital += amount  # In base currency
                sell_count += 1

        return {
            "buy_capital_quote": buy_capital,  # Quote currency needed for buys
            "sell_capital_base": sell_capital,  # Base currency needed for sells
            "buy_orders": buy_count,
            "sell_orders": sell_count,
            "total_orders": buy_count + sell_count,
        }

    def get_configuration(self) -> dict[str, Any]:
        """
        Get current generator configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "levels": self.levels,
            "spread_pct": self.spread_pct,
            "size": self.size,
            "side_filter": self.side_filter,
            "max_spread_pct": self.spread_pct * self.levels,
        }

    def update_configuration(
        self,
        levels: int | None = None,
        spread_pct: float | None = None,
        size: float | None = None,
        side_filter: str | None = None,
    ) -> None:
        """
        Update generator configuration.

        Args:
            levels: New levels value
            spread_pct: New spread percentage
            size: New size value
            side_filter: New side filter
        """
        if levels is not None:
            if levels <= 0:
                raise ValueError("Levels must be positive")
            self.levels = levels

        if spread_pct is not None:
            if spread_pct <= 0:
                raise ValueError("Spread percentage must be positive")
            self.spread_pct = spread_pct

        if size is not None:
            if size <= 0:
                raise ValueError("Size must be positive")
            self.size = size

        if side_filter is not None:
            if side_filter not in ["buy", "sell", None]:
                raise ValueError("Side filter must be 'buy', 'sell', or None")
            self.side_filter = side_filter

        logger.info(
            f"Updated configuration: levels={self.levels}, spread={self.spread_pct}%, size={self.size}, filter={self.side_filter}"
        )

    def copy_with_modifications(self, **kwargs: Any) -> "OrderGenerator":
        """
        Create a copy of this generator with modifications.

        Args:
            **kwargs: Configuration overrides

        Returns:
            New OrderGenerator instance
        """
        config = self.get_configuration()
        config.update(kwargs)

        return OrderGenerator(
            levels=config["levels"],
            spread_pct=config["spread_pct"],
            size=config["size"],
            side_filter=config["side_filter"],
        )
