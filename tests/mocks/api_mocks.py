"""
API mock utilities for testing.

Provides comprehensive mocking for Bitfinex API interactions,
WebSocket connections, and external service calls.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union
from unittest.mock import Mock, AsyncMock, MagicMock
from ..fixtures.api_responses import APIResponseFixtures, SuccessResponseFixture, ErrorResponseFixture


class MockBitfinexAPI:
    """
    Comprehensive mock for Bitfinex API.
    
    Provides realistic API responses with configurable behavior
    for testing various scenarios and edge cases.
    """
    
    def __init__(self, response_delay: float = 0.0, 
                 error_rate: float = 0.0,
                 rate_limit_enabled: bool = False):
        """
        Initialize mock API.
        
        Args:
            response_delay: Simulated response delay in seconds
            error_rate: Probability of returning errors (0.0 to 1.0)
            rate_limit_enabled: Whether to simulate rate limiting
        """
        self.response_delay = response_delay
        self.error_rate = error_rate
        self.rate_limit_enabled = rate_limit_enabled
        
        # Track API calls
        self.call_count = 0
        self.call_history = []
        self.last_call_time = 0
        
        # Rate limiting state
        self.rate_limit_calls = 0
        self.rate_limit_window_start = time.time()
        self.rate_limit_per_minute = 60
        
        # Configure default responses
        self.responses = APIResponseFixtures()
    
    async def _simulate_delay(self):
        """Simulate API response delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def _should_return_error(self) -> bool:
        """Determine if should return error based on error rate."""
        import random
        return random.random() < self.error_rate
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded."""
        if not self.rate_limit_enabled:
            return False
        
        current_time = time.time()
        
        # Reset rate limit window if needed
        if current_time - self.rate_limit_window_start >= 60:
            self.rate_limit_calls = 0
            self.rate_limit_window_start = current_time
        
        self.rate_limit_calls += 1
        return self.rate_limit_calls > self.rate_limit_per_minute
    
    def _record_call(self, method: str, **kwargs):
        """Record API call for tracking."""
        self.call_count += 1
        self.last_call_time = time.time()
        
        call_record = {
            'method': method,
            'timestamp': self.last_call_time,
            'call_number': self.call_count,
            'kwargs': kwargs
        }
        self.call_history.append(call_record)
    
    async def get_ticker(self, symbol: str = 'tBTCUSD') -> Dict[str, Any]:
        """Mock get ticker API call."""
        self._record_call('get_ticker', symbol=symbol)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception(f"API error fetching ticker for {symbol}")
        
        response = self.responses.create_ticker_response(symbol)
        return response.data
    
    async def get_orderbook(self, symbol: str = 'tBTCUSD', 
                          precision: str = 'P0') -> Dict[str, Any]:
        """Mock get orderbook API call."""
        self._record_call('get_orderbook', symbol=symbol, precision=precision)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception(f"API error fetching orderbook for {symbol}")
        
        response = self.responses.create_orderbook_response(symbol)
        return response.data
    
    async def get_trades(self, symbol: str = 'tBTCUSD', 
                        limit: int = 50) -> List[Dict[str, Any]]:
        """Mock get trades API call."""
        self._record_call('get_trades', symbol=symbol, limit=limit)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception(f"API error fetching trades for {symbol}")
        
        response = self.responses.create_trades_response(symbol, limit)
        return response.data
    
    async def get_wallets(self) -> List[Dict[str, Any]]:
        """Mock get wallets API call."""
        self._record_call('get_wallets')
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception("API error fetching wallets")
        
        response = self.responses.create_wallet_response()
        return response.data
    
    async def submit_order(self, symbol: str, amount: str, price: str,
                          side: str, order_type: str = 'EXCHANGE LIMIT',
                          **kwargs) -> Dict[str, Any]:
        """Mock submit order API call."""
        self._record_call('submit_order', symbol=symbol, amount=amount, 
                         price=price, side=side, order_type=order_type, **kwargs)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception(f"API error submitting order for {symbol}")
        
        # Generate order ID
        order_id = 10000000 + self.call_count
        
        response = self.responses.create_order_response(
            order_id=order_id,
            symbol=symbol,
            amount=amount,
            price=price,
            side=side,
            type=order_type
        )
        return response.data
    
    async def cancel_order(self, order_id: int, symbol: str = None) -> Dict[str, Any]:
        """Mock cancel order API call."""
        self._record_call('cancel_order', order_id=order_id, symbol=symbol)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception(f"API error canceling order {order_id}")
        
        response = self.responses.create_order_response(
            order_id=order_id,
            status='CANCELED'
        )
        return response.data
    
    async def get_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Mock get orders API call."""
        self._record_call('get_orders', symbol=symbol)
        await self._simulate_delay()
        
        if self._check_rate_limit():
            raise Exception("Rate limit exceeded")
        
        if self._should_return_error():
            raise Exception("API error fetching orders")
        
        response = self.responses.create_orders_list_response()
        return response.data
    
    def get_call_stats(self) -> Dict[str, Any]:
        """Get API call statistics."""
        method_counts = {}
        for call in self.call_history:
            method = call['method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'total_calls': self.call_count,
            'method_counts': method_counts,
            'last_call_time': self.last_call_time,
            'rate_limit_calls': self.rate_limit_calls
        }
    
    def reset_stats(self):
        """Reset call statistics."""
        self.call_count = 0
        self.call_history.clear()
        self.rate_limit_calls = 0
        self.rate_limit_window_start = time.time()


