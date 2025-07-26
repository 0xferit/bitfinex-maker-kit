"""
Input validation utilities.

This module provides validation functions for user inputs, trading parameters,
and data conversion with error handling used throughout the application.
"""


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
