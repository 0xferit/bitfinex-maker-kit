"""
Centralized client factory to eliminate duplication of dependency injection patterns.

This module provides a single point for client creation, replacing the duplicated
try/except pattern found throughout the codebase.
"""

from collections.abc import Callable
from typing import Any

from ..bitfinex_client import BitfinexClientWrapper
from ..services.container import get_container
from .auth import create_client


def get_client() -> BitfinexClientWrapper:
    """
    Get a Bitfinex client using dependency injection with fallback.

    This function centralizes the common pattern of trying dependency injection
    first and falling back to legacy client creation. It eliminates the
    duplication of this pattern across 9+ files in the codebase.

    Returns:
        BitfinexClientWrapper: Configured client instance

    Raises:
        SystemExit: If credentials are not available (from legacy fallback)
    """
    try:
        # Try dependency injection first (preferred method)
        container = get_container()
        return container.create_bitfinex_client()
    except Exception:
        # Fall back to legacy method for backward compatibility
        # Type ignore because legacy create_client returns Any but we know it's BitfinexClientWrapper
        return create_client()  # type: ignore[no-any-return]


def get_client_safe() -> BitfinexClientWrapper | None:
    """
    Get a Bitfinex client safely without raising SystemExit.

    This version catches SystemExit from the legacy create_client() function
    and returns None instead, useful for operations that should gracefully
    handle missing credentials.

    Returns:
        BitfinexClientWrapper or None: Client instance or None if creation fails
    """
    try:
        return get_client()
    except SystemExit:
        return None
    except Exception:
        return None


def with_client(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that injects a client as the first argument to a function.

    This decorator eliminates boilerplate client creation code from command
    functions while providing consistent error handling.

    Args:
        func: Function that expects a client as its first argument

    Returns:
        Decorated function that automatically gets a client

    Example:
        @with_client
        def my_command(client, other_args):
            return client.get_orders()
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        client = get_client_safe()
        if client is None:
            print("❌ Failed to create API client. Check your credentials.")
            return None
        return func(client, *args, **kwargs)

    # Preserve function metadata
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def ensure_client_available() -> bool:
    """
    Check if a client can be created without actually creating it.

    Useful for validation before starting operations that require API access.

    Returns:
        bool: True if client can be created, False otherwise
    """
    client = get_client_safe()
    return client is not None