class MockWebSocketConnection:
    """
    Mock WebSocket connection for testing.
    
    Simulates WebSocket behavior including connection lifecycle,
    message sending/receiving, and error conditions.
    """
    
    def __init__(self, auto_connect: bool = True, 
                 message_delay: float = 0.0):
        """
        Initialize mock WebSocket.
        
        Args:
            auto_connect: Whether to auto-connect on creation
            message_delay: Delay for message operations
        """
        self.auto_connect = auto_connect
        self.message_delay = message_delay
        
        # Connection state
        self.connected = auto_connect
        self.closed = False
        
        # Message queues
        self.sent_messages = []
        self.received_messages = []
        self.message_queue = asyncio.Queue()
        
        # Event tracking
        self.events = []
        
        # Callbacks
        self.on_message: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
    
    async def connect(self, uri: str):
        """Mock WebSocket connect."""
        if self.message_delay > 0:
            await asyncio.sleep(self.message_delay)
        
        self.connected = True
        self.closed = False
        
        self.events.append({
            'type': 'connect',
            'uri': uri,
            'timestamp': time.time()
        })
    
    async def send(self, message: Union[str, Dict[str, Any]]):
        """Mock WebSocket send."""
        if not self.connected:
            raise Exception("WebSocket not connected")
        
        if self.message_delay > 0:
            await asyncio.sleep(self.message_delay)
        
        if isinstance(message, dict):
            message = json.dumps(message)
        
        self.sent_messages.append({
            'message': message,
            'timestamp': time.time()
        })
        
        self.events.append({
            'type': 'send',
            'message': message,
            'timestamp': time.time()
        })
    
    async def recv(self) -> str:
        """Mock WebSocket receive."""
        if not self.connected:
            raise Exception("WebSocket not connected")
        
        # Wait for message in queue
        message = await self.message_queue.get()
        
        self.events.append({
            'type': 'recv',
            'message': message,
            'timestamp': time.time()
        })
        
        return message
    
    async def close(self):
        """Mock WebSocket close."""
        self.connected = False
        self.closed = True
        
        self.events.append({
            'type': 'close',
            'timestamp': time.time()
        })
        
        if self.on_close:
            await self.on_close()
    
    async def simulate_message(self, message: Union[str, Dict[str, Any]]):
        """Simulate receiving a message."""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        await self.message_queue.put(message)
        
        self.received_messages.append({
            'message': message,
            'timestamp': time.time()
        })
        
        if self.on_message:
            await self.on_message(message)
    
    async def simulate_error(self, error_message: str):
        """Simulate WebSocket error."""
        self.events.append({
            'type': 'error',
            'error': error_message,
            'timestamp': time.time()
        })
        
        if self.on_error:
            await self.on_error(Exception(error_message))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            'connected': self.connected,
            'closed': self.closed,
            'sent_count': len(self.sent_messages),
            'received_count': len(self.received_messages),
            'event_count': len(self.events),
            'last_event': self.events[-1] if self.events else None
        }


class MockAPIResponse:
    """Mock API response object."""
    
    def __init__(self, status_code: int = 200, 
                 data: Any = None, 
                 headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self.data = data
        self.headers = headers or {}
        self.text = json.dumps(data) if data else ""
    
    def json(self) -> Any:
        """Return JSON data."""
        return self.data
    
    def raise_for_status(self):
        """Raise exception for HTTP errors."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


def create_mock_api(scenario: str = 'normal') -> MockBitfinexAPI:
    """
    Create mock API with predefined scenario.
    
    Args:
        scenario: Predefined scenario ('normal', 'slow', 'errors', 'rate_limited')
    """
    scenarios = {
        'normal': {
            'response_delay': 0.0,
            'error_rate': 0.0,
            'rate_limit_enabled': False
        },
        'slow': {
            'response_delay': 0.5,
            'error_rate': 0.0,
            'rate_limit_enabled': False
        },
        'errors': {
            'response_delay': 0.0,
            'error_rate': 0.2,  # 20% error rate
            'rate_limit_enabled': False
        },
        'rate_limited': {
            'response_delay': 0.0,
            'error_rate': 0.0,
            'rate_limit_enabled': True
        },
        'stress': {
            'response_delay': 1.0,
            'error_rate': 0.1,
            'rate_limit_enabled': True
        }
    }
    
    config = scenarios.get(scenario, scenarios['normal'])
    return MockBitfinexAPI(**config)


def create_mock_websocket(scenario: str = 'normal') -> MockWebSocketConnection:
    """
    Create mock WebSocket with predefined scenario.
    
    Args:
        scenario: Predefined scenario ('normal', 'slow', 'disconnected')
    """
    scenarios = {
        'normal': {
            'auto_connect': True,
            'message_delay': 0.0
        },
        'slow': {
            'auto_connect': True,
            'message_delay': 0.1
        },
        'disconnected': {
            'auto_connect': False,
            'message_delay': 0.0
        }
    }
    
    config = scenarios.get(scenario, scenarios['normal'])
    return MockWebSocketConnection(**config)