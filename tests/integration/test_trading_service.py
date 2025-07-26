"""
Integration tests for trading service.

Tests trading service integration with mocked API clients,
cache services, and performance monitoring components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from maker_kit.domain.symbol import Symbol
from maker_kit.domain.price import Price
from maker_kit.domain.amount import Amount
from maker_kit.domain.order_id import OrderId
from maker_kit.services.container import create_service_container
from maker_kit.services.monitored_trading_service import create_monitored_trading_service
from maker_kit.utilities.constants import OrderSubmissionError
from ..mocks.client_mocks import create_mock_client, create_mock_async_client
from ..mocks.service_mocks import create_mock_performance_monitor, create_mock_cache_service
from ..fixtures.trading_data import TradingFixtures


@pytest.mark.integration
class TestTradingServiceIntegration:
    """Integration tests for trading service components."""
    
    @pytest.fixture
    async def trading_service(self, mock_bitfinex_client, test_config):
        """Create trading service for testing."""
        container = create_service_container(test_config)
        
        # Mock the client creation
        with patch.object(container, '_create_bitfinex_client', return_value=mock_bitfinex_client):
            service = container.create_trading_service()
            yield service
            
            # Cleanup
            if hasattr(service, 'cleanup'):
                await service.cleanup()
    
    @pytest.fixture
    async def monitored_trading_service(self, service_container):
        """Create monitored trading service for testing."""
        performance_monitor = create_mock_performance_monitor('baseline')
        
        service = create_monitored_trading_service(
            service_container,
            performance_monitor=performance_monitor
        )
        
        async with service:
            yield service
    
    async def test_place_order_integration(self, trading_service, sample_symbol, 
                                         sample_amount, sample_price):
        """Test order placement integration."""
        # Mock client response
        mock_order = Mock()
        mock_order.id = 12345678
        mock_order.symbol = str(sample_symbol)
        mock_order.amount = str(sample_amount)
        mock_order.price = str(sample_price)
        mock_order.side = 'buy'
        mock_order.status = 'ACTIVE'
        
        trading_service.get_client().submit_order.return_value = mock_order
        
        # Place order
        result = await trading_service.place_order(
            symbol=sample_symbol,
            amount=sample_amount,
            price=sample_price,
            side='buy'
        )
        
        # Verify result
        assert result['id'] == 12345678
        assert result['symbol'] == str(sample_symbol)
        assert result['amount'] == str(sample_amount)
        assert result['price'] == str(sample_price)
        assert result['side'] == 'buy'
        assert result['status'] == 'ACTIVE'
        
        # Verify client was called
        trading_service.get_client().submit_order.assert_called_once()
    
    async def test_cancel_order_integration(self, trading_service, sample_order_id):
        """Test order cancellation integration."""
        # Mock client response
        mock_order = Mock()
        mock_order.id = int(sample_order_id)
        mock_order.status = 'CANCELED'
        
        trading_service.get_client().cancel_order.return_value = mock_order
        
        # Cancel order
        result = await trading_service.cancel_order(str(sample_order_id))
        
        # Verify result
        assert result['id'] == int(sample_order_id)
        assert result['status'] == 'CANCELED'
        
        # Verify client was called
        trading_service.get_client().cancel_order.assert_called_once_with(
            int(sample_order_id), None
        )
    
    async def test_get_active_orders_integration(self, trading_service, sample_symbol):
        """Test getting active orders integration."""
        # Mock client response
        mock_orders = []
        for i in range(3):
            mock_order = Mock()
            mock_order.id = 12345678 + i
            mock_order.symbol = str(sample_symbol)
            mock_order.status = 'ACTIVE'
            mock_orders.append(mock_order)
        
        trading_service.get_client().get_orders.return_value = mock_orders
        
        # Get active orders
        result = await trading_service.get_active_orders(sample_symbol)
        
        # Verify result
        assert len(result) == 3
        for i, order in enumerate(result):
            assert order['id'] == 12345678 + i
            assert order['symbol'] == str(sample_symbol)
            assert order['status'] == 'ACTIVE'
        
        # Verify client was called
        trading_service.get_client().get_orders.assert_called_once()
    
    async def test_batch_order_placement(self, trading_service):
        """Test batch order placement integration."""
        # Setup batch orders
        orders = [
            {
                'symbol': 'tBTCUSD',
                'amount': '0.1',
                'price': '49000.0',
                'side': 'buy',
                'type': 'EXCHANGE LIMIT'
            },
            {
                'symbol': 'tBTCUSD',
                'amount': '0.1',
                'price': '51000.0',
                'side': 'sell',
                'type': 'EXCHANGE LIMIT'
            }
        ]
        
        # Mock client responses
        mock_orders = []
        for i, order_spec in enumerate(orders):
            mock_order = Mock()
            mock_order.id = 12345678 + i
            mock_order.symbol = order_spec['symbol']
            mock_order.amount = order_spec['amount']
            mock_order.price = order_spec['price']
            mock_order.side = order_spec['side']
            mock_order.status = 'ACTIVE'
            mock_orders.append(mock_order)
        
        trading_service.get_client().submit_order.side_effect = mock_orders
        
        # Place batch orders
        results = await trading_service.place_batch_orders(orders)
        
        # Verify results
        assert len(results) == 2
        for i, result in enumerate(results):
            assert result['id'] == 12345678 + i
            assert result['symbol'] == orders[i]['symbol']
            assert result['amount'] == orders[i]['amount']
            assert result['price'] == orders[i]['price']
            assert result['side'] == orders[i]['side']
            assert result['status'] == 'ACTIVE'
        
        # Verify client was called for each order
        assert trading_service.get_client().submit_order.call_count == 2


@pytest.mark.integration
class TestMonitoredTradingServiceIntegration:
    """Integration tests for monitored trading service."""
    
    async def test_performance_tracking_integration(self, monitored_trading_service,
                                                  sample_symbol, sample_amount, sample_price):
        """Test performance tracking integration."""
        # Place order (should be tracked)
        await monitored_trading_service.place_order(
            symbol=sample_symbol,
            amount=sample_amount,
            price=sample_price,
            side='buy'
        )
        
        # Get performance metrics
        metrics = monitored_trading_service.get_performance_metrics()
        
        # Verify tracking
        assert 'api_performance' in metrics
        assert 'trading_activity' in metrics
        
        # Check if operations were recorded
        monitor = monitored_trading_service.performance_monitor
        assert 'trading.place_order_total' in monitor.recorded_counters
        assert monitor.recorded_counters['trading.place_order_total'] > 0
    
    async def test_profiling_integration(self, monitored_trading_service,
                                       sample_symbol, sample_amount, sample_price):
        """Test profiling integration."""
        # Perform multiple operations
        operations = [
            ('place_order', {
                'symbol': sample_symbol,
                'amount': sample_amount,
                'price': sample_price,
                'side': 'buy'
            }),
            ('get_active_orders', {'symbol': sample_symbol}),
            ('get_account_balance', {})
        ]
        
        for operation, kwargs in operations:
            method = getattr(monitored_trading_service, operation)
            await method(**kwargs)
        
        # Get profiling report
        report = monitored_trading_service.get_profiling_report()
        
        # Verify profiling data
        assert 'timestamp' in report
        assert 'summary' in report
        
        # Check if operations were profiled
        profiler = monitored_trading_service.profiler
        assert len(profiler.recorded_timers) > 0
    
    async def test_error_tracking_integration(self, monitored_trading_service):
        """Test error tracking integration."""
        # Simulate API error
        mock_client = monitored_trading_service._trading_service.get_client()
        mock_client.submit_order.side_effect = OrderSubmissionError("API Error")
        
        # Attempt operation that will fail
        with pytest.raises(OrderSubmissionError):
            await monitored_trading_service.place_order(
                symbol=Symbol('tBTCUSD'),
                amount=Amount('0.1'),
                price=Price('50000.0'),
                side='buy'
            )
        
        # Verify error was tracked
        monitor = monitored_trading_service.performance_monitor
        assert 'trading.place_order_total' in monitor.recorded_counters
        
        # Get performance summary
        summary = monitored_trading_service.get_performance_summary()
        assert 'overall_health' in summary


@pytest.mark.integration
class TestServiceContainerIntegration:
    """Integration tests for service container."""
    
    async def test_service_creation_integration(self, test_config):
        """Test service creation through container."""
        container = create_service_container(test_config)
        
        # Create various services
        trading_service = container.create_trading_service()
        cache_service = container.create_cache_service()
        
        # Verify services are created
        assert trading_service is not None
        assert cache_service is not None
        
        # Verify services have expected methods
        assert hasattr(trading_service, 'place_order')
        assert hasattr(trading_service, 'cancel_order')
        assert hasattr(cache_service, 'get')
        assert hasattr(cache_service, 'set')
        
        # Cleanup
        await container.cleanup()
    
    async def test_service_dependency_injection(self, test_config):
        """Test service dependency injection."""
        container = create_service_container(test_config)
        
        # Create services that depend on each other
        cache_service = container.create_cache_service()
        trading_service = container.create_trading_service()
        
        # Services should be properly configured
        assert cache_service is not None
        assert trading_service is not None
        
        # Cleanup
        await container.cleanup()


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for cache integration."""
    
    @pytest.fixture
    async def cache_service(self):
        """Create cache service for testing."""
        cache = create_mock_cache_service('normal')
        yield cache
        await cache.cleanup()
    
    async def test_cache_with_trading_operations(self, cache_service):
        """Test cache integration with trading operations."""
        # Cache some trading data
        await cache_service.set('orders', 'active', [{'id': 123, 'status': 'ACTIVE'}])
        await cache_service.set('balance', 'USD', {'balance': 10000.0, 'available': 9500.0})
        
        # Retrieve cached data
        cached_orders = await cache_service.get('orders', 'active')
        cached_balance = await cache_service.get('balance', 'USD')
        
        # Verify cached data
        assert cached_orders is not None
        assert len(cached_orders) == 1
        assert cached_orders[0]['id'] == 123
        
        assert cached_balance is not None
        assert cached_balance['balance'] == 10000.0
        
        # Verify cache statistics
        stats = cache_service.get_stats()
        assert stats['hits'] >= 2
        assert stats['sets'] >= 2
    
    async def test_cache_expiration(self, cache_service):
        """Test cache expiration behavior."""
        # Set item with short TTL
        await cache_service.set('test', 'key', 'value', ttl=0.1)
        
        # Immediately retrieve (should hit)
        value = await cache_service.get('test', 'key')
        assert value == 'value'
        
        # Wait for expiration
        await asyncio.sleep(0.15)
        
        # Try to retrieve (should miss)
        expired_value = await cache_service.get('test', 'key')
        assert expired_value is None
        
        # Verify statistics
        stats = cache_service.get_stats()
        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
    
    async def test_cache_get_or_set(self, cache_service):
        """Test cache get_or_set functionality."""
        call_count = 0
        
        async def expensive_operation():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        # First call should fetch
        result1 = await cache_service.get_or_set('test', 'expensive', expensive_operation)
        assert result1 == "result_1"
        assert call_count == 1
        
        # Second call should use cache
        result2 = await cache_service.get_or_set('test', 'expensive', expensive_operation)
        assert result2 == "result_1"  # Same result
        assert call_count == 1  # Function not called again
        
        # Verify cache statistics
        stats = cache_service.get_stats()
        assert stats['hits'] >= 1
        assert stats['sets'] >= 1


