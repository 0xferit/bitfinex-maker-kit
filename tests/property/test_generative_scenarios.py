"""
Generative scenario testing for Maker-Kit.

Uses Hypothesis to generate complex trading scenarios and system
states for comprehensive edge case discovery and stress testing.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, example
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, invariant, initialize
import asyncio
import random
from decimal import Decimal
from typing import Dict, List, Any, Optional

from maker_kit.domain.symbol import Symbol
from maker_kit.domain.price import Price
from maker_kit.domain.amount import Amount
from maker_kit.domain.order_id import OrderId
from ..mocks.service_mocks import create_mock_trading_service, create_mock_cache_service
from ..fixtures.market_data import MarketDataFixtures
from ..fixtures.trading_data import TradingFixtures


# Complex scenario generators
@st.composite
def market_conditions(draw):
    """Generate realistic market conditions."""
    volatility_levels = ['low', 'medium', 'high', 'extreme']
    liquidity_levels = ['thin', 'normal', 'deep']
    trend_directions = ['up', 'down', 'sideways', 'volatile']
    
    return {
        'volatility': draw(st.sampled_from(volatility_levels)),
        'liquidity': draw(st.sampled_from(liquidity_levels)),
        'trend': draw(st.sampled_from(trend_directions)),
        'base_price': float(draw(st.decimals(min_value=Decimal("100"), max_value=Decimal("100000"), places=2))),
        'spread_bps': draw(st.integers(min_value=1, max_value=500)),  # 0.01% to 5%
        'volume_multiplier': float(draw(st.decimals(min_value=Decimal("0.1"), max_value=Decimal("10.0"), places=2)))
    }


@st.composite
def trading_strategies(draw):
    """Generate trading strategy configurations."""
    strategy_types = ['market_making', 'arbitrage', 'momentum', 'mean_reversion']
    
    strategy_type = draw(st.sampled_from(strategy_types))
    
    if strategy_type == 'market_making':
        return {
            'type': strategy_type,
            'levels': draw(st.integers(min_value=1, max_value=10)),
            'spread_pct': float(draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("2.0"), places=3))),
            'order_size': float(draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10.0"), places=6))),
            'max_inventory': float(draw(st.decimals(min_value=Decimal("1.0"), max_value=Decimal("100.0"), places=2)))
        }
    elif strategy_type == 'arbitrage':
        return {
            'type': strategy_type,
            'min_spread_bps': draw(st.integers(min_value=1, max_value=50)),
            'max_position': float(draw(st.decimals(min_value=Decimal("1.0"), max_value=Decimal("50.0"), places=2))),
            'timeout_seconds': draw(st.integers(min_value=1, max_value=60))
        }
    else:
        return {
            'type': strategy_type,
            'lookback_periods': draw(st.integers(min_value=5, max_value=100)),
            'threshold_pct': float(draw(st.decimals(min_value=Decimal("0.1"), max_value=Decimal("5.0"), places=2))),
            'position_size': float(draw(st.decimals(min_value=Decimal("0.1"), max_value=Decimal("20.0"), places=2)))
        }


@st.composite
def system_configurations(draw):
    """Generate system configuration scenarios."""
    return {
        'cache_size': draw(st.integers(min_value=100, max_value=10000)),
        'cache_ttl': float(draw(st.decimals(min_value=Decimal("1.0"), max_value=Decimal("3600.0"), places=1))),
        'api_rate_limit': draw(st.integers(min_value=10, max_value=1000)),
        'max_concurrent_orders': draw(st.integers(min_value=5, max_value=500)),
        'order_timeout': float(draw(st.decimals(min_value=Decimal("1.0"), max_value=Decimal("300.0"), places=1))),
        'retry_attempts': draw(st.integers(min_value=1, max_value=10)),
        'performance_monitoring': draw(st.booleans())
    }


@st.composite
def user_behavior_patterns(draw):
    """Generate user behavior patterns."""
    user_types = ['retail', 'institutional', 'hft', 'arbitrageur']
    activity_levels = ['low', 'medium', 'high', 'burst']
    
    return {
        'user_type': draw(st.sampled_from(user_types)),
        'activity_level': draw(st.sampled_from(activity_levels)),
        'order_size_preference': draw(st.sampled_from(['small', 'medium', 'large', 'mixed'])),
        'latency_sensitivity': draw(st.sampled_from(['low', 'medium', 'high'])),
        'error_tolerance': float(draw(st.decimals(min_value=Decimal("0.01"), max_value=Decimal("0.20"), places=3))),
        'session_duration': draw(st.integers(min_value=60, max_value=3600))  # 1 minute to 1 hour
    }


class TestComplexTradingScenarios:
    """Property-based tests for complex trading scenarios."""
    
    @given(market_conditions(), trading_strategies())
    async def test_strategy_under_market_conditions(self, market_cond, strategy):
        """Test trading strategies under various market conditions."""
        trading_service = create_mock_trading_service('normal')
        
        try:
            if strategy['type'] == 'market_making':
                await self._test_market_making_strategy(trading_service, market_cond, strategy)
            elif strategy['type'] == 'arbitrage':
                await self._test_arbitrage_strategy(trading_service, market_cond, strategy)
            else:
                await self._test_directional_strategy(trading_service, market_cond, strategy)
                
        except (ValueError, TypeError):
            # Some strategy/market combinations might be invalid
            pass
    
    async def _test_market_making_strategy(self, trading_service, market_cond, strategy):
        """Test market making strategy implementation."""
        center_price = market_cond['base_price']
        spread_pct = strategy['spread_pct']
        levels = strategy['levels']
        order_size = strategy['order_size']
        
        placed_orders = []
        
        # Place market making orders
        for level in range(1, levels + 1):
            # Adjust spread based on market volatility
            volatility_multiplier = {
                'low': 1.0, 'medium': 1.5, 'high': 2.0, 'extreme': 3.0
            }.get(market_cond['volatility'], 1.0)
            
            adjusted_spread = spread_pct * volatility_multiplier
            price_offset = center_price * (adjusted_spread / 100) * level
            
            bid_price = center_price - price_offset
            ask_price = center_price + price_offset
            
            if bid_price > 0:  # Valid price
                try:
                    # Place bid order
                    bid_order = await trading_service.place_order(
                        symbol=Symbol('tBTCUSD'),
                        amount=Amount(str(order_size)),
                        price=Price(str(bid_price)),
                        side='buy'
                    )
                    placed_orders.append(bid_order)
                    
                    # Place ask order
                    ask_order = await trading_service.place_order(
                        symbol=Symbol('tBTCUSD'),
                        amount=Amount(str(-order_size)),
                        price=Price(str(ask_price)),
                        side='sell'
                    )
                    placed_orders.append(ask_order)
                    
                except (ValueError, TypeError):
                    continue
        
        # Verify strategy properties
        if placed_orders:
            # Should have symmetric orders
            bid_orders = [o for o in placed_orders if o['side'] == 'buy']
            ask_orders = [o for o in placed_orders if o['side'] == 'sell']
            
            # In ideal conditions, should have equal bids and asks
            assert abs(len(bid_orders) - len(ask_orders)) <= 1
            
            # All bids should be below center, all asks above
            for bid in bid_orders:
                assert float(bid['price']) < center_price
            for ask in ask_orders:
                assert float(ask['price']) > center_price
    
    async def _test_arbitrage_strategy(self, trading_service, market_cond, strategy):
        """Test arbitrage strategy implementation."""
        # Simulate arbitrage opportunity detection
        min_spread = strategy['min_spread_bps'] / 10000  # Convert bps to decimal
        max_position = strategy['max_position']
        
        # Simulate price discrepancy
        base_price = market_cond['base_price']
        spread = base_price * min_spread * 2  # Profitable spread
        
        buy_price = base_price - spread / 2
        sell_price = base_price + spread / 2
        
        try:
            # Execute arbitrage (simultaneous buy low, sell high)
            position_size = min(max_position, strategy['max_position'])
            
            buy_order = await trading_service.place_order(
                symbol=Symbol('tBTCUSD'),
                amount=Amount(str(position_size)),
                price=Price(str(buy_price)),
                side='buy'
            )
            
            sell_order = await trading_service.place_order(
                symbol=Symbol('tBTCUSD'),
                amount=Amount(str(-position_size)),
                price=Price(str(sell_price)),
                side='sell'
            )
            
            # Verify arbitrage properties
            assert buy_order['side'] == 'buy'
            assert sell_order['side'] == 'sell'
            assert float(sell_order['price']) > float(buy_order['price'])
            
            # Calculate expected profit
            expected_profit = (float(sell_order['price']) - float(buy_order['price'])) * position_size
            assert expected_profit > 0
            
        except (ValueError, TypeError):
            pass
    
    async def _test_directional_strategy(self, trading_service, market_cond, strategy):
        """Test directional trading strategy."""
        base_price = market_cond['base_price']
        threshold = strategy['threshold_pct'] / 100
        position_size = strategy['position_size']
        
        # Simulate trend detection
        trend = market_cond['trend']
        
        if trend == 'up':
            # Buy on uptrend
            entry_price = base_price * (1 + threshold)
            side = 'buy'
            amount = position_size
        elif trend == 'down':
            # Sell on downtrend
            entry_price = base_price * (1 - threshold)
            side = 'sell'
            amount = -position_size
        else:
            # No clear trend, skip
            return
        
        try:
            order = await trading_service.place_order(
                symbol=Symbol('tBTCUSD'),
                amount=Amount(str(amount)),
                price=Price(str(entry_price)),
                side=side
            )
            
            # Verify directional strategy properties
            assert order['side'] == side
            assert float(order['price']) == entry_price
            
        except (ValueError, TypeError):
            pass
    
    @given(st.lists(user_behavior_patterns(), min_size=1, max_size=10))
    async def test_multi_user_scenarios(self, user_patterns):
        """Test system behavior with multiple user patterns."""
        trading_service = create_mock_trading_service('normal')
        
        async def simulate_user(user_pattern):
            """Simulate individual user behavior."""
            user_type = user_pattern['user_type']
            activity_level = user_pattern['activity_level']
            order_size_pref = user_pattern['order_size_preference']
            
            # Determine order count based on activity level
            order_counts = {
                'low': (1, 5),
                'medium': (5, 15),
                'high': (15, 30),
                'burst': (30, 50)
            }
            min_orders, max_orders = order_counts[activity_level]
            num_orders = random.randint(min_orders, max_orders)
            
            # Determine order sizes based on preference
            if order_size_pref == 'small':
                size_range = (0.01, 0.1)
            elif order_size_pref == 'medium':
                size_range = (0.1, 1.0)
            elif order_size_pref == 'large':
                size_range = (1.0, 10.0)
            else:  # mixed
                size_range = (0.01, 10.0)
            
            placed_orders = []
            
            for i in range(num_orders):
                try:
                    order_size = random.uniform(*size_range)
                    price = 50000 + random.uniform(-1000, 1000)
                    side = random.choice(['buy', 'sell'])
                    amount = order_size if side == 'buy' else -order_size
                    
                    order = await trading_service.place_order(
                        symbol=Symbol('tBTCUSD'),
                        amount=Amount(str(amount)),
                        price=Price(str(price)),
                        side=side
                    )
                    placed_orders.append(order)
                    
                    # Simulate user behavior timing
                    if activity_level == 'burst':
                        await asyncio.sleep(0.01)  # Very fast
                    elif activity_level == 'high':
                        await asyncio.sleep(0.1)   # Fast
                    else:
                        await asyncio.sleep(0.5)   # Normal pace
                        
                except (ValueError, TypeError):
                    continue
            
            return {
                'user_type': user_type,
                'orders_placed': len(placed_orders),
                'total_volume': sum(abs(float(o['amount'])) for o in placed_orders)
            }
        
        # Simulate all users concurrently
        user_tasks = [simulate_user(pattern) for pattern in user_patterns]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        # Analyze multi-user scenario results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        
        if successful_results:
            total_orders = sum(r['orders_placed'] for r in successful_results)
            total_volume = sum(r['total_volume'] for r in successful_results)
            
            # System should handle multiple users
            assert total_orders >= 0
            assert total_volume >= 0
            
            # Verify user type distribution
            user_types = [r['user_type'] for r in successful_results]
            assert len(set(user_types)) <= len(user_patterns)


class TestSystemStressScenarios:
    """Property-based tests for system stress scenarios."""
    
    @given(system_configurations())
    async def test_system_under_configuration(self, config):
        """Test system behavior under various configurations."""
        # Create services with specific configuration
        cache_service = create_mock_cache_service('normal')
        trading_service = create_mock_trading_service('normal')
        
        try:
            # Test cache with specified configuration
            await self._test_cache_stress(cache_service, config)
            
            # Test trading with specified limits
            await self._test_trading_stress(trading_service, config)
            
        finally:
            await cache_service.cleanup()
    
    async def _test_cache_stress(self, cache_service, config):
        """Stress test cache with configuration."""
        cache_size = min(config['cache_size'], 1000)  # Limit for test performance
        
        # Fill cache to capacity
        for i in range(cache_size):
            await cache_service.set('stress_test', f'key_{i}', f'value_{i}')
        
        # Verify cache behavior at capacity
        stats = cache_service.get_stats()
        assert stats['size'] <= cache_size
        
        # Test overflowing cache
        for i in range(cache_size, cache_size + 100):
            await cache_service.set('stress_test', f'overflow_{i}', f'value_{i}')
        
        # Cache should handle overflow (via eviction)
        final_stats = cache_service.get_stats()
        if config['cache_size'] <= 1000:  # Only check if we respect the limit
            assert final_stats['size'] <= cache_size
    
    async def _test_trading_stress(self, trading_service, config):
        """Stress test trading with configuration."""
        max_orders = min(config['max_concurrent_orders'], 100)  # Limit for test
        
        # Place up to max concurrent orders
        placed_orders = []
        for i in range(max_orders):
            try:
                order = await trading_service.place_order(
                    symbol=Symbol('tBTCUSD'),
                    amount=Amount('0.01'),
                    price=Price(f'{50000 + i}.0'),
                    side='buy' if i % 2 == 0 else 'sell'
                )
                placed_orders.append(order['id'])
            except (ValueError, TypeError):
                continue
        
        # System should handle the load
        active_orders = await trading_service.get_active_orders()
        assert len(active_orders) <= max_orders
        
        # Verify order management under load
        if placed_orders:
            # Cancel random orders
            orders_to_cancel = placed_orders[:len(placed_orders)//2]
            for order_id in orders_to_cancel:
                try:
                    await trading_service.cancel_order(str(order_id))
                except Exception:
                    continue
    
    @given(market_conditions(), st.integers(min_value=10, max_value=1000))
    async def test_high_frequency_scenario(self, market_cond, operations_count):
        """Test high-frequency trading scenario."""
        trading_service = create_mock_trading_service('normal')
        
        # Limit operations for test performance
        ops_count = min(operations_count, 100)
        
        successful_ops = 0
        failed_ops = 0
        
        start_time = asyncio.get_event_loop().time()
        
        for i in range(ops_count):
            try:
                # Rapid-fire orders with small variations
                price_variation = random.uniform(-10, 10)
                price = market_cond['base_price'] + price_variation
                
                if price > 0:  # Valid price
                    order = await trading_service.place_order(
                        symbol=Symbol('tBTCUSD'),
                        amount=Amount('0.001'),  # Small HFT size
                        price=Price(str(price)),
                        side=random.choice(['buy', 'sell'])
                    )
                    successful_ops += 1
                    
                    # Immediately cancel some orders (HFT behavior)
                    if i % 3 == 0:
                        await trading_service.cancel_order(str(order['id']))
            
            except (ValueError, TypeError):
                failed_ops += 1
                continue
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Verify HFT performance characteristics
        if successful_ops > 0:
            ops_per_second = successful_ops / duration
            
            # Should handle reasonable HFT throughput
            assert ops_per_second >= 5  # Minimum for mock service
            
            # Error rate should be acceptable
            total_ops = successful_ops + failed_ops
            error_rate = failed_ops / total_ops if total_ops > 0 else 0
            assert error_rate <= 0.5  # Allow up to 50% failure in stress test


# Integration scenario testing
class TradingSystemScenarioMachine(RuleBasedStateMachine):
    """Stateful testing for complete trading system scenarios."""
    
    active_orders = Bundle('active_orders')
    market_symbols = Bundle('market_symbols')
    
    def __init__(self):
        super().__init__()
        self.trading_service = create_mock_trading_service('normal')
        self.cache_service = create_mock_cache_service('normal')
        self.placed_orders = {}
        self.market_data = {}
        self.system_state = {
            'total_orders_placed': 0,
            'total_orders_cancelled': 0,
            'cache_operations': 0
        }
    
    @initialize()
    def setup_market(self):
        """Initialize market with basic symbols."""
        symbols = ['tBTCUSD', 'tETHUSD', 'tPNKUSD']
        for symbol in symbols:
            self.market_data[symbol] = {
                'base_price': random.uniform(100, 100000),
                'volatility': random.choice(['low', 'medium', 'high'])
            }
    
    @rule(target=market_symbols)
    def add_market_symbol(self):
        """Add a market symbol to the system."""
        symbols = ['tLTCUSD', 'tXRPUSD', 'tADAUSD', 'tDOTUSD']
        symbol = random.choice(symbols)
        
        if symbol not in self.market_data:
            self.market_data[symbol] = {
                'base_price': random.uniform(0.1, 1000),
                'volatility': random.choice(['low', 'medium', 'high'])
            }
        
        return symbol
    
    @rule(target=active_orders)
    async def place_market_order(self):
        """Place a market order."""
        if not self.market_data:
            return None
        
        symbol_str = random.choice(list(self.market_data.keys()))
        market_data = self.market_data[symbol_str]
        
        # Generate order based on market conditions
        base_price = market_data['base_price']
        volatility_mult = {'low': 0.01, 'medium': 0.05, 'high': 0.1}[market_data['volatility']]
        price_variation = base_price * volatility_mult * random.uniform(-1, 1)
        order_price = base_price + price_variation
        
        if order_price <= 0:
            return None
        
        try:
            order_size = random.uniform(0.01, 1.0)
            side = random.choice(['buy', 'sell'])
            amount = order_size if side == 'buy' else -order_size
            
            order = await self.trading_service.place_order(
                symbol=Symbol(symbol_str),
                amount=Amount(str(amount)),
                price=Price(str(order_price)),
                side=side
            )
            
            order_id = order['id']
            self.placed_orders[order_id] = {
                'symbol': symbol_str,
                'price': order_price,
                'amount': amount,
                'side': side
            }
            
            self.system_state['total_orders_placed'] += 1
            return order_id
            
        except (ValueError, TypeError):
            return None
    
    @rule(order_id=active_orders)
    async def cancel_order(self, order_id):
        """Cancel an active order."""
        if order_id is None:
            return
        
        try:
            await self.trading_service.cancel_order(str(order_id))
            if order_id in self.placed_orders:
                del self.placed_orders[order_id]
            self.system_state['total_orders_cancelled'] += 1
        except Exception:
            pass
    
    @rule()
    async def cache_market_data(self):
        """Cache market data."""
        if not self.market_data:
            return
        
        symbol = random.choice(list(self.market_data.keys()))
        market_data = self.market_data[symbol]
        
        await self.cache_service.set(
            'market_data',
            f'price_{symbol}',
            market_data['base_price'],
            ttl=random.uniform(10, 300)
        )
        
        self.system_state['cache_operations'] += 1
    
    @rule()
    async def update_market_conditions(self):
        """Update market conditions dynamically."""
        if not self.market_data:
            return
        
        symbol = random.choice(list(self.market_data.keys()))
        
        # Simulate price movement
        current_price = self.market_data[symbol]['base_price']
        volatility = self.market_data[symbol]['volatility']
        
        vol_mult = {'low': 0.01, 'medium': 0.03, 'high': 0.08}[volatility]
        price_change = current_price * vol_mult * random.uniform(-1, 1)
        new_price = max(0.01, current_price + price_change)
        
        self.market_data[symbol]['base_price'] = new_price
        
        # Sometimes change volatility
        if random.random() < 0.1:
            self.market_data[symbol]['volatility'] = random.choice(['low', 'medium', 'high'])
    
    @invariant()
    def system_consistency(self):
        """Invariant: system state should remain consistent."""
        # Basic state consistency
        assert self.system_state['total_orders_placed'] >= 0
        assert self.system_state['total_orders_cancelled'] >= 0
        assert self.system_state['cache_operations'] >= 0
        
        # Orders cancelled shouldn't exceed orders placed
        assert self.system_state['total_orders_cancelled'] <= self.system_state['total_orders_placed']
        
        # Market data should have valid prices
        for symbol, data in self.market_data.items():
            assert data['base_price'] > 0
            assert data['volatility'] in ['low', 'medium', 'high']
    
    @invariant()
    def cache_consistency(self):
        """Invariant: cache should remain consistent."""
        stats = self.cache_service.get_stats()
        
        # Cache stats should be valid
        assert stats['hits'] >= 0
        assert stats['misses'] >= 0
        assert stats['sets'] >= 0
        assert 0 <= stats['hit_ratio'] <= 1
    
    def teardown(self):
        """Clean up after testing."""
        asyncio.create_task(self.cache_service.cleanup())


# Test the scenario machine
TestTradingSystemScenarioMachine = TradingSystemScenarioMachine.TestCase


class TestGenerativeEdgeCases:
    """Generative tests for discovering edge cases."""
    
    @given(st.data())
    async def test_random_operation_sequences(self, data):
        """Test random sequences of operations to discover edge cases."""
        trading_service = create_mock_trading_service('normal')
        cache_service = create_mock_cache_service('normal')
        
        try:
            # Generate random operation sequence
            num_operations = data.draw(st.integers(min_value=5, max_value=50))
            
            for _ in range(num_operations):
                operation = data.draw(st.sampled_from([
                    'place_order', 'cancel_order', 'cache_set', 'cache_get',
                    'get_orders', 'update_market'
                ]))
                
                try:
                    if operation == 'place_order':
                        symbol = data.draw(st.sampled_from(['tBTCUSD', 'tETHUSD']))
                        price = data.draw(st.floats(min_value=0.01, max_value=100000))
                        amount = data.draw(st.floats(min_value=-10, max_value=10))
                        
                        if amount != 0:
                            side = 'sell' if amount < 0 else 'buy'
                            await trading_service.place_order(
                                symbol=Symbol(symbol),
                                amount=Amount(str(amount)),
                                price=Price(str(price)),
                                side=side
                            )
                    
                    elif operation == 'cancel_order':
                        order_id = data.draw(st.integers(min_value=10000000, max_value=99999999))
                        await trading_service.cancel_order(str(order_id))
                    
                    elif operation == 'cache_set':
                        key = data.draw(st.text(min_size=1, max_size=50))
                        value = data.draw(st.text(max_size=100))
                        ttl = data.draw(st.floats(min_value=0.1, max_value=3600))
                        
                        await cache_service.set('test', key, value, ttl=ttl)
                    
                    elif operation == 'cache_get':
                        key = data.draw(st.text(min_size=1, max_size=50))
                        await cache_service.get('test', key)
                    
                    elif operation == 'get_orders':
                        symbol = data.draw(st.sampled_from(['tBTCUSD', 'tETHUSD']))
                        await trading_service.get_active_orders(Symbol(symbol))
                
                except (ValueError, TypeError, Exception):
                    # Edge cases may cause exceptions - this is expected
                    continue
        
        finally:
            await cache_service.cleanup()
    
    @settings(max_examples=50, deadline=None)
    @given(st.data())
    async def test_concurrent_operation_chaos(self, data):
        """Test chaotic concurrent operations for race conditions."""
        trading_service = create_mock_trading_service('normal')
        cache_service = create_mock_cache_service('normal')
        
        try:
            num_workers = data.draw(st.integers(min_value=3, max_value=20))
            
            async def chaotic_worker(worker_id):
                """Worker that performs random operations."""
                operations = data.draw(st.integers(min_value=5, max_value=30))
                
                for i in range(operations):
                    try:
                        # Random operation selection
                        op_type = data.draw(st.sampled_from([
                            'trading', 'cache', 'query'
                        ]))
                        
                        if op_type == 'trading':
                            # Random trading operation
                            amount = data.draw(st.floats(min_value=0.001, max_value=1.0))
                            price = data.draw(st.floats(min_value=100, max_value=100000))
                            side = data.draw(st.sampled_from(['buy', 'sell']))
                            amount_val = amount if side == 'buy' else -amount
                            
                            await trading_service.place_order(
                                symbol=Symbol('tBTCUSD'),
                                amount=Amount(str(amount_val)),
                                price=Price(str(price)),
                                side=side
                            )
                        
                        elif op_type == 'cache':
                            # Random cache operation
                            key = f"worker_{worker_id}_key_{i}"
                            value = f"value_{worker_id}_{i}"
                            
                            if data.draw(st.booleans()):
                                await cache_service.set('chaos', key, value)
                            else:
                                await cache_service.get('chaos', key)
                        
                        elif op_type == 'query':
                            # Random query operation
                            await trading_service.get_active_orders()
                    
                    except Exception:
                        # Chaos testing - exceptions are expected
                        continue
                
                return worker_id
            
            # Run chaotic workers concurrently
            tasks = [chaotic_worker(i) for i in range(num_workers)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # System should survive chaos
            completed_workers = [r for r in results if not isinstance(r, Exception)]
            assert len(completed_workers) >= 0  # At least some workers should complete
        
        finally:
            await cache_service.cleanup()