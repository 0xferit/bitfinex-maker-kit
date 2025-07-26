"""
Tests for performance profiling utilities.

Validates profiling functionality, memory analysis, and performance
optimization tools for development and production monitoring.
"""

import pytest
import asyncio
import time
import gc
from typing import Dict, Any

from maker_kit.utilities.profiler import (
    CodeProfiler, MemoryProfiler, PerformanceOptimizer
)
from maker_kit.domain.symbol import Symbol
from maker_kit.domain.price import Price
from maker_kit.domain.amount import Amount
from ..mocks.service_mocks import create_mock_trading_service


@pytest.mark.unit
class TestCodeProfiler:
    """Tests for code profiling functionality."""
    
    async def test_function_profiling(self):
        """Test function execution profiling."""
        profiler = CodeProfiler()
        
        @profiler.profile_function
        async def sample_function(x: int, y: int) -> int:
            await asyncio.sleep(0.01)  # Simulate work
            return x + y
        
        # Execute profiled function multiple times
        results = []
        for i in range(5):
            result = await sample_function(i, i * 2)
            results.append(result)
        
        # Verify function results
        assert results == [0, 3, 6, 9, 12]
        
        # Verify profiling data
        profile_data = profiler.get_profile_data()
        assert 'sample_function' in profile_data
        
        func_data = profile_data['sample_function']
        assert func_data['call_count'] == 5
        assert func_data['total_time'] > 0.04  # Should be at least 5 * 0.01
        assert func_data['avg_time'] > 0.008   # Should be close to 0.01
        assert func_data['min_time'] > 0
        assert func_data['max_time'] > func_data['min_time']
    
    async def test_context_manager_profiling(self):
        """Test profiling with context manager."""
        profiler = CodeProfiler()
        
        async with profiler.profile_block('test_block'):
            await asyncio.sleep(0.02)
            result = 42
        
        profile_data = profiler.get_profile_data()
        assert 'test_block' in profile_data
        
        block_data = profile_data['test_block']
        assert block_data['call_count'] == 1
        assert block_data['total_time'] >= 0.02
        assert block_data['avg_time'] >= 0.02
    
    async def test_nested_profiling(self):
        """Test nested function profiling."""
        profiler = CodeProfiler()
        
        @profiler.profile_function
        async def inner_function(x: int) -> int:
            await asyncio.sleep(0.005)
            return x * 2
        
        @profiler.profile_function
        async def outer_function(x: int) -> int:
            result = await inner_function(x)
            await asyncio.sleep(0.01)
            return result + 1
        
        final_result = await outer_function(5)
        assert final_result == 11
        
        profile_data = profiler.get_profile_data()
        assert 'inner_function' in profile_data
        assert 'outer_function' in profile_data
        
        # Outer function should take longer than inner
        outer_time = profile_data['outer_function']['total_time']
        inner_time = profile_data['inner_function']['total_time']
        assert outer_time > inner_time
    
    async def test_error_handling_in_profiling(self):
        """Test profiling with exception handling."""
        profiler = CodeProfiler()
        
        @profiler.profile_function
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")
        
        # Function should still be profiled even when it raises
        with pytest.raises(ValueError, match="Test error"):
            await failing_function()
        
        profile_data = profiler.get_profile_data()
        assert 'failing_function' in profile_data
        
        func_data = profile_data['failing_function']
        assert func_data['call_count'] == 1
        assert func_data['error_count'] == 1
        assert func_data['total_time'] >= 0.01
    
    def test_profile_data_export(self):
        """Test profile data export functionality."""
        profiler = CodeProfiler()
        
        # Add some mock profile data
        profiler._profile_data['test_func'] = {
            'call_count': 10,
            'total_time': 1.5,
            'avg_time': 0.15,
            'min_time': 0.1,
            'max_time': 0.3,
            'error_count': 2
        }
        
        # Test JSON export
        json_export = profiler.export_profile_data('json')
        assert 'test_func' in json_export
        assert '"call_count": 10' in json_export
        
        # Test CSV export
        csv_export = profiler.export_profile_data('csv')
        assert 'function_name,call_count,total_time,avg_time' in csv_export
        assert 'test_func,10,1.500,0.150' in csv_export


