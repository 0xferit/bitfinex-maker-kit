"""
API response fixtures for testing.

Provides realistic API response scenarios for comprehensive testing
of API interactions, error handling, and data processing.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseStatus(Enum):
    """API response status codes."""

    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMITED = 429
    SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


@dataclass
class APIResponseFixture:
    """Base fixture for API responses."""

    status_code: int
    data: Any = None
    error: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize default headers."""
        if not self.headers:
            self.headers = {
                "Content-Type": "application/json",
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": "59",
                "X-RateLimit-Reset": str(int(time.time() + 60)),
            }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        response = {
            "status_code": self.status_code,
            "headers": self.headers,
            "timestamp": self.timestamp,
        }

        if self.data is not None:
            response["data"] = self.data

        if self.error is not None:
            response["error"] = self.error

        return response

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class SuccessResponseFixture(APIResponseFixture):
    """Fixture for successful API responses."""

    status_code: int = ResponseStatus.SUCCESS.value

    def __post_init__(self):
        super().__post_init__()
        # Ensure error is None for success responses
        self.error = None


@dataclass
class ErrorResponseFixture(APIResponseFixture):
    """Fixture for error API responses."""

    status_code: int = ResponseStatus.BAD_REQUEST.value
    error_code: str = "GENERIC_ERROR"
    error_message: str = "An error occurred"

    def __post_init__(self):
        super().__post_init__()
        # Set error data
        self.error = {
            "code": self.error_code,
            "message": self.error_message,
            "timestamp": self.timestamp,
        }
        # Ensure data is None for error responses
        self.data = None


