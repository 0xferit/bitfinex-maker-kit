"""
Price value object for trading operations.

Provides type-safe price representation with validation and formatting utilities.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..utilities.constants import PRICE_PRECISION


@dataclass(frozen=True)
class Price:
    """
    Immutable price value object with validation and formatting.

    Ensures all prices are positive and provides consistent formatting
    for display and API operations.
    """

    value: Decimal

    def __init__(self, value: int | float | str | Decimal) -> None:
        """Create Price from various input types."""
        if isinstance(value, Decimal):
            decimal_value = value
        elif isinstance(value, int | float | str):
            try:
                decimal_value = Decimal(str(value))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid price format: {value}") from e
        else:
            raise TypeError(f"Price must be int, float, str, or Decimal, got: {type(value)}")

        if decimal_value <= 0:
            raise ValueError(f"Price must be positive, got: {decimal_value}")

        object.__setattr__(self, "value", decimal_value)

    @classmethod
    def from_float(cls, price: float) -> "Price":
        """Create Price from float value."""
        if price <= 0:
            raise ValueError(f"Price must be positive, got: {price}")
        return cls(Decimal(str(price)))

    @classmethod
    def from_string(cls, price: str) -> "Price":
        """Create Price from string value."""
        try:
            decimal_price = Decimal(price)
            if decimal_price <= 0:
                raise ValueError(f"Price must be positive, got: {price}")
            return cls(decimal_price)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid price format: {price}") from e

    def to_float(self) -> float:
        """Convert to float for API operations."""
        return float(self.value)

    def format_display(self) -> str:
        """Format price for user display."""
        return f"${self.value:.{PRICE_PRECISION}f}"

    def format_api(self) -> str:
        """Format price for API submission."""
        return f"{self.value:.{PRICE_PRECISION}f}"

    def round_to_precision(self) -> "Price":
        """Round price to standard precision."""
        rounded = self.value.quantize(Decimal("0." + "0" * PRICE_PRECISION), rounding=ROUND_HALF_UP)
        return Price(rounded)

    def is_within_spread(self, bid: "Price", ask: "Price") -> bool:
        """Check if this price is within the bid-ask spread."""
        return bid.value < self.value < ask.value

    def distance_from(self, other: "Price") -> Decimal:
        """Calculate absolute distance from another price."""
        return abs(self.value - other.value)

    def percentage_distance_from(self, other: "Price") -> Decimal:
        """Calculate percentage distance from another price."""
        if other.value == 0:
            raise ValueError("Cannot calculate percentage from zero price")
        return (abs(self.value - other.value) / other.value) * 100

    def apply_percentage_change(self, percentage: float) -> "Price":
        """Apply a percentage change to this price."""
        multiplier = Decimal(str(1 + percentage / 100))
        new_value = self.value * multiplier
        return Price(new_value)

    def __str__(self) -> str:
        """String representation."""
        return str(self.value)

    def __lt__(self, other: "Price") -> bool:
        """Less than comparison."""
        return self.value < other.value

    def __le__(self, other: "Price") -> bool:
        """Less than or equal comparison."""
        return self.value <= other.value

    def __gt__(self, other: "Price") -> bool:
        """Greater than comparison."""
        return self.value > other.value

    def __ge__(self, other: "Price") -> bool:
        """Greater than or equal comparison."""
        return self.value >= other.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, Price):
            return self.value == other.value
        return False

    def __ne__(self, other: object) -> bool:
        """Not equal comparison."""
        return not self.__eq__(other)

    def __add__(self, other: "Price") -> "Price":
        """Addition operation."""
        return Price(self.value + other.value)

    def __sub__(self, other: "Price") -> "Price":
        """Subtraction operation."""
        result = self.value - other.value
        return Price(result)

    def __mul__(self, other: Decimal | int | float) -> "Price":
        """Multiplication operation."""
        if isinstance(other, int | float):
            other = Decimal(str(other))
        result = self.value * other
        return Price(result)

    def __truediv__(self, other: Decimal | int | float) -> "Price":
        """Division operation."""
        if isinstance(other, int | float):
            other = Decimal(str(other))
        result = self.value / other
        return Price(result)

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Price('{self.value}')"
