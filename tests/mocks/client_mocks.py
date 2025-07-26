"""
Client mock utilities for testing.

Provides comprehensive mocking for Bitfinex clients and external
API interactions with realistic behavior simulation.
"""

import time
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
from ..fixtures.api_responses import APIResponseFixtures


class MockBitfinexClient:
    """
    Mock Bitfinex client for testing.
    
    Provides realistic client behavior without actual API calls,
    allowing for comprehensive client interaction testing.
    """
    
    def __init__(self, api_key: str = "test_key", 
                 api_secret: str = "test_secret",
                 response_delay: float = 0.0):
        """
        Initialize mock client.
        
        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            response_delay: Simulated response delay
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.response_delay = response_delay
        
        # Client state
        self.authenticated = bool(api_key and api_secret)
        self.connected = True
        
        # Response fixtures
        self.fixtures = APIResponseFixtures()
        
        # Call tracking
        self.call_history = []
        self.call_count = 0
    
    def _record_call(self, method: str, **kwargs):
        """Record method call for tracking."""
        self.call_count += 1
        self.call_history.append({
            'method': method,
            'timestamp': time.time(),
            'call_number': self.call_count,
            'kwargs': kwargs
        })
    
    def _simulate_delay(self):
        """Simulate response delay."""
        if self.response_delay > 0:
            time.sleep(self.response_delay)
    
    def get_ticker(self, symbol: str = 'tBTCUSD') -> Mock:
        """Mock get ticker method."""
        self._record_call('get_ticker', symbol=symbol)
        self._simulate_delay()
        
        # Create mock ticker object
        ticker = Mock()
        response = self.fixtures.create_ticker_response(symbol)
        data = response.data
        
        ticker.symbol = data['symbol']
        ticker.bid = data['bid']
        ticker.ask = data['ask']
        ticker.last_price = data['last_price']
        ticker.bid_size = data['bid_size']
        ticker.ask_size = data['ask_size']
        ticker.volume = data['volume']
        ticker.high = data['high']
        ticker.low = data['low']
        ticker.timestamp = data['timestamp']
        
        return ticker
    
    def get_orderbook(self, symbol: str = 'tBTCUSD', 
                     precision: str = 'P0') -> Mock:
        """Mock get orderbook method."""
        self._record_call('get_orderbook', symbol=symbol, precision=precision)
        self._simulate_delay()
        
        # Create mock orderbook object
        orderbook = Mock()
        response = self.fixtures.create_orderbook_response(symbol)
        data = response.data
        
        orderbook.symbol = data['symbol']
        orderbook.timestamp = data['timestamp']
        
        # Create bid/ask objects
        orderbook.bids = []
        for bid_data in data['bids']:
            bid = Mock()
            bid.price = bid_data[0]
            bid.amount = bid_data[1]
            orderbook.bids.append(bid)
        
        orderbook.asks = []
        for ask_data in data['asks']:
            ask = Mock()
            ask.price = ask_data[0]
            ask.amount = ask_data[1]
            orderbook.asks.append(ask)
        
        return orderbook
    
    def get_trades(self, symbol: str = 'tBTCUSD', limit: int = 50) -> List[Mock]:
        """Mock get trades method."""
        self._record_call('get_trades', symbol=symbol, limit=limit)
        self._simulate_delay()
        
        response = self.fixtures.create_trades_response(symbol, limit)
        trades = []
        
        for trade_data in response.data:
            trade = Mock()
            trade.id = trade_data['id']
            trade.timestamp = trade_data['timestamp']
            trade.price = trade_data['price']
            trade.amount = trade_data['amount']
            trade.side = trade_data['side']
            trades.append(trade)
        
        return trades
    
    def get_wallets(self) -> List[Mock]:
        """Mock get wallets method."""
        self._record_call('get_wallets')
        self._simulate_delay()
        
        response = self.fixtures.create_wallet_response()
        wallets = []
        
        for wallet_data in response.data:
            wallet = Mock()
            wallet.currency = wallet_data['currency']
            wallet.type = wallet_data['type']
            wallet.balance = wallet_data['balance']
            wallet.available = wallet_data['available']
            wallets.append(wallet)
        
        return wallets
    
    def submit_order(self, symbol: str, amount: str, price: str,
                    side: str, order_type: str = 'EXCHANGE LIMIT',
                    **kwargs) -> Mock:
        """Mock submit order method."""
        self._record_call('submit_order', symbol=symbol, amount=amount,
                         price=price, side=side, order_type=order_type, **kwargs)
        self._simulate_delay()
        
        if not self.authenticated:
            raise Exception("Authentication required")
        
        # Generate order ID
        order_id = 10000000 + self.call_count
        
        response = self.fixtures.create_order_response(
            order_id=order_id,
            symbol=symbol,
            amount=amount,
            price=price,
            side=side,
            type=order_type
        )
        
        # Create mock order object
        order = Mock()
        data = response.data
        
        order.id = data['id']
        order.symbol = data['symbol']
        order.amount = data['amount']
        order.price = data['price']
        order.side = data['side']
        order.type = data['type']
        order.status = data['status']
        order.timestamp = data['timestamp']
        order.flags = data['flags']
        order.client_order_id = data['client_order_id']
        
        return order
    
    def cancel_order(self, order_id: int, symbol: str = None) -> Mock:
        """Mock cancel order method."""
        self._record_call('cancel_order', order_id=order_id, symbol=symbol)
        self._simulate_delay()
        
        if not self.authenticated:
            raise Exception("Authentication required")
        
        response = self.fixtures.create_order_response(
            order_id=order_id,
            status='CANCELED'
        )
        
        # Create mock order object
        order = Mock()
        data = response.data
        
        order.id = data['id']
        order.symbol = data['symbol']
        order.amount = data['amount']
        order.price = data['price']
        order.side = data['side']
        order.type = data['type']
        order.status = data['status']
        order.timestamp = data['timestamp']
        
        return order
    
    def get_orders(self, symbol: str = None) -> List[Mock]:
        """Mock get orders method."""
        self._record_call('get_orders', symbol=symbol)
        self._simulate_delay()
        
        if not self.authenticated:
            raise Exception("Authentication required")
        
        response = self.fixtures.create_orders_list_response()
        orders = []
        
        for order_data in response.data:
            order = Mock()
            order.id = order_data['id']
            order.symbol = order_data['symbol']
            order.amount = order_data['amount']
            order.price = order_data['price']
            order.side = order_data['side']
            order.type = order_data['type']
            order.status = order_data['status']
            order.timestamp = order_data['timestamp']
            orders.append(order)
        
        return orders
    
    def get_order_status(self, order_id: int) -> Mock:
        """Mock get order status method."""
        self._record_call('get_order_status', order_id=order_id)
        self._simulate_delay()
        
        if not self.authenticated:
            raise Exception("Authentication required")
        
        response = self.fixtures.create_order_response(order_id=order_id)
        
        # Create mock order object
        order = Mock()
        data = response.data
        
        order.id = data['id']
        order.symbol = data['symbol']
        order.amount = data['amount']
        order.price = data['price']
        order.side = data['side']
        order.type = data['type']
        order.status = data['status']
        order.timestamp = data['timestamp']
        
        return order
    
    def get_call_stats(self) -> Dict[str, Any]:
        """Get client call statistics."""
        method_counts = {}
        for call in self.call_history:
            method = call['method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'total_calls': self.call_count,
            'method_counts': method_counts,
            'authenticated': self.authenticated,
            'connected': self.connected
        }
    
    def reset_stats(self):
        """Reset call statistics."""
        self.call_count = 0
        self.call_history.clear()


class MockAsyncClient:
    """
    Mock async Bitfinex client for testing.
    
    Provides async client behavior for testing async operations
    and concurrent request handling.
    """
    
    def __init__(self, api_key: str = "test_key", 
                 api_secret: str = "test_secret",
                 response_delay: float = 0.0):
        """Initialize mock async client."""
        self.sync_client = MockBitfinexClient(api_key, api_secret, response_delay)
    
    async def get_ticker(self, symbol: str = 'tBTCUSD') -> Mock:
        """Mock async get ticker method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_ticker(symbol)
    
    async def get_orderbook(self, symbol: str = 'tBTCUSD', 
                           precision: str = 'P0') -> Mock:
        """Mock async get orderbook method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_orderbook(symbol, precision)
    
    async def get_trades(self, symbol: str = 'tBTCUSD', limit: int = 50) -> List[Mock]:
        """Mock async get trades method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_trades(symbol, limit)
    
    async def get_wallets(self) -> List[Mock]:
        """Mock async get wallets method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_wallets()
    
    async def submit_order(self, symbol: str, amount: str, price: str,
                          side: str, order_type: str = 'EXCHANGE LIMIT',
                          **kwargs) -> Mock:
        """Mock async submit order method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.submit_order(symbol, amount, price, side, order_type, **kwargs)
    
    async def cancel_order(self, order_id: int, symbol: str = None) -> Mock:
        """Mock async cancel order method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.cancel_order(order_id, symbol)
    
    async def get_orders(self, symbol: str = None) -> List[Mock]:
        """Mock async get orders method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_orders(symbol)
    
    async def get_order_status(self, order_id: int) -> Mock:
        """Mock async get order status method."""
        if self.sync_client.response_delay > 0:
            import asyncio
            await asyncio.sleep(self.sync_client.response_delay)
        
        return self.sync_client.get_order_status(order_id)
    
    def get_call_stats(self) -> Dict[str, Any]:
        """Get async client call statistics."""
        return self.sync_client.get_call_stats()
    
    def reset_stats(self):
        """Reset call statistics."""
        self.sync_client.reset_stats()


def create_mock_client(scenario: str = 'normal') -> MockBitfinexClient:
    """
    Create mock client with predefined scenario.
    
    Args:
        scenario: Predefined scenario ('normal', 'slow', 'unauthenticated')
    """
    scenarios = {
        'normal': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'response_delay': 0.0
        },
        'slow': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'response_delay': 0.5
        },
        'unauthenticated': {
            'api_key': '',
            'api_secret': '',
            'response_delay': 0.0
        },
        'very_slow': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'response_delay': 2.0
        }
    }
    
    config = scenarios.get(scenario, scenarios['normal'])
    return MockBitfinexClient(**config)


def create_mock_async_client(scenario: str = 'normal') -> MockAsyncClient:
    """
    Create mock async client with predefined scenario.
    
    Args:
        scenario: Predefined scenario ('normal', 'slow', 'unauthenticated')
    """
    scenarios = {
        'normal': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'response_delay': 0.0
        },
        'slow': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'response_delay': 0.5
        },
        'unauthenticated': {
            'api_key': '',
            'api_secret': '',
            'response_delay': 0.0
        }
    }
    
    config = scenarios.get(scenario, scenarios['normal'])
    return MockAsyncClient(**config)