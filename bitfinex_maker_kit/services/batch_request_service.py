"""
Request batching and debouncing service for Maker-Kit.

Provides intelligent request batching, debouncing, and rate limiting
to optimize API usage and comply with exchange rate limits.
"""

import asyncio
import hashlib
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class RequestPriority(Enum):
    """Request priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BatchConfig:
    """Configuration for request batching."""

    max_batch_size: int = 10
    batch_timeout: float = 0.1  # 100ms
    debounce_window: float = 0.05  # 50ms
    max_concurrent_batches: int = 5
    rate_limit_per_second: int = 60
    enable_deduplication: bool = True


@dataclass
class PendingRequest[T]:
    """Represents a pending request."""

    key: str
    params: dict[str, Any]
    future: asyncio.Future[T]
    timestamp: float
    priority: RequestPriority
    request_id: str = field(default_factory=lambda: str(time.time()))

    def __post_init__(self) -> None:
        """Generate request ID if not provided."""
        if not self.request_id:
            content = f"{self.key}:{self.params}:{self.timestamp}"
            self.request_id = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]


@dataclass
class RateLimitState:
    """Rate limiting state."""

    requests_in_window: deque = field(default_factory=deque)
    window_start: float = field(default_factory=time.time)
    requests_count: int = 0

    def add_request(self, timestamp: float) -> None:
        """Add request to rate limit tracking."""
        self.requests_in_window.append(timestamp)
        self.requests_count += 1

    def cleanup_old_requests(self, window_size: float = 1.0) -> None:
        """Remove requests older than window."""
        cutoff = time.time() - window_size
        while self.requests_in_window and self.requests_in_window[0] < cutoff:
            self.requests_in_window.popleft()
            self.requests_count -= 1

    def can_make_request(self, rate_limit: int, window_size: float = 1.0) -> bool:
        """Check if request can be made within rate limit."""
        self.cleanup_old_requests(window_size)
        return len(self.requests_in_window) < rate_limit


class BatchRequestService:
    """
    Service for batching, debouncing, and rate limiting API requests.

    Optimizes API usage by grouping related requests, removing duplicates,
    and respecting rate limits while maintaining response times.
    """

    def __init__(self, config: BatchConfig | None = None):
        """
        Initialize batch request service.

        Args:
            config: Batching configuration
        """
        self.config = config or BatchConfig()

        # Request batching state
        self._pending_requests: dict[str, list[PendingRequest]] = defaultdict(list)
        self._batch_timers: dict[str, asyncio.Handle] = {}
        self._active_batches: set[str] = set()

        # Rate limiting state
        self._rate_limit_state = RateLimitState()

        # Request handlers
        self._batch_handlers: dict[str, Callable] = {}

        # Deduplication tracking
        self._request_hashes: dict[str, PendingRequest] = {}

        # Statistics
        self._stats = {
            "total_requests": 0,
            "batched_requests": 0,
            "deduplicated_requests": 0,
            "rate_limited_requests": 0,
            "average_batch_size": 0.0,
            "batches_executed": 0,
        }

        # Concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        self._shutdown = False

    def register_batch_handler(self, request_type: str, handler: Callable) -> None:
        """
        Register a batch handler for a request type.

        Args:
            request_type: Type of request to handle
            handler: Async function to handle batched requests
        """
        self._batch_handlers[request_type] = handler
        logger.info(f"Registered batch handler for {request_type}")

    def _create_request_hash(self, request_type: str, params: dict[str, Any]) -> str:
        """Create hash for request deduplication."""
        content = f"{request_type}:{sorted(params.items())}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    async def make_request(
        self,
        request_type: str,
        params: dict[str, Any],
        priority: RequestPriority = RequestPriority.NORMAL,
    ) -> Any:
        """
        Make a batched/debounced request.

        Args:
            request_type: Type of request
            params: Request parameters
            priority: Request priority

        Returns:
            Request result

        Raises:
            ValueError: If no handler registered for request type
            asyncio.TimeoutError: If request times out
        """
        if self._shutdown:
            raise RuntimeError("Batch request service is shutting down")

        if request_type not in self._batch_handlers:
            raise ValueError(f"No handler registered for request type: {request_type}")

        self._stats["total_requests"] += 1

        # Check for deduplication
        request_hash = self._create_request_hash(request_type, params)

        if self.config.enable_deduplication and request_hash in self._request_hashes:
            # Return existing future for identical request
            existing_request = self._request_hashes[request_hash]
            self._stats["deduplicated_requests"] += 1
            logger.debug(f"Deduplicated request: {request_type} - {request_hash}")
            return await existing_request.future

        # Create new request
        future: asyncio.Future[Any] = asyncio.Future()
        request = PendingRequest(
            key=request_type, params=params, future=future, timestamp=time.time(), priority=priority
        )

        # Track for deduplication
        if self.config.enable_deduplication:
            self._request_hashes[request_hash] = request

        # Add to pending requests
        self._pending_requests[request_type].append(request)

        # Sort by priority and timestamp
        self._pending_requests[request_type].sort(
            key=lambda r: (r.priority.value, r.timestamp), reverse=True
        )

        # Schedule batch processing
        await self._schedule_batch_processing(request_type)

        try:
            return await future
        finally:
            # Clean up deduplication tracking
            if self.config.enable_deduplication and request_hash in self._request_hashes:
                del self._request_hashes[request_hash]

    async def _schedule_batch_processing(self, request_type: str) -> None:
        """Schedule batch processing for a request type."""
        # Cancel existing timer if any
        if request_type in self._batch_timers:
            self._batch_timers[request_type].cancel()

        # Check if we should process immediately
        pending_count = len(self._pending_requests[request_type])

        if pending_count >= self.config.max_batch_size:
            # Process immediately if batch is full
            task = asyncio.create_task(self._process_batch(request_type))
            # Store reference to prevent garbage collection
            if not hasattr(self, "_background_tasks"):
                self._background_tasks = set()
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        else:
            # Schedule processing after timeout
            loop = asyncio.get_event_loop()

            def schedule_batch() -> None:
                task = asyncio.create_task(self._process_batch(request_type))
                if not hasattr(self, "_background_tasks"):
                    self._background_tasks = set()
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

            timer = loop.call_later(self.config.batch_timeout, schedule_batch)
            self._batch_timers[request_type] = timer

    async def _process_batch(self, request_type: str) -> None:
        """Process a batch of requests."""
        if request_type in self._active_batches:
            return  # Already processing

        # Cancel timer if exists
        if request_type in self._batch_timers:
            self._batch_timers[request_type].cancel()
            del self._batch_timers[request_type]

        # Get pending requests
        requests = self._pending_requests[request_type]
        if not requests:
            return

        # Clear pending requests
        self._pending_requests[request_type] = []

        # Mark as active
        self._active_batches.add(request_type)

        try:
            async with self._semaphore:
                await self._execute_batch(request_type, requests)
        finally:
            self._active_batches.discard(request_type)

    async def _execute_batch(self, request_type: str, requests: list[PendingRequest]) -> None:
        """Execute a batch of requests."""
        if not requests:
            return

        # Check rate limiting
        if not self._rate_limit_state.can_make_request(self.config.rate_limit_per_second):
            # Apply backoff
            await self._apply_rate_limit_backoff()

        batch_size = len(requests)
        self._stats["batched_requests"] += batch_size
        self._stats["batches_executed"] += 1

        # Update average batch size
        total_batches = self._stats["batches_executed"]
        current_avg = self._stats["average_batch_size"]
        self._stats["average_batch_size"] = (
            current_avg * (total_batches - 1) + batch_size
        ) / total_batches

        handler = self._batch_handlers[request_type]

        try:
            logger.debug(f"Executing batch of {batch_size} {request_type} requests")

            # Record rate limit
            self._rate_limit_state.add_request(time.time())

            # Execute batch handler
            results = await handler([req.params for req in requests])

            # Distribute results to futures
            if isinstance(results, list) and len(results) == len(requests):
                # One result per request
                for request, result in zip(requests, results, strict=False):
                    if not request.future.done():
                        request.future.set_result(result)
            else:
                # Single result for all requests (e.g., batch operation)
                for request in requests:
                    if not request.future.done():
                        request.future.set_result(results)

            logger.debug(f"Batch execution completed for {request_type}")

        except Exception as e:
            logger.error(f"Batch execution failed for {request_type}: {e}")

            # Set exception on all futures
            for request in requests:
                if not request.future.done():
                    request.future.set_exception(e)

    async def _apply_rate_limit_backoff(self) -> None:
        """Apply rate limit backoff."""
        self._stats["rate_limited_requests"] += 1

        # Calculate backoff time
        backoff_time = 1.0 / self.config.rate_limit_per_second

        logger.debug(f"Rate limit reached, backing off for {backoff_time:.3f}s")
        await asyncio.sleep(backoff_time)

    async def flush_pending_requests(self, request_type: str | None = None) -> None:
        """
        Flush pending requests immediately.

        Args:
            request_type: Specific request type to flush, or None for all
        """
        if request_type:
            if request_type in self._pending_requests:
                await self._process_batch(request_type)
        else:
            # Flush all pending request types
            for req_type in list(self._pending_requests.keys()):
                await self._process_batch(req_type)

    def get_stats(self) -> dict[str, Any]:
        """
        Get batch request statistics.

        Returns:
            Dictionary with statistics
        """
        total_requests = self._stats["total_requests"]
        batching_efficiency = 0.0

        if total_requests > 0:
            batching_efficiency = (self._stats["batched_requests"] / total_requests) * 100

        pending_counts = {
            req_type: len(requests) for req_type, requests in self._pending_requests.items()
        }

        return {
            "total_requests": total_requests,
            "batched_requests": self._stats["batched_requests"],
            "deduplicated_requests": self._stats["deduplicated_requests"],
            "rate_limited_requests": self._stats["rate_limited_requests"],
            "batches_executed": self._stats["batches_executed"],
            "average_batch_size": self._stats["average_batch_size"],
            "batching_efficiency_pct": batching_efficiency,
            "pending_requests": pending_counts,
            "active_batches": len(self._active_batches),
            "current_rate_limit_usage": len(self._rate_limit_state.requests_in_window),
        }

    async def shutdown(self, timeout: float = 5.0) -> None:
        """
        Shutdown the batch request service.

        Args:
            timeout: Maximum time to wait for pending requests
        """
        self._shutdown = True

        logger.info("Shutting down batch request service...")

        # Cancel all timers
        for timer in self._batch_timers.values():
            timer.cancel()
        self._batch_timers.clear()

        # Flush all pending requests
        try:
            await asyncio.wait_for(self.flush_pending_requests(), timeout=timeout)
        except TimeoutError:
            logger.warning("Timeout waiting for pending requests to complete")

        # Cancel any remaining futures
        for requests in self._pending_requests.values():
            for request in requests:
                if not request.future.done():
                    request.future.cancel()

        self._pending_requests.clear()
        self._request_hashes.clear()

        logger.info("Batch request service shutdown complete")


def create_batch_request_service(config: BatchConfig | None = None) -> BatchRequestService:
    """
    Create batch request service with configuration.

    Args:
        config: Optional batch configuration

    Returns:
        Configured BatchRequestService instance
    """
    return BatchRequestService(config)
