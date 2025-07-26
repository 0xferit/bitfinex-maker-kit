"""
Test package for Maker-Kit.

Provides comprehensive testing infrastructure with modern testing patterns,
fixtures, and utilities for trading system validation.
"""

__all__ = [
    'test_wrapper_architecture',  # API wrapper POST_ONLY enforcement
    'test_post_only_enforcement',  # Legacy: Centralized function tests
    'conftest',                   # Pytest configuration and fixtures
    'fixtures',                   # Test data fixtures
    'mocks',                      # Mock objects and utilities  
    'integration',                # Integration test suite
    'unit',                       # Unit test suite
    'performance',                # Performance test suite
    'load',                       # Load testing suite
] 