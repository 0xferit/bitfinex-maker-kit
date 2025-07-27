"""
WebSocket event handling for real-time trading operations.

This package handles WebSocket connections and event processing for
automated market making, separated from business logic and UI concerns.
"""

from .event_handler import WebSocketEventHandler

__all__ = ["WebSocketEventHandler"]
