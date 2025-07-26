"""
Test command - Test API and WebSocket connections.
"""

from typing import Any

from ..utilities.auth import test_comprehensive


def test_command() -> Any:
    """Test both REST API and WebSocket connections comprehensively"""
    return test_comprehensive()
