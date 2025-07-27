"""
Test package for Maker-Kit.

Provides comprehensive testing infrastructure with modern testing patterns,
fixtures, and utilities for trading system validation.
"""

__all__ = [
    "conftest",  # Pytest configuration and fixtures
    "fixtures",  # Test data fixtures
    "integration",  # Integration test suite
    "load",  # Load testing suite
    "mocks",  # Mock objects and utilities
    "performance",  # Performance test suite
    "test_post_only_enforcement",  # Legacy: Centralized function tests
    "test_wrapper_architecture",  # API wrapper POST_ONLY enforcement
    "unit",  # Unit test suite
]
