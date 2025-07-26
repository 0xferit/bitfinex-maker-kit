"""
Dedicated service for handling order updates.

This service encapsulates all order update logic, including validation,
strategy selection, and execution, separated from the API client.
"""

from typing import Any

from ..update_strategies.strategy_factory import UpdateStrategyFactory
from ..utilities.constants import OrderSubmissionError
from .api_client import BitfinexAPIClient
from .order_fetcher import OrderFetcher
from .order_validator import OrderUpdateValidator


class OrderUpdateResult:
    """Result of an order update operation."""

    def __init__(
        self,
        success: bool,
        method: str,
        order_id: int,
        message: str,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.method = method
        self.order_id = order_id
        self.message = message
        self.response_data = response_data


class OrderUpdateService:
    """
    Service responsible for handling all order update operations.

    This service coordinates validation, order fetching, strategy selection,
    and update execution while maintaining separation of concerns.
    """

    def __init__(self, api_client: BitfinexAPIClient) -> None:
        """Initialize order update service with API client."""
        self.api_client = api_client
        self.validator = OrderUpdateValidator()
        self.order_fetcher = OrderFetcher(api_client)
        self.strategy_factory = UpdateStrategyFactory()

    def update_order(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
        use_cancel_recreate: bool = False,
    ) -> OrderUpdateResult:
        """
        Update an existing order using configurable strategies.

        Args:
            order_id: ID of the order to update
            price: New price for the order
            amount: New absolute amount for the order (always provide as positive)
            delta: Amount to add/subtract from current amount (alternative to amount)
            use_cancel_recreate: If True, use cancel-and-recreate instead of WebSocket

        Returns:
            OrderUpdateResult with operation details

        Raises:
            OrderSubmissionError: If order update fails
            ValueError: If parameters are invalid
        """
        try:
            # Step 1: Validate and create update request
            request = self.validator.validate_update_request(order_id, price, amount, delta)

            # Step 2: Fetch and validate the existing order
            current_order = self.order_fetcher.fetch_order_by_id(order_id)
            self.validator.validate_order_state(current_order)

            # Step 3: Select and execute update strategy
            strategy = self.strategy_factory.create_strategy(use_cancel_recreate)

            if use_cancel_recreate:
                print(f"   Using {strategy.get_strategy_name()} (has risk of order loss)")

            result = strategy.execute_update(request, current_order, self)

            # Step 4: Return structured result
            return OrderUpdateResult(
                success=result.success,
                method=result.method,
                order_id=result.order_id,
                message=result.message,
                response_data=result.response_data,
            )

        except ValueError as e:
            # Parameter validation errors
            raise ValueError(str(e)) from e
        except OrderSubmissionError:
            # API errors - re-raise as-is
            raise
        except Exception as e:
            # Unexpected errors
            raise OrderSubmissionError(f"Order update failed: {e}") from e

    def get_client(self) -> BitfinexAPIClient:
        """Get the underlying API client for strategy use."""
        return self.api_client
