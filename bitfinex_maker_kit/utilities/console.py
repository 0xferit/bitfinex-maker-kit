"""
Console output and user interaction utilities.

This module provides functions for formatted console output, user prompts,
and interactive confirmations used throughout the CLI application.
"""

from .constants import EMOJI_ERROR, EMOJI_INFO, EMOJI_SUCCESS, EMOJI_WARNING


def print_success(message: str) -> None:
    """Print success message with emoji."""
    print(f"{EMOJI_SUCCESS} {message}")


def print_error(message: str) -> None:
    """Print error message with emoji."""
    print(f"{EMOJI_ERROR} {message}")


def print_warning(message: str) -> None:
    """Print warning message with emoji."""
    print(f"{EMOJI_WARNING} {message}")


def print_info(message: str) -> None:
    """Print info message with emoji."""
    print(f"{EMOJI_INFO} {message}")


def print_section_header(title: str, width: int = 60) -> None:
    """Print formatted section header."""
    print(f"\n{title}")
    print("=" * width)


def print_table_separator(width: int = 80) -> None:
    """Print table separator line."""
    print("─" * width)


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.

    Args:
        prompt: The question to ask
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    suffix = " (y/N)" if not default else " (Y/n)"
    response = input(f"{prompt}{suffix}: ").strip().lower()

    if not response:
        return default

    return response in ["y", "yes"]


# Standardized error message functions to eliminate duplication
def print_operation_error(operation: str, error: Exception) -> None:
    """
    Print standardized error message for failed operations.

    Args:
        operation: Description of the operation that failed (e.g., "get wallet data")
        error: The exception that occurred
    """
    print_error(f"Failed to {operation}: {error}")


def print_api_error(api_call: str, error: Exception) -> None:
    """
    Print standardized error message for API call failures.

    Args:
        api_call: Name of the API call that failed (e.g., "get orders")
        error: The exception that occurred
    """
    print_error(f"API call failed - {api_call}: {error}")


def print_order_error(order_id: int | str, operation: str, error: Exception) -> None:
    """
    Print standardized error message for order-related operations.

    Args:
        order_id: ID of the order that failed
        operation: Operation that failed (e.g., "cancel", "update")
        error: The exception that occurred
    """
    print_error(f"Failed to {operation} order {order_id}: {error}")


def print_validation_error(field: str, value: str, reason: str) -> None:
    """
    Print standardized validation error message.

    Args:
        field: Name of the field that failed validation
        value: The invalid value
        reason: Reason for validation failure
    """
    print_error(f"Invalid {field} '{value}': {reason}")


def print_not_found_error(item_type: str, identifier: str) -> None:
    """
    Print standardized 'not found' error message.

    Args:
        item_type: Type of item not found (e.g., "order", "symbol")
        identifier: Identifier that wasn't found
    """
    print_error(
        f"{item_type.title()} {identifier} not found (may have already been filled or cancelled)"
    )


def print_bulk_operation_result(operation: str, success_count: int, total_count: int) -> None:
    """
    Print result of bulk operations.

    Args:
        operation: Operation performed (e.g., "cancel", "update")
        success_count: Number of successful operations
        total_count: Total number of operations attempted
    """
    if success_count == total_count:
        print_success(f"Successfully {operation}ed {success_count} items")
    elif success_count > 0:
        print_warning(f"Partially successful: {operation}ed {success_count}/{total_count} items")
    else:
        print_error(f"Failed to {operation} any of {total_count} items")
