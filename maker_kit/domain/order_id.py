"""
OrderId value object for order identification.

Provides type-safe order ID representation with validation and utilities.
"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class OrderId:
    """
    Immutable order ID value object with validation.
    
    Handles both real order IDs from the exchange and placeholder IDs
    generated locally when order ID extraction fails.
    """
    
    value: Union[int, str]
    is_placeholder: bool = False
    
    def __post_init__(self):
        """Validate order ID after initialization."""
        if self.value is None:
            raise ValueError("Order ID cannot be None")
        
        if isinstance(self.value, str):
            if not self.value.strip():
                raise ValueError("String order ID cannot be empty")
        elif isinstance(self.value, int):
            if self.value <= 0:
                raise ValueError(f"Integer order ID must be positive, got: {self.value}")
        else:
            raise ValueError(f"Order ID must be int or str, got: {type(self.value)}")
    
    @classmethod
    def from_exchange(cls, order_id: Union[int, str]) -> 'OrderId':
        """
        Create OrderId from exchange response.
        
        Args:
            order_id: Order ID from exchange API
        """
        return cls(order_id, is_placeholder=False)
    
    @classmethod
    def create_placeholder(cls, side: str, price: float, amount: float, suffix: str = "") -> 'OrderId':
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
        if isinstance(self.value, int):
            return self.value
        elif isinstance(self.value, str) and self.value.isdigit():
            return int(self.value)
        else:
            raise ValueError(f"Cannot convert order ID '{self.value}' to integer")
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if the order ID matches a given pattern (for placeholder IDs)."""
        if not self.is_placeholder:
            return False
        
        import re
        try:
            return bool(re.search(pattern, str(self.value)))
        except re.error:
            return False
    
    def get_placeholder_info(self) -> dict:
        """
        Extract information from placeholder ID.
        
        Returns:
            Dict with parsed placeholder information, empty if not a placeholder
        """
        if not self.is_placeholder or not isinstance(self.value, str):
            return {}
        
        try:
            # Expected format: side_price_amount[_suffix]
            parts = str(self.value).split('_')
            if len(parts) >= 3:
                return {
                    'side': parts[0],
                    'price': float(parts[1]),
                    'amount': float(parts[2]),
                    'suffix': '_'.join(parts[3:]) if len(parts) > 3 else ''
                }
        except (ValueError, IndexError):
            pass
        
        return {}
    
    def __str__(self) -> str:
        """String representation."""
        prefix = "[P]" if self.is_placeholder else ""
        return f"{prefix}{self.value}"
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if isinstance(other, OrderId):
            return self.value == other.value and self.is_placeholder == other.is_placeholder
        elif isinstance(other, (int, str)):
            return self.value == other
        return False
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash((self.value, self.is_placeholder))