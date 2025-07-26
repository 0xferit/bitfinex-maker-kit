"""
Base classes for order update strategies.

Defines the interface and data structures for different order update approaches.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class OrderUpdateRequest:
    """
    Represents a request to update an order.

    Encapsulates all the parameters needed to update an order,
    with validation and conversion utilities.
    """

    order_id: int
    price: Decimal | None = None
    amount: Decimal | None = None  # Always positive
    delta: Decimal | None = None  # Can be positive or negative

    def __post_init__(self) -> None:
        """Validate the update request."""
        if self.order_id <= 0:
            raise ValueError("Order ID must be positive")

        if self.amount is not None and self.delta is not None:
            raise ValueError("Cannot specify both amount and delta")

        if self.price is None and self.amount is None and self.delta is None:
            raise ValueError("Must specify at least one parameter to update")

        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")

        if self.amount is not None and self.amount <= 0:
            raise ValueError("Amount must be positive")

    def has_price_update(self) -> bool:
        """Check if this request includes a price update."""
        return self.price is not None

    def has_amount_update(self) -> bool:
        """Check if this request includes an amount update."""
        return self.amount is not None or self.delta is not None

    def calculate_new_amount(self, current_amount: Decimal) -> Decimal:
        """
        Calculate the new amount based on current amount and request parameters.

        Args:
            current_amount: Current order amount (signed, as from API)

        Returns:
            New amount (positive)
        """
        current_abs_amount = abs(current_amount)

        if self.amount is not None:
            return self.amount
        elif self.delta is not None:
            new_amount = current_abs_amount + self.delta
            if new_amount <= 0:
                raise ValueError(f"Delta {self.delta} would result in non-positive amount")
            return new_amount
        else:
            return current_abs_amount


@dataclass
class OrderUpdateResult:
    """
    Result of an order update operation.

    Contains information about the update method used and any relevant
    response data or error information.
    """

    success: bool
    method: str  # 'websocket_atomic', 'cancel_recreate', etc.
    order_id: int
    message: str
    response_data: dict[str, Any] | None = None
    new_order_id: int | None = None  # For cancel-recreate

    def is_cancel_recreate(self) -> bool:
        """Check if this was a cancel-and-recreate operation."""
        return self.method == "cancel_recreate"

    def is_atomic_update(self) -> bool:
        """Check if this was an atomic update operation."""
        return self.method in ["websocket_atomic", "rest_atomic"]


class OrderUpdateStrategy(ABC):
    """
    Abstract base class for order update strategies.

    Implements the Strategy pattern for different approaches to updating orders:
    - WebSocket atomic updates
    - Cancel-and-recreate updates
    - Future: REST API atomic updates
    """

    @abstractmethod
    def can_handle_request(self, request: OrderUpdateRequest) -> bool:
        """
        Check if this strategy can handle the given update request.

        Args:
            request: The order update request

        Returns:
            True if this strategy can handle the request
        """
        pass

    @abstractmethod
    def execute_update(
        self, request: OrderUpdateRequest, current_order: Any, client: Any
    ) -> OrderUpdateResult:
        """
        Execute the order update using this strategy.

        Args:
            request: The order update request
            current_order: Current order object from API
            client: Bitfinex client instance

        Returns:
            Result of the update operation
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy for logging/reporting."""
        pass

    def get_risk_level(self) -> str:
        """
        Get the risk level of this strategy.

        Returns:
            'low', 'medium', or 'high'
        """
        return "medium"  # Default implementation
