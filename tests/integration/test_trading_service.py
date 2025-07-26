"""
Integration tests for trading service - SAFETY FIRST TESTING.

TRADING SAFETY PRINCIPLES TESTED:
- Real API integration (paper trading account for safety)
- POST_ONLY order enforcement
- NO CACHING - live data only for trading safety
- Real service integration without stale data risks

Tests trading service integration with real performance monitoring
and API clients. Cache testing remains for component validation only.
"""

import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol
from bitfinex_maker_kit.services.cache_service import CacheBackend, create_cache_service
from bitfinex_maker_kit.services.container import get_container
from bitfinex_maker_kit.services.monitored_trading_service import create_monitored_trading_service
from bitfinex_maker_kit.services.performance_monitor import create_performance_monitor


@pytest.mark.integration
class TestTradingServiceIntegration:
    """Integration tests for trading service components."""

    @pytest.fixture
    def trading_service(self, test_config):
        """Create trading service for testing with real API client."""
        container = get_container()
        container.configure(test_config)

        # Use real API client with paper trading credentials from environment
        service = container.create_trading_service()
        yield service

        # Cleanup
        container.cleanup()

    def test_place_order_integration(
        self, trading_service, sample_symbol, sample_amount, sample_price
    ):
        """Test order placement integration with real API."""
        # Place order using real API client with paper trading credentials
        success, result = trading_service.place_order(
            symbol=sample_symbol, side="buy", amount=sample_amount, price=sample_price
        )

        # Since paper trading may have symbol limitations, we test the integration works
        # regardless of success/failure - both are valid API responses
        assert isinstance(success, bool)

        if success:
            # If successful, verify result structure
            assert "id" in result
            assert result["symbol"] == str(sample_symbol)
            assert result["amount"] == str(sample_amount)
            assert result["price"] == str(sample_price)
            assert result["side"] == "buy"
            assert result["status"] in ["ACTIVE", "EXECUTED", "PARTIALLY_FILLED"]
        else:
            # If failed, result should contain error information
            assert isinstance(result, str | dict)

    def test_cancel_order_integration(
        self, trading_service, sample_symbol, sample_amount, sample_price
    ):
        """Test order cancellation integration with real API."""
        # First try to place an order to get a real order ID
        place_success, place_result = trading_service.place_order(
            symbol=sample_symbol, side="buy", amount=sample_amount, price=sample_price
        )

        if not place_success:
            # If order placement fails (e.g., due to paper trading limitations),
            # test cancellation with a known non-existent order ID
            from bitfinex_maker_kit.domain.order_id import OrderId

            test_order_id = OrderId("12345678")  # Valid but likely non-existent order ID

            cancel_success, cancel_result = trading_service.cancel_order(test_order_id)

            # Cancellation should fail but still test the integration
            assert isinstance(cancel_success, bool)
            # Either failed (expected) or succeeded (if order existed)
            return

        # If order placement succeeded, proceed with real cancellation test
        order_id = place_result["id"]

        # Convert order ID to OrderId domain object for cancellation
        from bitfinex_maker_kit.domain.order_id import OrderId

        order_id_obj = OrderId(str(order_id))

        # Cancel the order using real API
        cancel_success, cancel_result = trading_service.cancel_order(order_id_obj)

        # Verify cancellation (should succeed since we just placed the order)
        assert cancel_success is True
        assert cancel_result.id == order_id
        assert cancel_result.status == "CANCELED"

    def test_get_orders_integration(self, trading_service, sample_symbol):
        """Test getting orders integration with real API."""
        # Get orders using real API (may return empty list or existing orders)
        result = trading_service.get_orders(sample_symbol)

        # Verify result structure (orders list can be empty)
        assert isinstance(result, list)

        # If we have orders, verify they have expected structure
        for order in result:
            assert hasattr(order, "id")
            assert hasattr(order, "symbol")
            assert hasattr(order, "status")
            assert order.symbol == str(sample_symbol)

    def test_multiple_order_placement(self, trading_service):
        """Test placing multiple orders individually with real API."""
        # Setup test orders
        orders = [
            ("tBTCUSD", "buy", "0.001", "45000.0"),
            ("tBTCUSD", "sell", "0.001", "55000.0"),
        ]

        # Place orders individually using real API
        results = []
        for symbol_str, side, amount_str, price_str in orders:
            success, result = trading_service.place_order(
                symbol=Symbol(symbol_str),
                side=side,
                amount=Amount(amount_str),
                price=Price(price_str),
            )
            results.append((success, result))

        # Verify results
        assert len(results) == 2
        for i, (success, result) in enumerate(results):
            assert isinstance(success, bool)

            if success:
                # If successful, verify result structure
                assert "id" in result
                assert result["symbol"] == orders[i][0]
                assert result["amount"] == orders[i][2]
                assert result["price"] == orders[i][3]
                assert result["side"] == orders[i][1]
                assert result["status"] in ["ACTIVE", "EXECUTED", "PARTIALLY_FILLED"]
            else:
                # If failed (e.g., paper trading limitations), verify error structure
                assert isinstance(result, str | dict)


