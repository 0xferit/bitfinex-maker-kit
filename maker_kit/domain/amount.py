"""
Amount value object for trading operations.

Provides type-safe amount representation with Bitfinex API conversion utilities.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union
from ..utilities.constants import AMOUNT_PRECISION, OrderSide


@dataclass(frozen=True)
class Amount:
    """
    Immutable amount value object with validation and Bitfinex conversion.
    
    Handles the Bitfinex API convention where buy orders use positive amounts
    and sell orders use negative amounts, while providing a clean interface
    that always works with positive values.
    """
    
    value: Decimal
    
    def __post_init__(self):
        """Validate amount after initialization."""
        if self.value <= 0:
            raise ValueError(f"Amount must be positive, got: {self.value}")
    
    @classmethod
    def from_float(cls, amount: float) -> 'Amount':
        """Create Amount from float value."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got: {amount}")
        return cls(Decimal(str(amount)))
    
    @classmethod
    def from_string(cls, amount: str) -> 'Amount':
        """Create Amount from string value."""
        try:
            decimal_amount = Decimal(amount)
            if decimal_amount <= 0:
                raise ValueError(f"Amount must be positive, got: {amount}")
            return cls(decimal_amount)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount format: {amount}") from e
    
    @classmethod
    def from_bitfinex_amount(cls, bitfinex_amount: Union[float, str], side: OrderSide) -> 'Amount':
        """
        Create Amount from Bitfinex API response amount.
        
        Bitfinex uses positive amounts for buy orders and negative for sell orders.
        This method converts to our always-positive Amount representation.
        """
        decimal_amount = Decimal(str(bitfinex_amount))
        positive_amount = abs(decimal_amount)
        
        if positive_amount <= 0:
            raise ValueError(f"Amount must be positive, got: {positive_amount}")
        
        return cls(positive_amount)
    
    def to_float(self) -> float:
        """Convert to float for calculations."""
        return float(self.value)
    
    def for_bitfinex_side(self, side: OrderSide) -> Decimal:
        """
        Convert amount for Bitfinex API based on order side.
        
        Bitfinex expects:
        - Positive amounts for buy orders  
        - Negative amounts for sell orders
        """
        if side == OrderSide.BUY:
            return self.value
        elif side == OrderSide.SELL:
            return -self.value
        else:
            raise ValueError(f"Invalid order side: {side}")
    
    def for_bitfinex_side_float(self, side: OrderSide) -> float:
        """Convert amount to float for Bitfinex API based on order side."""
        return float(self.for_bitfinex_side(side))
    
    def format_display(self) -> str:
        """Format amount for user display."""
        return f"{self.value:.{AMOUNT_PRECISION}f}"
    
    def format_api(self) -> str:
        """Format amount for API submission."""
        return f"{self.value:.{AMOUNT_PRECISION}f}"
    
    def round_to_precision(self) -> 'Amount':
        """Round amount to standard precision."""
        rounded = self.value.quantize(
            Decimal('0.' + '0' * AMOUNT_PRECISION),
            rounding=ROUND_HALF_UP
        )
        return Amount(rounded)
    
    def add(self, other: 'Amount') -> 'Amount':
        """Add another amount to this one."""
        return Amount(self.value + other.value)
    
    def subtract(self, other: 'Amount') -> 'Amount':
        """Subtract another amount from this one."""
        result = self.value - other.value
        if result <= 0:
            raise ValueError(f"Subtraction would result in non-positive amount: {result}")
        return Amount(result)
    
    def multiply(self, factor: Union[float, Decimal]) -> 'Amount':
        """Multiply amount by a factor."""
        if isinstance(factor, float):
            factor = Decimal(str(factor))
        
        result = self.value * factor
        if result <= 0:
            raise ValueError(f"Multiplication would result in non-positive amount: {result}")
        return Amount(result)
    
    def percentage_of(self, percentage: float) -> 'Amount':
        """Calculate a percentage of this amount."""
        if percentage <= 0:
            raise ValueError(f"Percentage must be positive, got: {percentage}")
        
        factor = Decimal(str(percentage / 100))
        return self.multiply(factor)
    
    def is_sufficient_for_order(self, minimum: 'Amount') -> bool:
        """Check if this amount meets minimum order requirements."""
        return self.value >= minimum.value
    
    def __str__(self) -> str:
        """String representation."""
        return self.format_display()
    
    def __lt__(self, other: 'Amount') -> bool:
        """Less than comparison."""
        return self.value < other.value
    
    def __le__(self, other: 'Amount') -> bool:
        """Less than or equal comparison."""
        return self.value <= other.value
    
    def __gt__(self, other: 'Amount') -> bool:
        """Greater than comparison."""
        return self.value > other.value
    
    def __ge__(self, other: 'Amount') -> bool:
        """Greater than or equal comparison."""
        return self.value >= other.value
    
    def __eq__(self, other: 'Amount') -> bool:
        """Equality comparison."""
        return self.value == other.value