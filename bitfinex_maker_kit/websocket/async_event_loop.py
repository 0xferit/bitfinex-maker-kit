"""
Async event loop management for Maker-Kit.

Provides clean event loop lifecycle management for async operations
with proper startup, shutdown, and error handling.
"""

import asyncio
import logging
import signal
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from .connection_manager import AsyncWebSocketConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class EventLoopConfig:
    """Configuration for async event loop."""

    graceful_shutdown_timeout: float = 30.0
    task_cleanup_timeout: float = 10.0
    enable_signal_handlers: bool = True
    debug_mode: bool = False


class AsyncEventLoopManager:
    """
    Manages async event loop lifecycle for Maker-Kit.

    Provides proper startup, shutdown, and task management
    for long-running async operations like WebSocket connections.
    """

    def __init__(self, config: EventLoopConfig):
        """
        Initialize event loop manager.

        Args:
            config: Event loop configuration
        """
        self.config = config
        self.loop: asyncio.AbstractEventLoop | None = None
        self.running = False
        self.shutdown_requested = False

        # Task management
        self.background_tasks: set[asyncio.Task] = set()
        self.cleanup_callbacks: list[Callable] = []

        # Signal handling
        self._original_handlers: dict[int, Any] = {}

        # Statistics
        self.start_time: float | None = None
        self.shutdown_time: float | None = None
        self.tasks_created = 0
        self.tasks_completed = 0
        self.tasks_cancelled = 0

    async def __aenter__(self) -> "AsyncEventLoopManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()

    async def start(self) -> None:
        """Start the event loop manager."""
        if self.running:
            logger.warning("Event loop manager already running")
            return

        self.loop = asyncio.get_running_loop()
        self.running = True
        self.shutdown_requested = False
        self.start_time = self.loop.time()

        # Configure loop
        if self.config.debug_mode:
            self.loop.set_debug(True)

        # Set up signal handlers
        if self.config.enable_signal_handlers:
            self._setup_signal_handlers()

        logger.info("Async event loop manager started")

    async def shutdown(self) -> None:
        """Shutdown the event loop manager gracefully."""
        if not self.running:
            logger.warning("Event loop manager not running")
            return

        if self.shutdown_requested:
            logger.warning("Shutdown already in progress")
            return

        self.shutdown_requested = True
        self.shutdown_time = self.loop.time() if self.loop else None

        logger.info("Starting graceful shutdown of event loop manager")

        try:
            # Cancel all background tasks
            await self._cancel_background_tasks()

            # Run cleanup callbacks
            await self._run_cleanup_callbacks()

            # Restore signal handlers
            self._restore_signal_handlers()

            self.running = False

            logger.info("Event loop manager shutdown complete")

        except Exception as e:
            logger.error(f"Error during event loop shutdown: {e}")
            raise

    def create_task(self, coro: Any, name: str | None = None) -> asyncio.Task[Any]:
        """
        Create and track a background task.

        Args:
            coro: Coroutine to run
            name: Optional task name

        Returns:
            Created task
        """
        if not self.running:
            raise RuntimeError("Event loop manager not running")

        task = asyncio.create_task(coro, name=name)
        self.background_tasks.add(task)
        self.tasks_created += 1

        # Add callback to remove task when done
        task.add_done_callback(self._task_done_callback)

        logger.debug(f"Created background task: {name or task.get_name()}")
        return task

    def _task_done_callback(self, task: asyncio.Task) -> None:
        """Callback when a background task completes."""
        self.background_tasks.discard(task)

        if task.cancelled():
            self.tasks_cancelled += 1
            logger.debug(f"Background task cancelled: {task.get_name()}")
        elif task.exception():
            logger.error(f"Background task failed: {task.get_name()} - {task.exception()}")
        else:
            self.tasks_completed += 1
            logger.debug(f"Background task completed: {task.get_name()}")

    async def _cancel_background_tasks(self) -> None:
        """Cancel all background tasks."""
        if not self.background_tasks:
            return

        logger.info(f"Cancelling {len(self.background_tasks)} background tasks")

        # Cancel all tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete or timeout
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=self.config.task_cleanup_timeout,
                )
            except TimeoutError:
                logger.warning(
                    f"Some background tasks did not complete within {self.config.task_cleanup_timeout}s"
                )

        self.background_tasks.clear()

    async def _run_cleanup_callbacks(self) -> None:
        """Run all registered cleanup callbacks."""
        if not self.cleanup_callbacks:
            return

        logger.info(f"Running {len(self.cleanup_callbacks)} cleanup callbacks")

        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in cleanup callback: {e}")

    def register_cleanup_callback(self, callback: Callable) -> None:
        """
        Register a cleanup callback to run during shutdown.

        Args:
            callback: Cleanup function (sync or async)
        """
        self.cleanup_callbacks.append(callback)
        logger.debug("Registered cleanup callback")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if sys.platform == "win32":
            # Windows doesn't support SIGTERM
            signals = [signal.SIGINT]
        else:
            signals = [signal.SIGINT, signal.SIGTERM]

        for sig in signals:
            try:
                # Store original handler
                self._original_handlers[sig] = signal.signal(sig, self._signal_handler)  # type: ignore[arg-type]
                logger.debug(f"Registered signal handler for {sig.name}")  # type: ignore[attr-defined]
            except ValueError as e:
                # Signal not available on this platform
                logger.debug(f"Could not register handler for {sig.name}: {e}")  # type: ignore[attr-defined]

    def _restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
                logger.debug(f"Restored signal handler for {sig.name}")  # type: ignore[attr-defined]
            except ValueError as e:
                logger.debug(f"Could not restore handler for {sig.name}: {e}")  # type: ignore[attr-defined]

        self._original_handlers.clear()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        if self.shutdown_requested:
            logger.warning(f"Received signal {signum} during shutdown - forcing exit")
            sys.exit(1)

        logger.info(f"Received signal {signum} - starting graceful shutdown")

        if self.loop and self.loop.is_running():
            # Schedule shutdown in the event loop
            self.loop.create_task(self.shutdown())
        else:
            # Fallback to immediate shutdown
            sys.exit(0)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get event loop statistics.

        Returns:
            Dictionary with statistics
        """
        uptime = None
        if self.start_time and self.loop:
            if self.shutdown_time:
                uptime = self.shutdown_time - self.start_time
            else:
                uptime = self.loop.time() - self.start_time

        return {
            "running": self.running,
            "shutdown_requested": self.shutdown_requested,
            "uptime": uptime,
            "background_tasks": len(self.background_tasks),
            "tasks_created": self.tasks_created,
            "tasks_completed": self.tasks_completed,
            "tasks_cancelled": self.tasks_cancelled,
            "cleanup_callbacks": len(self.cleanup_callbacks),
        }

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to be requested."""
        while self.running and not self.shutdown_requested:
            await asyncio.sleep(0.1)


