"""
Async WebSocket connection manager for Maker-Kit.

Provides proper async context management for WebSocket connections
with automatic reconnection, heartbeat, and graceful shutdown.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..bitfinex_client import BitfinexClientWrapper

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionConfig:
    """Configuration for WebSocket connection."""

    reconnect_attempts: int = 5
    reconnect_delay_base: float = 1.0  # Base delay for exponential backoff
    reconnect_delay_max: float = 30.0
    heartbeat_interval: float = 30.0
    connection_timeout: float = 10.0
    ping_timeout: float = 5.0
    enable_heartbeat: bool = True
    enable_auto_reconnect: bool = True


class AsyncWebSocketConnectionManager:
    """
    Async WebSocket connection manager with proper lifecycle management.

    Provides context manager interface for WebSocket connections with
    automatic reconnection, heartbeat monitoring, and graceful shutdown.
    """

    def __init__(self, client: BitfinexClientWrapper, config: ConnectionConfig):
        """
        Initialize connection manager.

        Args:
            client: Bitfinex client wrapper
            config: Connection configuration
        """
        self.client = client
        self.config = config
        self.state = ConnectionState.DISCONNECTED

        # Connection management
        self._connection_lock = asyncio.Lock()
        self._reconnect_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.connection_attempts = 0
        self.successful_connections = 0
        self.reconnection_count = 0
        self.last_connection_time: float | None = None
        self.last_error: str | None = None

        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {
            "connection_established": [],
            "connection_lost": [],
            "connection_error": [],
            "message_received": [],
            "heartbeat_timeout": [],
        }

    async def __aenter__(self) -> "AsyncWebSocketConnectionManager":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> bool:
        """
        Connect to WebSocket with retry logic.

        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
                logger.warning(f"Already connected or connecting (state: {self.state.value})")
                return self.state == ConnectionState.CONNECTED

            self.state = ConnectionState.CONNECTING
            self.connection_attempts += 1

            try:
                logger.info(f"Connecting to WebSocket (attempt {self.connection_attempts})")

                # Set connection timeout
                await asyncio.wait_for(self._do_connect(), timeout=self.config.connection_timeout)

                self.state = ConnectionState.CONNECTED
                self.successful_connections += 1
                self.last_connection_time = asyncio.get_event_loop().time()
                self.last_error = None

                logger.info("WebSocket connection established")

                # Start heartbeat if enabled
                if self.config.enable_heartbeat:
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # Notify event handlers
                await self._emit_event(
                    "connection_established",
                    {"attempt": self.connection_attempts, "timestamp": self.last_connection_time},
                )

                return True

            except TimeoutError:
                error_msg = f"Connection timeout after {self.config.connection_timeout}s"
                logger.error(error_msg)
                self.last_error = error_msg
                self.state = ConnectionState.ERROR

                await self._emit_event(
                    "connection_error", {"error": error_msg, "attempt": self.connection_attempts}
                )

                return False

            except Exception as e:
                error_msg = f"Connection error: {e!s}"
                logger.error(error_msg)
                self.last_error = error_msg
                self.state = ConnectionState.ERROR

                await self._emit_event(
                    "connection_error", {"error": error_msg, "attempt": self.connection_attempts}
                )

                return False

    async def _do_connect(self) -> None:
        """Perform the actual connection."""
        await self.client.wss.start()

    async def disconnect(self) -> bool:
        """
        Disconnect from WebSocket gracefully.

        Returns:
            True if disconnection successful, False otherwise
        """
        async with self._connection_lock:
            if self.state == ConnectionState.DISCONNECTED:
                logger.warning("Already disconnected")
                return True

            self.state = ConnectionState.CLOSING

            try:
                logger.info("Disconnecting from WebSocket")

                # Signal shutdown
                self._shutdown_event.set()

                # Stop heartbeat
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._heartbeat_task

                # Stop reconnection task
                if self._reconnect_task and not self._reconnect_task.done():
                    self._reconnect_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self._reconnect_task

                # Close WebSocket connection
                await self.client.wss.close()

                self.state = ConnectionState.DISCONNECTED
                logger.info("WebSocket disconnected")

                return True

            except Exception as e:
                error_msg = f"Disconnection error: {e!s}"
                logger.error(error_msg)
                self.last_error = error_msg
                self.state = ConnectionState.ERROR
                return False

    async def reconnect(self) -> bool:
        """
        Reconnect with exponential backoff.

        Returns:
            True if reconnection successful, False otherwise
        """
        if not self.config.enable_auto_reconnect:
            logger.info("Auto-reconnect disabled")
            return False

        if self.state == ConnectionState.RECONNECTING:
            logger.warning("Already reconnecting")
            return False

        self.state = ConnectionState.RECONNECTING
        self.reconnection_count += 1

        logger.info(f"Starting reconnection attempt {self.reconnection_count}")

        for attempt in range(self.config.reconnect_attempts):
            if self._shutdown_event.is_set():
                logger.info("Shutdown requested - stopping reconnection")
                return False

            # Calculate delay with exponential backoff
            delay = min(
                self.config.reconnect_delay_base * (2**attempt), self.config.reconnect_delay_max
            )

            logger.info(
                f"Reconnection attempt {attempt + 1}/{self.config.reconnect_attempts} in {delay:.1f}s"
            )

            try:
                await asyncio.sleep(delay)

                if await self.connect():
                    logger.info(f"Reconnection successful after {attempt + 1} attempts")
                    return True

            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")

        logger.error(f"Reconnection failed after {self.config.reconnect_attempts} attempts")
        self.state = ConnectionState.ERROR

        return False

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop to monitor connection health."""
        logger.debug("Starting heartbeat loop")

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.heartbeat_interval)

                if self._shutdown_event.is_set():
                    break

                # Send ping and wait for pong
                if not await self._send_heartbeat():
                    logger.warning("Heartbeat failed - connection may be lost")

                    await self._emit_event(
                        "heartbeat_timeout", {"timestamp": asyncio.get_event_loop().time()}
                    )

                    # Trigger reconnection if auto-reconnect is enabled
                    if self.config.enable_auto_reconnect:
                        self._reconnect_task = asyncio.create_task(self.reconnect())

                    break

            except asyncio.CancelledError:
                logger.debug("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                break

        logger.debug("Heartbeat loop stopped")

    async def _send_heartbeat(self) -> bool:
        """
        Send heartbeat ping and wait for pong.

        Returns:
            True if heartbeat successful, False otherwise
        """
        try:
            # Implementation would depend on Bitfinex WebSocket API
            # For now, just check if connection is still alive
            if hasattr(self.client.wss, "ping"):
                pong_waiter = await self.client.wss.ping()
                await asyncio.wait_for(pong_waiter, timeout=self.config.ping_timeout)
                return True
            else:
                # Fallback: assume connection is healthy if no ping method
                return self.state == ConnectionState.CONNECTED

        except TimeoutError:
            logger.warning("Heartbeat ping timeout")
            return False
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False

    def register_event_handler(self, event_type: str, handler: Callable[..., Any]) -> None:
        """
        Register an event handler.

        Args:
            event_type: Type of event
            handler: Handler function
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
            logger.debug(f"Registered handler for {event_type}")
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def unregister_event_handler(self, event_type: str, handler: Callable[..., Any]) -> None:
        """
        Unregister an event handler.

        Args:
            event_type: Type of event
            handler: Handler function
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                logger.debug(f"Unregistered handler for {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for {event_type}")

    async def _emit_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        handlers = self._event_handlers.get(event_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    def get_connection_stats(self) -> dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dictionary with connection statistics
        """
        return {
            "state": self.state.value,
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "reconnection_count": self.reconnection_count,
            "last_connection_time": self.last_connection_time,
            "last_error": self.last_error,
            "uptime": (asyncio.get_event_loop().time() - self.last_connection_time)
            if self.last_connection_time
            else 0,
        }

    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.state == ConnectionState.CONNECTED

    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.state == ConnectionState.CONNECTED and self.last_error is None

    async def wait_for_connection(self, timeout: float | None = None) -> bool:
        """
        Wait for connection to be established.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if connected within timeout, False otherwise
        """
        start_time = asyncio.get_event_loop().time()

        while self.state != ConnectionState.CONNECTED:
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                return False

            if self.state in [ConnectionState.ERROR, ConnectionState.CLOSED]:
                return False

            await asyncio.sleep(0.1)

        return True


def create_connection_manager(
    client: BitfinexClientWrapper, config: ConnectionConfig | None = None
) -> AsyncWebSocketConnectionManager:
    """
    Create a WebSocket connection manager.

    Args:
        client: Bitfinex client wrapper
        config: Connection configuration (uses defaults if None)

    Returns:
        Configured AsyncWebSocketConnectionManager
    """
    if config is None:
        config = ConnectionConfig()

    return AsyncWebSocketConnectionManager(client, config)