@pytest.mark.integration 
class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    async def test_api_error_propagation(self, trading_service):
        """Test API error propagation through service layers."""
        # Mock API error
        trading_service.get_client().submit_order.side_effect = Exception("API Error")
        
        # Verify error propagates correctly
        with pytest.raises(Exception) as exc_info:
            await trading_service.place_order(
                symbol=Symbol('tBTCUSD'),
                amount=Amount('0.1'),
                price=Price('50000.0'),
                side='buy'
            )
        
        assert "API Error" in str(exc_info.value)
    
    async def test_validation_error_handling(self, trading_service):
        """Test validation error handling."""
        # Invalid symbol should raise validation error
        with pytest.raises((ValueError, TypeError)):
            await trading_service.place_order(
                symbol=Symbol('INVALID'),  # This should fail in Symbol creation
                amount=Amount('0.1'),
                price=Price('50000.0'),
                side='buy'
            )
    
    async def test_network_error_simulation(self, trading_service):
        """Test network error simulation."""
        # Mock network error
        trading_service.get_client().get_orders.side_effect = ConnectionError("Network error")
        
        # Verify error handling
        with pytest.raises(ConnectionError):
            await trading_service.get_active_orders()


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrencyIntegration:
    """Integration tests for concurrent operations."""
    
    async def test_concurrent_order_placement(self, trading_service):
        """Test concurrent order placement."""
        # Setup multiple orders
        orders = []
        for i in range(5):
            orders.append({
                'symbol': Symbol('tBTCUSD'),
                'amount': Amount('0.1'),
                'price': Price(f'{50000 + i * 100}.0'),
                'side': 'buy'
            })
        
        # Mock client responses
        mock_orders = []
        for i in range(5):
            mock_order = Mock()
            mock_order.id = 12345678 + i
            mock_order.status = 'ACTIVE'
            mock_orders.append(mock_order)
        
        trading_service.get_client().submit_order.side_effect = mock_orders
        
        # Place orders concurrently
        tasks = [
            trading_service.place_order(**order_params)
            for order_params in orders
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all orders were placed
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result['id'] == 12345678 + i
            assert result['status'] == 'ACTIVE'
    
    async def test_concurrent_cache_operations(self, cache_service):
        """Test concurrent cache operations."""
        # Concurrent set operations
        set_tasks = [
            cache_service.set('test', f'key_{i}', f'value_{i}')
            for i in range(10)
        ]
        
        await asyncio.gather(*set_tasks)
        
        # Concurrent get operations
        get_tasks = [
            cache_service.get('test', f'key_{i}')
            for i in range(10)
        ]
        
        results = await asyncio.gather(*get_tasks)
        
        # Verify results
        for i, result in enumerate(results):
            assert result == f'value_{i}'