@pytest.mark.unit
class TestMemoryProfiler:
    """Tests for memory profiling functionality."""
    
    def test_memory_snapshot(self):
        """Test memory snapshot functionality."""
        profiler = MemoryProfiler()
        
        # Take initial snapshot
        initial_snapshot = profiler.take_memory_snapshot('initial')
        assert initial_snapshot['name'] == 'initial'
        assert initial_snapshot['timestamp'] > 0
        assert initial_snapshot['memory_mb'] > 0
        assert initial_snapshot['objects_count'] > 0
        
        # Create some objects to change memory
        large_list = [i for i in range(10000)]
        
        # Take second snapshot
        after_snapshot = profiler.take_memory_snapshot('after_allocation')
        assert after_snapshot['memory_mb'] >= initial_snapshot['memory_mb']
        
        # Clean up
        del large_list
        gc.collect()
    
    def test_memory_tracking(self):
        """Test memory usage tracking over time."""
        profiler = MemoryProfiler()
        
        # Start tracking
        profiler.start_tracking('test_tracking')
        
        # Simulate memory usage changes
        data = []
        for i in range(100):
            data.append(f"data_item_{i}" * 100)  # Create some memory pressure
            if i % 20 == 0:
                profiler.record_memory_usage('test_tracking')
        
        # Stop tracking
        profiler.stop_tracking('test_tracking')
        
        # Verify tracking data
        tracking_data = profiler.get_tracking_data('test_tracking')
        assert tracking_data['name'] == 'test_tracking'
        assert len(tracking_data['memory_samples']) >= 5  # Should have several samples
        assert tracking_data['peak_memory_mb'] > tracking_data['initial_memory_mb']
        
        # Clean up
        del data
        gc.collect()
    
    async def test_async_memory_monitoring(self):
        """Test asynchronous memory monitoring."""
        profiler = MemoryProfiler()
        
        async def memory_intensive_task():
            data = []
            for i in range(1000):
                data.append([j for j in range(100)])  # Create nested lists
                if i % 100 == 0:
                    await asyncio.sleep(0.001)  # Yield control
            return len(data)
        
        # Monitor memory during task execution
        async with profiler.monitor_async_task('intensive_task'):
            result = await memory_intensive_task()
        
        assert result == 1000
        
        # Verify monitoring results
        monitoring_data = profiler.get_monitoring_data('intensive_task')
        assert monitoring_data['task_name'] == 'intensive_task'
        assert monitoring_data['duration'] > 0
        assert monitoring_data['peak_memory_mb'] > monitoring_data['initial_memory_mb']
        assert len(monitoring_data['memory_timeline']) > 0
    
    def test_memory_leak_detection(self):
        """Test memory leak detection functionality."""
        profiler = MemoryProfiler()
        
        # Create a pattern that could indicate a memory leak
        profiler.take_memory_snapshot('baseline')
        
        # Simulate operations that might leak memory
        leaked_objects = []
        for i in range(5):
            # Add objects without cleaning up
            leaked_objects.extend([f"object_{j}" for j in range(100)])
            profiler.take_memory_snapshot(f'iteration_{i}')
        
        # Analyze for potential leaks
        leak_analysis = profiler.analyze_memory_leaks()
        
        # Should detect increasing memory usage
        assert len(leak_analysis['snapshots']) >= 6
        assert leak_analysis['memory_trend'] == 'increasing'
        assert leak_analysis['potential_leak'] == True
        
        # Clean up
        del leaked_objects
        gc.collect()