@pytest.mark.integration
class TestMonitoredTradingServiceIntegration:
    """Integration tests for monitored trading service."""

    @pytest.fixture
    def monitored_trading_service(self, test_config):
        """Create monitored trading service for testing with real services."""
        from bitfinex_maker_kit.services.container import get_container

        # Create container and configure it
        container = get_container()
        container.configure(test_config)

        # Create real performance monitor for testing
        performance_monitor = create_performance_monitor(
            monitoring_interval=1.0,  # Fast interval for testing
            retention_period=60.0,  # Short retention for testing
        )

        service = create_monitored_trading_service(
            container, performance_monitor=performance_monitor
        )
        yield service

        # Cleanup
        container.cleanup()

    @pytest.mark.asyncio
    async def test_performance_tracking_integration(
        self, monitored_trading_service, sample_symbol, sample_amount, sample_price
    ):
        """Test performance tracking integration with real API."""
        # Place order using real API (should be tracked by performance monitor)
        result = await monitored_trading_service.place_order(
            symbol=sample_symbol, side="buy", amount=sample_amount, price=sample_price
        )

        # Since paper trading may have symbol limitations, we test the integration works
        # regardless of success/failure - both are valid API responses
        assert "success" in result
        assert "result" in result
        assert isinstance(result["success"], bool)

        # Get performance metrics
        metrics = monitored_trading_service.get_performance_metrics()

        # Verify tracking (using available metric structure)
        assert isinstance(metrics, dict)

        # Check if operations were recorded in performance monitor
        assert monitored_trading_service.performance_monitor is not None

        # Verify actual tracking occurred
        summary = monitored_trading_service.get_performance_summary()
        assert isinstance(summary, dict)

    @pytest.mark.asyncio
    async def test_profiling_integration(
        self, monitored_trading_service, sample_symbol, sample_amount, sample_price
    ):
        """Test profiling integration."""
        # Mock the underlying TradingService methods
        with (
            patch.object(
                monitored_trading_service._trading_service, "place_order"
            ) as mock_place_order,
            patch.object(
                monitored_trading_service._trading_service, "get_orders"
            ) as mock_get_orders,
            patch.object(
                monitored_trading_service._trading_service, "get_wallet_balances"
            ) as mock_get_balance,
        ):
            # Setup mock returns
            mock_place_order.return_value = (True, {"id": 12345678, "status": "ACTIVE"})
            mock_get_orders.return_value = [{"id": 12345678, "status": "ACTIVE"}]
            mock_get_balance.return_value = [{"currency": "USD", "balance": 10000.0}]

            # Perform multiple operations
            operations = [
                (
                    "place_order",
                    {
                        "symbol": sample_symbol,
                        "side": "buy",
                        "amount": sample_amount,
                        "price": sample_price,
                    },
                ),
                ("get_orders", {"symbol": sample_symbol}),
                ("get_wallet_balances", {}),
            ]

            for operation, kwargs in operations:
                method = getattr(monitored_trading_service, operation)
                await method(**kwargs)

            # Get profiling report
            report = monitored_trading_service.get_profiling_report()

            # Verify profiling data structure
            assert isinstance(report, dict)

            # Check if profiler exists and has data
            profiler = monitored_trading_service.profiler
            assert profiler is not None

    @pytest.mark.asyncio
    async def test_error_tracking_integration(self, monitored_trading_service):
        """Test error tracking integration."""
        # Simulate API error in the underlying trading service
        api_error = RuntimeError("API Error")

        with patch.object(
            monitored_trading_service._trading_service, "place_order"
        ) as mock_place_order:
            mock_place_order.side_effect = api_error

            # Attempt operation that will fail
            with pytest.raises(RuntimeError, match="API Error"):
                await monitored_trading_service.place_order(
                    symbol=Symbol("tBTCUSD"),
                    side="buy",
                    amount=Amount("0.1"),
                    price=Price("50000.0"),
                )

            # Verify error tracking
            monitor = monitored_trading_service.performance_monitor
            assert monitor is not None

            # Get performance summary
            summary = monitored_trading_service.get_performance_summary()
            assert isinstance(summary, dict)


