"""
Input validation utilities.

This module provides validation functions for user inputs, trading parameters,
and data conversion with error handling used throughout the application.
"""

import re
from typing import Any


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


def validate_positive_number(value: int | float, name: str) -> None:
    """Validate that a number is positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_empty_string(value: str, name: str) -> None:
    """Validate that a string is not empty."""
    if not value or not value.strip():
        raise ValueError(f"{name} cannot be empty")


def safe_float_convert(value: str | int | float, default: float = 0.0) -> float:
    """Safely convert value to float with fallback."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def validate_symbol(symbol: str | None) -> None:
    """
    Validate trading symbol format.
    Valid symbols must:
    - Be non-empty strings
    - Start with 't' or 'f' (trading or funding)
    - Be at least 6 characters long
    - Contain only uppercase letters after the prefix
    Args:
        symbol: The trading symbol to validate
    Raises:
        ValidationError: If symbol format is invalid
    """
    if symbol is None or not isinstance(symbol, str):
        raise ValidationError("Symbol cannot be None or non-string")

    if not symbol:
        raise ValidationError("Symbol cannot be empty")

    # Check if it starts with 't' or 'f' and has proper format
    if not re.match(r"^[tf][A-Z]{5,}$", symbol):
        raise ValidationError(
            f"Invalid symbol format: {symbol}. Must start with 't' or 'f' followed by uppercase letters"
        )


def validate_price(price: str | int | float | None) -> None:
    """
    Validate price value.
    Valid prices must:
    - Be convertible to float
    - Be greater than 0
    - Not be None
    Args:
        price: The price to validate
    Raises:
        ValidationError: If price is invalid
    """
    if price is None:
        raise ValidationError("Price cannot be None")

    try:
        price_float = float(price)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Price must be a valid number, got: {price}") from e

    if price_float <= 0:
        raise ValidationError(f"Price must be greater than 0, got: {price_float}")


def validate_amount(amount: str | int | float | None) -> None:
    """
    Validate amount value.
    Valid amounts must:
    - Be convertible to float
    - Not be zero
    - Not be None
    Args:
        amount: The amount to validate
    Raises:
        ValidationError: If amount is invalid
    """
    if amount is None:
        raise ValidationError("Amount cannot be None")

    try:
        amount_float = float(amount)
    except (ValueError, TypeError) as e:
        raise ValidationError(f"Amount must be a valid number, got: {amount}") from e

    if amount_float == 0:
        raise ValidationError("Amount cannot be zero")


def validate_order_params(params: dict[str, Any]) -> None:
    """
    Validate order parameters dictionary.
    Required fields:
    - symbol: Valid trading symbol
    - amount: Valid amount (non-zero)
    - price: Valid price (positive)
    - side: Valid side (buy or sell)
    Args:
        params: Dictionary containing order parameters
    Raises:
        ValidationError: If any required parameter is missing or invalid
    """
    required_fields = ["symbol", "amount", "price", "side"]

    # Check for required fields
    for field in required_fields:
        if field not in params:
            raise ValidationError(f"Missing required field: {field}")

    # Validate individual fields
    validate_symbol(params["symbol"])
    validate_amount(params["amount"])
    validate_price(params["price"])