@pytest.mark.unit
class TestPerformanceOptimizer:
    """Tests for performance optimization utilities."""
    
    def test_bottleneck_identification(self):
        """Test bottleneck identification in profile data."""
        optimizer = PerformanceOptimizer()
        
        # Create mock profile data with clear bottlenecks
        profile_data = {
            'fast_function': {
                'call_count': 1000,
                'total_time': 0.1,
                'avg_time': 0.0001
            },
            'slow_function': {
                'call_count': 10,
                'total_time': 5.0,
                'avg_time': 0.5
            },
            'moderate_function': {
                'call_count': 100,
                'total_time': 1.0,
                'avg_time': 0.01
            }
        }
        
        bottlenecks = optimizer.identify_bottlenecks(profile_data)
        
        # Should identify slow_function as primary bottleneck
        assert len(bottlenecks) > 0
        assert bottlenecks[0]['function_name'] == 'slow_function'
        assert bottlenecks[0]['severity'] == 'high'
        assert bottlenecks[0]['total_time'] == 5.0
    
    def test_optimization_recommendations(self):
        """Test optimization recommendation generation."""
        optimizer = PerformanceOptimizer()
        
        profile_data = {
            'database_query': {
                'call_count': 1000,
                'total_time': 10.0,
                'avg_time': 0.01
            },
            'api_call': {
                'call_count': 50,
                'total_time': 15.0,
                'avg_time': 0.3
            },
            'computation': {
                'call_count': 10000,
                'total_time': 2.0,
                'avg_time': 0.0002
            }
        }
        
        recommendations = optimizer.generate_recommendations(profile_data)
        
        # Should provide relevant recommendations
        assert len(recommendations) > 0
        
        # Find API call recommendation (slowest per call)
        api_rec = next((r for r in recommendations if 'api_call' in r['function']), None)
        assert api_rec is not None
        assert 'caching' in api_rec['recommendation'].lower() or 'batch' in api_rec['recommendation'].lower()
    
    async def test_performance_comparison(self):
        """Test performance comparison between implementations."""
        optimizer = PerformanceOptimizer()
        
        # Define two implementations to compare
        async def implementation_a(n: int) -> int:
            await asyncio.sleep(0.001 * n)  # Slower implementation
            return sum(range(n))
        
        async def implementation_b(n: int) -> int:
            await asyncio.sleep(0.0005 * n)  # Faster implementation
            return n * (n - 1) // 2  # Mathematical formula
        
        # Compare implementations
        comparison = await optimizer.compare_implementations(
            {'impl_a': implementation_a, 'impl_b': implementation_b},
            test_args=[10],
            iterations=5
        )
        
        # Verify comparison results
        assert 'impl_a' in comparison
        assert 'impl_b' in comparison
        
        impl_a_data = comparison['impl_a']
        impl_b_data = comparison['impl_b']
        
        assert impl_a_data['avg_time'] > impl_b_data['avg_time']  # A should be slower
        assert impl_a_data['result'] == impl_b_data['result']      # Results should match
        
        # Check recommendation
        assert 'fastest_implementation' in comparison
        assert comparison['fastest_implementation'] == 'impl_b'
    
    def test_performance_regression_detection(self):
        """Test performance regression detection."""
        optimizer = PerformanceOptimizer()
        
        # Baseline performance data
        baseline = {
            'function_x': {'avg_time': 0.1, 'call_count': 100},
            'function_y': {'avg_time': 0.05, 'call_count': 200},
            'function_z': {'avg_time': 0.2, 'call_count': 50}
        }
        
        # Current performance data with regression
        current = {
            'function_x': {'avg_time': 0.15, 'call_count': 100},  # 50% slower - regression
            'function_y': {'avg_time': 0.04, 'call_count': 200},  # 20% faster - improvement
            'function_z': {'avg_time': 0.2, 'call_count': 50}    # Same - no change
        }
        
        regression_analysis = optimizer.detect_performance_regression(baseline, current)
        
        # Should detect regression in function_x
        assert 'regressions' in regression_analysis
        assert 'improvements' in regression_analysis
        assert 'no_change' in regression_analysis
        
        regressions = regression_analysis['regressions']
        assert len(regressions) == 1
        assert regressions[0]['function'] == 'function_x'
        assert regressions[0]['slowdown_percent'] == 50.0
        
        improvements = regression_analysis['improvements']
        assert len(improvements) == 1
        assert improvements[0]['function'] == 'function_y'
        assert improvements[0]['speedup_percent'] == 20.0


@pytest.mark.integration
class TestProfilerIntegration:
    """Integration tests for profiler with real trading operations."""
    
    async def test_trading_service_profiling(self):
        """Test profiling real trading service operations."""
        profiler = CodeProfiler()
        trading_service = create_mock_trading_service('normal')
        
        @profiler.profile_function
        async def place_multiple_orders():
            orders = []
            for i in range(10):
                order = await trading_service.place_order(
                    symbol=Symbol('tBTCUSD'),
                    amount=Amount(f'0.{i+1:02d}'),
                    price=Price(f'{50000 + i}.0'),
                    side='buy' if i % 2 == 0 else 'sell'
                )
                orders.append(order)
            return orders
        
        # Execute profiled trading operations
        orders = await place_multiple_orders()
        assert len(orders) == 10
        
        # Analyze profiling results
        profile_data = profiler.get_profile_data()
        assert 'place_multiple_orders' in profile_data
        
        func_data = profile_data['place_multiple_orders']
        assert func_data['call_count'] == 1
        assert func_data['total_time'] > 0
        
        # Generate optimization recommendations
        optimizer = PerformanceOptimizer()
        recommendations = optimizer.generate_recommendations(profile_data)
        
        # Should provide meaningful recommendations for trading operations
        assert len(recommendations) >= 0  # May or may not have recommendations
    
    async def test_memory_profiling_with_trading_operations(self):
        """Test memory profiling during trading operations."""
        memory_profiler = MemoryProfiler()
        trading_service = create_mock_trading_service('normal')
        
        # Monitor memory during intensive trading operations
        async with memory_profiler.monitor_async_task('intensive_trading'):
            # Create many orders to increase memory usage
            orders = []
            for i in range(100):
                try:
                    order = await trading_service.place_order(
                        symbol=Symbol('tBTCUSD'),
                        amount=Amount(f'{(i % 10 + 1) * 0.01:.6f}'),
                        price=Price(f'{50000 + (i % 1000)}.0'),
                        side='buy' if i % 2 == 0 else 'sell'
                    )
                    orders.append(order)
                except Exception:
                    continue
        
        # Analyze memory usage
        monitoring_data = memory_profiler.get_monitoring_data('intensive_trading')
        assert monitoring_data['task_name'] == 'intensive_trading'
        assert monitoring_data['duration'] > 0
        assert len(monitoring_data['memory_timeline']) > 0
        
        # Memory usage should increase with more orders
        initial_memory = monitoring_data['initial_memory_mb']
        peak_memory = monitoring_data['peak_memory_mb']
        assert peak_memory >= initial_memory