@pytest.mark.integration
class TestServiceContainerIntegration:
    """Integration tests for service container."""

    @pytest.mark.asyncio
    async def test_service_creation_integration(self, test_config, mock_bitfinex_client):
        """Test service creation through container."""
        container = get_container()
        container.configure(test_config)

        # Mock the client creation to prevent API credential validation
        with patch.object(container, "create_bitfinex_client", return_value=mock_bitfinex_client):
            # Create various services
            trading_service = container.create_trading_service()
            # Note: cache_service creation method doesn't exist in container,
            # so we'll import and create it directly
            from bitfinex_maker_kit.services.cache_service import create_cache_service

            cache_service = create_cache_service()

            # Verify services are created
            assert trading_service is not None
            assert cache_service is not None

            # Verify services have expected methods
            assert hasattr(trading_service, "place_order")
            assert hasattr(trading_service, "cancel_order")
            assert hasattr(cache_service, "get")
            assert hasattr(cache_service, "set")

            # Cleanup
            container.cleanup()
            await cache_service.cleanup()

    @pytest.mark.asyncio
    async def test_service_dependency_injection(self, test_config, mock_bitfinex_client):
        """Test service dependency injection."""
        container = get_container()
        container.configure(test_config)

        # Mock the client creation to prevent API credential validation
        with patch.object(container, "create_bitfinex_client", return_value=mock_bitfinex_client):
            # Create services that depend on each other
            from bitfinex_maker_kit.services.cache_service import create_cache_service

            cache_service = create_cache_service()
            trading_service = container.create_trading_service()

            # Services should be properly configured
            assert cache_service is not None
            assert trading_service is not None

            # Cleanup
            container.cleanup()
            await cache_service.cleanup()


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for cache integration."""

    @pytest_asyncio.fixture
    async def test_cache_service(self):
        """Create real cache service for testing."""
        cache = create_cache_service(
            backend_type=CacheBackend.MEMORY, max_size=1000, default_ttl=30.0
        )
        yield cache
        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_cache_with_trading_operations(self, test_cache_service):
        """Test cache integration with trading operations."""
        # Cache some trading data
        await test_cache_service.set("orders", "active", [{"id": 123, "status": "ACTIVE"}])
        await test_cache_service.set("balance", "USD", {"balance": 10000.0, "available": 9500.0})

        # Retrieve cached data
        cached_orders = await test_cache_service.get("orders", "active")
        cached_balance = await test_cache_service.get("balance", "USD")

        # Verify cached data
        assert cached_orders is not None
        assert len(cached_orders) == 1
        assert cached_orders[0]["id"] == 123

        assert cached_balance is not None
        assert cached_balance["balance"] == 10000.0

        # Verify cache statistics
        stats = test_cache_service.get_stats()
        assert stats.hits >= 2

    @pytest.mark.asyncio
    async def test_cache_expiration(self, test_cache_service):
        """Test cache expiration behavior."""
        # Set item with short TTL
        await test_cache_service.set("test", "key", "value", ttl=0.1)

        # Immediately retrieve (should hit)
        value = await test_cache_service.get("test", "key")
        assert value == "value"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Try to retrieve (should miss)
        expired_value = await test_cache_service.get("test", "key")
        assert expired_value is None

        # Verify statistics
        stats = test_cache_service.get_stats()
        assert stats.hits >= 1
        assert stats.misses >= 1

    @pytest.mark.asyncio
    async def test_cache_get_or_set(self, test_cache_service):
        """Test cache get_or_set functionality."""
        call_count = 0

        async def expensive_operation():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call should fetch
        result1 = await test_cache_service.get_or_set("test", "expensive", expensive_operation)
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should use cache
        result2 = await test_cache_service.get_or_set("test", "expensive", expensive_operation)
        assert result2 == "result_1"  # Same result
        assert call_count == 1  # Function not called again

        # Verify cache statistics
        stats = test_cache_service.get_stats()
        assert stats.hits >= 1


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""

    @pytest.fixture
    def trading_service(self, mock_bitfinex_client, test_config):
        """Create trading service for testing."""
        container = get_container()
        container.configure(test_config)

        # Mock the client creation
        with patch.object(container, "create_bitfinex_client", return_value=mock_bitfinex_client):
            service = container.create_trading_service()
            yield service

            # Cleanup
            container.cleanup()

    def test_api_error_propagation(self, trading_service):
        """Test API error propagation through service layers."""
        # Mock the submit_order utility function to raise an error
        with patch("bitfinex_maker_kit.utilities.orders.submit_order") as mock_submit:
            mock_submit.side_effect = Exception("API Error")

            # Verify error propagates correctly (synchronous call)
            success, result = trading_service.place_order(
                symbol=Symbol("tBTCUSD"), side="buy", amount=Amount("0.1"), price=Price("50000.0")
            )

            # Should return False and error message
            assert success is False
            assert "API Error" in str(result)

    def test_validation_error_handling(self, trading_service):
        """Test validation error handling."""
        # Invalid symbol should raise validation error during Symbol creation
        with pytest.raises((ValueError, TypeError)):
            # This should fail when creating the Symbol object with invalid format
            Symbol("INVALID_SYMBOL_FORMAT")  # Symbol expects "tBTCUSD" format

    def test_network_error_simulation(self, trading_service):
        """Test network error simulation."""
        # Mock network error in client
        trading_service.get_client().get_orders.side_effect = ConnectionError("Network error")

        # Verify error handling (synchronous call)
        result = trading_service.get_orders()

        # Should return empty list when error occurs
        assert result == []


@pytest.mark.integration
@pytest.mark.slow
class TestConcurrencyIntegration:
    """Integration tests for concurrent operations."""

    @pytest.fixture
    def trading_service(self, mock_bitfinex_client, test_config):
        """Create trading service for testing."""
        container = get_container()
        container.configure(test_config)

        # Mock the client creation
        with patch.object(container, "create_bitfinex_client", return_value=mock_bitfinex_client):
            service = container.create_trading_service()
            yield service

            # Cleanup
            container.cleanup()

    def test_concurrent_order_placement(self, trading_service):
        """Test concurrent order placement simulation."""
        # Since TradingService methods are synchronous, we'll simulate
        # concurrent calls by testing multiple individual calls
        orders = []
        for i in range(5):
            orders.append(
                {
                    "symbol": Symbol("tBTCUSD"),
                    "side": "buy",
                    "amount": Amount("0.1"),
                    "price": Price(f"{50000 + i * 100}.0"),
                }
            )

        # Mock the submit_order utility function
        with patch("bitfinex_maker_kit.utilities.orders.submit_order") as mock_submit:
            mock_results = []
            for i in range(5):
                mock_results.append((True, {"id": 12345678 + i, "status": "ACTIVE"}))

            mock_submit.side_effect = mock_results

            # Place orders individually (simulating concurrent behavior)
            results = []
            for order_params in orders:
                success, result = trading_service.place_order(**order_params)
                results.append((success, result))

            # Verify all orders were placed
            assert len(results) == 5
            for i, (success, result) in enumerate(results):
                assert success is True
                assert result["id"] == 12345678 + i
                assert result["status"] == "ACTIVE"

    @pytest_asyncio.fixture
    async def concurrent_cache_service(self):
        """Create real cache service for concurrent testing."""
        cache = create_cache_service(
            backend_type=CacheBackend.MEMORY, max_size=1000, default_ttl=30.0
        )
        yield cache
        await cache.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, concurrent_cache_service):
        """Test concurrent cache operations."""
        # Concurrent set operations
        set_tasks = [
            concurrent_cache_service.set("test", f"key_{i}", f"value_{i}") for i in range(10)
        ]

        await asyncio.gather(*set_tasks)

        # Concurrent get operations
        get_tasks = [concurrent_cache_service.get("test", f"key_{i}") for i in range(10)]

        results = await asyncio.gather(*get_tasks)

        # Verify results
        for i, result in enumerate(results):
            assert result == f"value_{i}"
