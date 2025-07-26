"""
Centralized response parsing utilities for Bitfinex API responses.

This module eliminates code duplication by providing a single place to handle
the various response formats from the Bitfinex API, particularly for order
submission and management operations.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OrderResponseParser:
    """
    Centralized parser for Bitfinex API responses related to orders.

    Handles the various response formats from order submission, updates,
    and cancellation operations, providing consistent order ID extraction
    and response parsing across the application.
    """

    @staticmethod
    def extract_order_id(response: Any) -> int | str | None:
        """
        Extract order ID from Bitfinex API response.

        Handles multiple response formats:
        - Notification with data attribute
        - Direct order response
        - List responses
        - Alternative notification formats

        Args:
            response: API response object from Bitfinex

        Returns:
            Order ID if found, None otherwise
        """
        if response is None:
            return None

        try:
            # Try different response formats from Bitfinex API

            # Format 1: Response with data attribute (most common)
            if hasattr(response, "data") and response.data:
                order_data = response.data
                if isinstance(order_data, list) and len(order_data) > 0:
                    # Data is a list, get the first order
                    first_item = order_data[0]
                    if hasattr(first_item, "id"):
                        return first_item.id
                    elif isinstance(first_item, int | str):
                        return first_item
                elif hasattr(order_data, "id"):
                    # Data is a single order object
                    return order_data.id

            # Format 2: Alternative notification format
            if hasattr(response, "notify_info") and response.notify_info:
                if isinstance(response.notify_info, list) and len(response.notify_info) > 0:
                    first_item = response.notify_info[0]
                    if isinstance(first_item, int | str):
                        return first_item

            # Format 3: Direct order response
            if hasattr(response, "id"):
                return response.id

            # Format 4: Response is a list directly
            if isinstance(response, list) and len(response) > 0:
                first_item = response[0]
                if hasattr(first_item, "id"):
                    return first_item.id
                elif isinstance(first_item, int | str):
                    return first_item

        except Exception as e:
            logger.warning(f"Error extracting order ID from response: {e}")
            logger.debug(f"Response type: {type(response)}")
            if hasattr(response, "__dict__"):
                logger.debug(f"Response attributes: {list(response.__dict__.keys())}")

        return None

    @staticmethod
    def extract_order_details(response: Any) -> dict[str, Any]:
        """
        Extract comprehensive order details from API response.

        Args:
            response: API response object from Bitfinex

        Returns:
            Dictionary with order details, empty dict if extraction fails
        """
        details = {}

        try:
            order_id = OrderResponseParser.extract_order_id(response)
            if order_id:
                details["id"] = order_id

            # Try to extract additional details based on response format
            if hasattr(response, "data") and response.data:
                order_data = response.data
                if isinstance(order_data, list) and len(order_data) > 0:
                    order_obj = order_data[0]
                    if hasattr(order_obj, "__dict__"):
                        details.update(order_obj.__dict__)
                elif hasattr(order_data, "__dict__"):
                    details.update(order_data.__dict__)
            elif hasattr(response, "__dict__"):
                details.update(response.__dict__)

        except Exception as e:
            logger.warning(f"Error extracting order details: {e}")

        return details

    @staticmethod
    def generate_placeholder_id(side: str, price: float, amount: float, suffix: str = "") -> str:
        """
        Generate a placeholder order ID when real ID extraction fails.

        Creates a deterministic ID based on order parameters for tracking
        purposes when the API response doesn't contain a proper order ID.

        Args:
            side: Order side ('buy' or 'sell')
            price: Order price
            amount: Order amount (will be converted to absolute value)
            suffix: Optional suffix to add to the ID

        Returns:
            Placeholder ID string
        """
        abs_amount = abs(amount)
        base_id = f"{side.lower()}_{price:.6f}_{abs_amount:.6f}"

        if suffix:
            base_id += f"_{suffix}"

        return base_id

    @staticmethod
    def log_response_debug_info(response: Any, context: str = "") -> None:
        """
        Log debug information about API response structure.

        Useful for debugging when order ID extraction fails or when
        encountering new response formats from the Bitfinex API.

        Args:
            response: API response object
            context: Optional context string for logging
        """
        try:
            context_prefix = f"[{context}] " if context else ""
            logger.debug(f"{context_prefix}Response debug info:")
            logger.debug(f"{context_prefix}  Type: {type(response)}")

            if hasattr(response, "__dict__"):
                logger.debug(f"{context_prefix}  Attributes: {list(response.__dict__.keys())}")

            if hasattr(response, "data"):
                logger.debug(f"{context_prefix}  Data type: {type(response.data)}")
                if hasattr(response.data, "__dict__"):
                    logger.debug(
                        f"{context_prefix}  Data attributes: {list(response.data.__dict__.keys())}"
                    )

            if isinstance(response, list):
                logger.debug(f"{context_prefix}  List length: {len(response)}")
                if response and hasattr(response[0], "__dict__"):
                    logger.debug(
                        f"{context_prefix}  First item attributes: {list(response[0].__dict__.keys())}"
                    )

        except Exception as e:
            logger.warning(f"{context_prefix}Failed to log debug info: {e}")


class OrderTracker:
    """
    Utility class for tracking orders with fallback to placeholder IDs.

    Handles the common pattern of extracting order IDs from responses
    and falling back to placeholder IDs when extraction fails.
    """

    def __init__(self):
        self.tracked_orders: dict[int | str, dict[str, Any]] = {}

    def track_order_from_response(
        self, response: Any, side: str, amount: float, price: float, symbol: str = ""
    ) -> int | str:
        """
        Track an order from API response, using placeholder ID if needed.

        Args:
            response: API response from order submission
            side: Order side ('buy' or 'sell')
            amount: Order amount
            price: Order price
            symbol: Trading symbol (optional, for context)

        Returns:
            Order ID (real or placeholder)
        """
        # Try to extract real order ID
        order_id = OrderResponseParser.extract_order_id(response)

        if order_id:
            # Use real order ID
            self.tracked_orders[order_id] = {
                "id": order_id,
                "side": side,
                "amount": abs(amount),
                "price": price,
                "symbol": symbol,
                "is_placeholder": False,
            }
            logger.info(f"Tracking order with real ID: {order_id}")
        else:
            # Generate placeholder ID
            placeholder_id = OrderResponseParser.generate_placeholder_id(side, price, abs(amount))
            self.tracked_orders[placeholder_id] = {
                "id": placeholder_id,
                "side": side,
                "amount": abs(amount),
                "price": price,
                "symbol": symbol,
                "is_placeholder": True,
            }
            logger.warning(
                f"Order placed but couldn't extract ID, using placeholder: {placeholder_id}"
            )
            OrderResponseParser.log_response_debug_info(response, "placeholder_fallback")

        return order_id or placeholder_id

    def get_tracked_order(self, order_id: int | str) -> dict[str, Any] | None:
        """Get details for a tracked order."""
        return self.tracked_orders.get(order_id)

    def remove_tracked_order(self, order_id: int | str) -> bool:
        """Remove an order from tracking. Returns True if order was tracked."""
        return self.tracked_orders.pop(order_id, None) is not None

    def get_all_tracked_orders(self) -> dict[int | str, dict[str, Any]]:
        """Get all currently tracked orders."""
        return self.tracked_orders.copy()

    def clear_all_tracked_orders(self) -> None:
        """Clear all tracked orders."""
        self.tracked_orders.clear()
        logger.info("Cleared all tracked orders")
