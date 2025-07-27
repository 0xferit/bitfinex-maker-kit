"""
OrderId value object for order identification.

Provides type-safe order ID representation with validation and utilities.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrderId:
    """
    Immutable order ID value object with validation.

    Handles both real order IDs from the exchange and placeholder IDs
    generated locally when order ID extraction fails.
    """

    value: int
    is_placeholder: bool = False
    original_string: str | None = None  # Store original string for placeholder IDs

    def __post_init__(self) -> None:
        """Validate the OrderId after initialization."""
        if self.value <= 0:
            raise ValueError(f"Order ID must be positive, got: {self.value}")

        # Validate real order IDs have proper range
        if not self.is_placeholder and (self.value < 10000000 or self.value > 99999999):
            raise ValueError(f"Order ID must be between 10000000 and 99999999, got: {self.value}")

    def __init__(self, value: int | str, is_placeholder: bool = False) -> None:
        """Create OrderId from various input types."""
        if value is None:
            raise ValueError("Order ID cannot be None")

        processed_value: int
        processed_is_placeholder: bool = is_placeholder
        processed_original_string: str | None = None

        # Convert string to int if it's a valid numeric string
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("String order ID cannot be empty")

            # Try to convert to int if it's numeric and not a placeholder
            if not is_placeholder and value.isdigit():
                int_value = int(value)
                if int_value < 10000000 or int_value > 99999999:
                    raise ValueError(
                        f"Order ID must be between 10000000 and 99999999, got: {int_value}"
                    )
                processed_value = int_value
                processed_is_placeholder = False
                processed_original_string = None
            elif is_placeholder:
                # For placeholder IDs, store the original string and use hash as int value
                hash_value = abs(hash(value)) % 1000000000  # Ensure it's within reasonable range
                processed_value = hash_value
                processed_is_placeholder = True
                processed_original_string = value
            else:
                raise ValueError(f"Invalid order ID format: {value}")
        elif isinstance(value, int):
            if value <= 0:
                raise ValueError(f"Integer order ID must be positive, got: {value}")
            if not is_placeholder and (value < 10000000 or value > 99999999):
                raise ValueError(f"Order ID must be between 10000000 and 99999999, got: {value}")
            processed_value = value
            processed_is_placeholder = is_placeholder
            processed_original_string = None
        else:
            raise TypeError(f"Order ID must be int or str, got: {type(value)}")

        # Use object.__setattr__ to set the frozen dataclass fields
        object.__setattr__(self, "value", processed_value)
        object.__setattr__(self, "is_placeholder", processed_is_placeholder)
        object.__setattr__(self, "original_string", processed_original_string)

    @classmethod
    def from_exchange(cls, order_id: int | str) -> "OrderId":
        """
        Create OrderId from exchange response.

        Args:
            order_id: Order ID from exchange API
        """
        return cls(order_id, is_placeholder=False)

    @classmethod
    def create_placeholder(
        cls, side: str, price: float, amount: float, suffix: str = ""
    ) -> "OrderId":
        """
        Create placeholder OrderId when exchange ID is not available.

        Args:
            side: Order side ('buy' or 'sell')
            price: Order price
            amount: Order amount
            suffix: Optional suffix for uniqueness
        """
        abs_amount = abs(amount)
        base_id = f"{side.lower()}_{price:.6f}_{abs_amount:.6f}"

        if suffix:
            base_id += f"_{suffix}"

        return cls(base_id, is_placeholder=True)

    def is_real_order_id(self) -> bool:
        """Check if this is a real order ID from the exchange."""
        return not self.is_placeholder

    def is_placeholder_id(self) -> bool:
        """Check if this is a placeholder ID."""
        return self.is_placeholder

    def can_be_cancelled(self) -> bool:
        """Check if this order can be cancelled via API."""
        return self.is_real_order_id()

    def to_string(self) -> str:
        """Convert to string representation."""
        return str(self.value)

    def to_int(self) -> int:
        """
        Convert to integer representation.

        Raises:
            ValueError: If the order ID is not convertible to int
        """
        return self.value

    def matches_pattern(self, pattern: str) -> bool:
        """Check if the order ID matches a given pattern (for placeholder IDs)."""
        if not self.is_placeholder:
            return False

        import re

        try:
            return bool(re.search(pattern, str(self.value)))
        except re.error:
            return False

    def get_placeholder_info(self) -> dict[str, Any]:
        """
        Extract information from placeholder ID.

        Returns:
            Dict with parsed placeholder information, empty if not a placeholder
        """
        if not self.is_placeholder or not self.original_string:
            return {}

        try:
            # Expected format: side_price_amount[_suffix]
            parts = self.original_string.split("_")
            if len(parts) >= 3:
                return {
                    "side": parts[0],
                    "price": float(parts[1]),
                    "amount": float(parts[2]),
                    "suffix": "_".join(parts[3:]) if len(parts) > 3 else "",
                }
        except (ValueError, IndexError):
            pass

        return {}

    def __str__(self) -> str:
        """String representation."""
        if self.is_placeholder and self.original_string:
            return self.original_string
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, OrderId):
            return self.value == other.value
        elif isinstance(other, int):
            return self.value == other
        elif isinstance(other, str) and other.isdigit():
            return self.value == int(other)
        return False

    def __ne__(self, other: object) -> bool:
        """Not equal comparison."""
        return not self.__eq__(other)

    def __lt__(self, other: "OrderId") -> bool:
        """Less than comparison."""
        return self.value < other.value

    def __le__(self, other: "OrderId") -> bool:
        """Less than or equal comparison."""
        return self.value <= other.value

    def __gt__(self, other: "OrderId") -> bool:
        """Greater than comparison."""
        return self.value > other.value

    def __ge__(self, other: "OrderId") -> bool:
        """Greater than or equal comparison."""
        return self.value >= other.value

    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash(self.value)

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"OrderId({self.value})"