@asynccontextmanager
async def managed_event_loop(config: EventLoopConfig | None = None) -> Any:
    """
    Async context manager for event loop lifecycle.

    Args:
        config: Event loop configuration

    Yields:
        AsyncEventLoopManager instance
    """
    if config is None:
        config = EventLoopConfig()

    manager = AsyncEventLoopManager(config)

    try:
        await manager.start()
        yield manager
    finally:
        await manager.shutdown()


class AutoMarketMakerEventLoop:
    """
    Specialized event loop for AutoMarketMaker operations.

    Combines WebSocket connection management with event loop lifecycle
    for clean async market making operations.
    """

    def __init__(
        self,
        connection_manager: AsyncWebSocketConnectionManager,
        event_loop_config: EventLoopConfig | None = None,
    ):
        """
        Initialize market maker event loop.

        Args:
            connection_manager: WebSocket connection manager
            event_loop_config: Event loop configuration
        """
        self.connection_manager = connection_manager
        self.event_loop_manager = AsyncEventLoopManager(event_loop_config or EventLoopConfig())

        # Market making state
        self.market_making_active = False
        self.replenish_task: asyncio.Task | None = None

        # Register cleanup
        self.event_loop_manager.register_cleanup_callback(self._cleanup_market_making)

    async def start_market_making(self, replenish_interval: float = 30.0) -> None:
        """
        Start market making with WebSocket monitoring.

        Args:
            replenish_interval: Interval for order replenishment in seconds
        """
        if self.market_making_active:
            logger.warning("Market making already active")
            return

        logger.info("Starting market making event loop")

        # Start event loop manager
        await self.event_loop_manager.start()

        # Connect WebSocket
        if not await self.connection_manager.connect():
            raise RuntimeError("Failed to establish WebSocket connection")

        # Start market making
        self.market_making_active = True

        # Start replenishment task
        self.replenish_task = self.event_loop_manager.create_task(
            self._replenishment_loop(replenish_interval), name="order_replenishment"
        )

        logger.info("Market making event loop started")

    async def stop_market_making(self) -> None:
        """Stop market making and clean up resources."""
        if not self.market_making_active:
            logger.warning("Market making not active")
            return

        logger.info("Stopping market making event loop")

        self.market_making_active = False

        # Cancel replenishment task
        if self.replenish_task and not self.replenish_task.done():
            self.replenish_task.cancel()

        # Shutdown event loop manager (will also disconnect WebSocket)
        await self.event_loop_manager.shutdown()

        logger.info("Market making event loop stopped")

    async def _replenishment_loop(self, interval: float) -> None:
        """Periodic order replenishment loop."""
        logger.info(f"Starting order replenishment loop (interval: {interval}s)")

        # Initial delay to let orders settle
        await asyncio.sleep(interval)

        while self.market_making_active and not self.event_loop_manager.shutdown_requested:
            try:
                if self.market_making_active:
                    # Replenishment logic would be implemented here
                    # For now, just log that we're checking
                    logger.debug("Checking for orders to replenish")

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info("Order replenishment loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in replenishment loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(interval)

        logger.info("Order replenishment loop stopped")

    async def _cleanup_market_making(self) -> None:
        """Cleanup callback for market making resources."""
        logger.info("Cleaning up market making resources")

        self.market_making_active = False

        # Disconnect WebSocket
        if self.connection_manager.is_connected():
            await self.connection_manager.disconnect()

    async def run_until_shutdown(self) -> None:
        """Run the event loop until shutdown is requested."""
        await self.event_loop_manager.wait_for_shutdown()

    def get_status(self) -> dict[str, Any]:
        """
        Get market making status.

        Returns:
            Status dictionary
        """
        return {
            "market_making_active": self.market_making_active,
            "websocket_connected": self.connection_manager.is_connected(),
            "websocket_healthy": self.connection_manager.is_healthy(),
            "event_loop_stats": self.event_loop_manager.get_statistics(),
            "connection_stats": self.connection_manager.get_connection_stats(),
        }