@dataclass
class WebSocketMessageFixture:
    """Fixture for WebSocket messages."""

    channel: str
    event: str
    data: Any = None
    chanId: int | None = None
    symbol: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        message = {"channel": self.channel, "event": self.event, "timestamp": self.timestamp}

        if self.data is not None:
            message["data"] = self.data

        if self.chanId is not None:
            message["chanId"] = self.chanId

        if self.symbol is not None:
            message["symbol"] = self.symbol

        return message

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class APIResponseFixtures:
    """
    Factory class for creating comprehensive API response fixtures.

    Provides realistic API response scenarios for testing various
    API interactions and error conditions.
    """

    @classmethod
    def create_ticker_response(cls, symbol: str = "tBTCUSD", **kwargs) -> SuccessResponseFixture:
        """Create ticker API response."""
        ticker_data = {
            "symbol": symbol,
            "bid": kwargs.get("bid", 49950.0),
            "ask": kwargs.get("ask", 50050.0),
            "last_price": kwargs.get("last_price", 50000.0),
            "bid_size": kwargs.get("bid_size", 1.5),
            "ask_size": kwargs.get("ask_size", 2.0),
            "volume": kwargs.get("volume", 1000.0),
            "high": kwargs.get("high", 51000.0),
            "low": kwargs.get("low", 49000.0),
            "timestamp": time.time(),
        }

        return SuccessResponseFixture(data=ticker_data)

    @classmethod
    def create_orderbook_response(
        cls, symbol: str = "tBTCUSD", levels: int = 10
    ) -> SuccessResponseFixture:
        """Create order book API response."""
        base_price = 50000.0

        bids = []
        asks = []

        for i in range(levels):
            # Bids (decreasing prices)
            bid_price = base_price * (1 - (i + 1) * 0.0001)
            bid_amount = 1.0 + (i * 0.5)
            bids.append([bid_price, bid_amount])

            # Asks (increasing prices)
            ask_price = base_price * (1 + (i + 1) * 0.0001)
            ask_amount = 1.0 + (i * 0.5)
            asks.append([ask_price, ask_amount])

        orderbook_data = {"symbol": symbol, "bids": bids, "asks": asks, "timestamp": time.time()}

        return SuccessResponseFixture(data=orderbook_data)

    @classmethod
    def create_order_response(cls, order_id: int = 12345678, **kwargs) -> SuccessResponseFixture:
        """Create order API response."""
        order_data = {
            "id": order_id,
            "symbol": kwargs.get("symbol", "tBTCUSD"),
            "amount": kwargs.get("amount", "0.1"),
            "price": kwargs.get("price", "50000.0"),
            "side": kwargs.get("side", "buy"),
            "type": kwargs.get("type", "EXCHANGE LIMIT"),
            "status": kwargs.get("status", "ACTIVE"),
            "timestamp": time.time(),
            "flags": kwargs.get("flags", 512),  # POST_ONLY
            "client_order_id": kwargs.get("client_order_id", f"client_{order_id}"),
        }

        return SuccessResponseFixture(data=order_data)

    @classmethod
    def create_orders_list_response(cls, count: int = 5) -> SuccessResponseFixture:
        """Create orders list API response."""
        orders = []

        for i in range(count):
            order_id = 12345678 + i
            side = "buy" if i % 2 == 0 else "sell"
            price = 50000.0 + (i * 100) * (1 if side == "sell" else -1)

            order = {
                "id": order_id,
                "symbol": "tBTCUSD",
                "amount": "0.1",
                "price": str(price),
                "side": side,
                "type": "EXCHANGE LIMIT",
                "status": "ACTIVE",
                "timestamp": time.time() - (i * 60),  # Spread over time
                "flags": 512,
            }
            orders.append(order)

        return SuccessResponseFixture(data=orders)

    @classmethod
    def create_wallet_response(cls) -> SuccessResponseFixture:
        """Create wallet API response."""
        wallets = [
            {"currency": "USD", "type": "exchange", "balance": 10000.0, "available": 9500.0},
            {"currency": "BTC", "type": "exchange", "balance": 1.0, "available": 0.9},
            {"currency": "ETH", "type": "exchange", "balance": 10.0, "available": 9.5},
        ]

        return SuccessResponseFixture(data=wallets)

    @classmethod
    def create_trades_response(
        cls, symbol: str = "tBTCUSD", count: int = 20
    ) -> SuccessResponseFixture:
        """Create trades API response."""
        trades = []
        current_time = time.time()
        base_price = 50000.0

        for i in range(count):
            # Simulate price movement
            price_change = (i - count / 2) * 10  # Small price changes
            price = base_price + price_change

            trade = {
                "id": 1000000 + i,
                "timestamp": current_time - (i * 60),  # 1 minute intervals
                "price": price,
                "amount": round(0.01 + (i * 0.01), 6),
                "side": "buy" if i % 2 == 0 else "sell",
            }
            trades.append(trade)

        return SuccessResponseFixture(data=trades)

    @classmethod
    def create_error_response(
        cls, error_type: str = "INVALID_REQUEST", status_code: int = 400
    ) -> ErrorResponseFixture:
        """Create error API response."""
        error_messages = {
            "INVALID_REQUEST": "Invalid request parameters",
            "UNAUTHORIZED": "Invalid API credentials",
            "RATE_LIMITED": "Rate limit exceeded",
            "INSUFFICIENT_BALANCE": "Insufficient account balance",
            "INVALID_SYMBOL": "Invalid trading symbol",
            "ORDER_NOT_FOUND": "Order not found",
            "SERVER_ERROR": "Internal server error",
            "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
        }

        return ErrorResponseFixture(
            status_code=status_code,
            error_code=error_type,
            error_message=error_messages.get(error_type, "Unknown error"),
        )

    @classmethod
    def create_rate_limit_response(cls) -> ErrorResponseFixture:
        """Create rate limit error response."""
        response = cls.create_error_response("RATE_LIMITED", 429)
        response.headers.update(
            {
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + 60)),
                "Retry-After": "60",
            }
        )
        return response

    @classmethod
    def create_websocket_messages(cls) -> list[WebSocketMessageFixture]:
        """Create WebSocket message fixtures."""
        return [
            # Subscription confirmation
            WebSocketMessageFixture(
                channel="ticker", event="subscribed", chanId=1, symbol="tBTCUSD"
            ),
            # Ticker update
            WebSocketMessageFixture(
                channel="ticker",
                event="update",
                chanId=1,
                data=[
                    1,
                    50000.0,
                    0.1,
                    50050.0,
                    0.2,
                    100.0,
                    0.002,
                    50000.0,
                    1000.0,
                    51000.0,
                    49000.0,
                ],
            ),
            # Order update
            WebSocketMessageFixture(
                channel="orders",
                event="update",
                data={
                    "id": 12345678,
                    "symbol": "tBTCUSD",
                    "status": "EXECUTED",
                    "amount": "0.1",
                    "price": "50000.0",
                },
            ),
            # Error message
            WebSocketMessageFixture(
                channel="error",
                event="error",
                data={"code": "SUBSCRIPTION_FAILED", "message": "Failed to subscribe to channel"},
            ),
        ]

    @classmethod
    def create_batch_response(
        cls, requests: list[dict[str, Any]]
    ) -> list[SuccessResponseFixture | ErrorResponseFixture]:
        """Create batch API response."""
        responses = []

        for request in requests:
            request_type = request.get("type")

            if request_type == "ticker":
                responses.append(cls.create_ticker_response(request.get("symbol", "tBTCUSD")))
            elif request_type == "order":
                responses.append(cls.create_order_response())
            elif request_type == "orders":
                responses.append(cls.create_orders_list_response())
            else:
                responses.append(cls.create_error_response("INVALID_REQUEST"))

        return responses

    @classmethod
    def create_network_error_scenarios(cls) -> dict[str, Exception]:
        """Create network error scenarios."""
        return {
            "connection_timeout": ConnectionError("Connection timed out"),
            "connection_refused": ConnectionError("Connection refused"),
            "dns_resolution_failed": ConnectionError("DNS resolution failed"),
            "ssl_error": ConnectionError("SSL certificate verification failed"),
            "read_timeout": TimeoutError("Read operation timed out"),
            "write_timeout": TimeoutError("Write operation timed out"),
        }
