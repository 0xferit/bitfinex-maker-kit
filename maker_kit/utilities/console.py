"""
Console output and user interaction utilities.

This module provides functions for formatted console output, user prompts,
and interactive confirmations used throughout the CLI application.
"""

from .constants import EMOJI_SUCCESS, EMOJI_ERROR, EMOJI_WARNING, EMOJI_INFO


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
    
    return response in ['y', 'yes'] 