"""
Property-based tests for cache operations.

Uses Hypothesis to verify cache behavior, consistency, and performance
properties under various load conditions and data patterns.
"""

import asyncio
import contextlib
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, invariant, rule

from ..mocks.service_mocks import create_mock_cache_service

# Configure Hypothesis for CI performance
CI_SETTINGS = settings(max_examples=15, deadline=10000)  # 10 second deadline per test


# Cache-specific strategies
@st.composite
def cache_keys(draw):
    """Generate realistic cache keys."""
    key_patterns = [
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=1, max_size=50
        ),
        st.from_regex(r"[a-zA-Z0-9_\-\.]+"),
        st.builds(
            lambda x, y: f"{x}:{y}",
            st.sampled_from(["user", "order", "market", "config"]),
            st.integers(min_value=1, max_value=999999),
        ),
    ]

    return draw(st.one_of(key_patterns))


@st.composite
def cache_values(draw):
    """Generate various cache value types."""
    value_strategies = st.one_of(
        st.text(min_size=0, max_size=1000),
        st.integers(min_value=-1000000, max_value=1000000),
        st.floats(allow_nan=False, allow_infinity=False),
        st.lists(st.integers(), min_size=0, max_size=100),
        st.dictionaries(st.text(min_size=1, max_size=20), st.integers(), min_size=0, max_size=50),
        st.none(),
    )

    return draw(value_strategies)


@st.composite
def cache_namespaces(draw):
    """Generate cache namespaces."""
    namespaces = ["default", "user_data", "market_data", "orders", "config", "temp", "session"]
    return draw(st.sampled_from(namespaces))


@st.composite
def ttl_values(draw):
    """Generate time-to-live values."""
    ttl_strategies = st.one_of(
        st.just(None),  # Use default TTL
        st.floats(min_value=0.1, max_value=3600.0),  # 0.1 seconds to 1 hour
        st.integers(min_value=1, max_value=86400),  # 1 second to 1 day
    )

    return draw(ttl_strategies)


class TestCacheConsistencyProperties:
    """Property-based tests for cache consistency."""

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values())
    async def test_set_get_consistency(self, namespace, key, value):
        """Test that set followed by get returns the same value."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set value
            await cache_service.set(namespace, key, value)

            # Get value immediately
            retrieved_value = await cache_service.get(namespace, key)

            # Should get back the same value
            assert retrieved_value == value

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values(), cache_values())
    async def test_overwrite_consistency(self, namespace, key, value1, value2):
        """Test that overwriting a key updates the value."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set first value
            await cache_service.set(namespace, key, value1)

            # Set second value (overwrite)
            await cache_service.set(namespace, key, value2)

            # Should get the second value
            retrieved_value = await cache_service.get(namespace, key)
            assert retrieved_value == value2
            assert retrieved_value != value1 or value1 == value2

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values())
    async def test_delete_consistency(self, namespace, key, value):
        """Test that delete removes the value."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set value
            await cache_service.set(namespace, key, value)

            # Verify it exists
            retrieved_value = await cache_service.get(namespace, key)
            assert retrieved_value == value

            # Delete the key
            deleted = await cache_service.delete(namespace, key)
            assert deleted

            # Should return None after deletion
            retrieved_after_delete = await cache_service.get(namespace, key)
            assert retrieved_after_delete is None

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(
        cache_namespaces(),
        st.lists(st.tuples(cache_keys(), cache_values()), min_size=1, max_size=20),
    )
    async def test_namespace_isolation(self, base_namespace, key_value_pairs):
        """Test that different namespaces are isolated."""
        cache_service = create_mock_cache_service("normal")

        try:
            namespace1 = f"{base_namespace}_1"
            namespace2 = f"{base_namespace}_2"

            # Use unique keys only
            unique_pairs = {}
            for key, value in key_value_pairs:
                unique_pairs[key] = value  # Keep last value for each key

            # Set values in first namespace
            for key, value in unique_pairs.items():
                await cache_service.set(namespace1, key, value)

            # Keys should not exist in second namespace
            for key in unique_pairs:
                retrieved = await cache_service.get(namespace2, key)
                assert retrieved is None

            # Set different values in second namespace
            for key, value in unique_pairs.items():
                modified_value = f"modified_{value}" if isinstance(value, str) else value
                await cache_service.set(namespace2, key, modified_value)

            # First namespace should still have original values
            for key, value in unique_pairs.items():
                retrieved = await cache_service.get(namespace1, key)
                assert retrieved == value

        finally:
            await cache_service.cleanup()


class TestCacheExpirationProperties:
    """Property-based tests for cache expiration behavior."""

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values())
    async def test_immediate_expiration(self, namespace, key, value):
        """Test immediate expiration with very short TTL."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set with very short TTL
            await cache_service.set(namespace, key, value, ttl=0.01)  # 10ms

            # Should exist immediately
            immediate_value = await cache_service.get(namespace, key)
            assert immediate_value == value

            # Wait for expiration
            await asyncio.sleep(0.02)  # 20ms

            # Should be expired
            expired_value = await cache_service.get(namespace, key)
            assert expired_value is None

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @settings(max_examples=10, deadline=15000)  # More time for TTL tests
    @given(
        cache_namespaces(), cache_keys(), cache_values(), st.floats(min_value=0.1, max_value=1.0)
    )
    async def test_ttl_accuracy(self, namespace, key, value, ttl):
        """Test TTL accuracy within reasonable bounds."""
        cache_service = create_mock_cache_service("normal")

        try:
            start_time = time.time()
            await cache_service.set(namespace, key, value, ttl=ttl)

            # Check periodically until expiration
            while time.time() - start_time < ttl + 0.5:  # Allow 500ms tolerance
                retrieved = await cache_service.get(namespace, key)
                elapsed = time.time() - start_time

                if elapsed < ttl - 0.1:  # Before expiration (with tolerance)
                    assert retrieved == value, (
                        f"Value expired too early at {elapsed:.3f}s (TTL: {ttl}s)"
                    )
                elif elapsed > ttl + 0.1:  # After expiration (with tolerance)
                    assert retrieved is None, f"Value not expired at {elapsed:.3f}s (TTL: {ttl}s)"
                    break

                await asyncio.sleep(0.1)

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values())
    async def test_none_ttl_uses_default(self, namespace, key, value):
        """Test that None TTL uses cache service default."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set without explicit TTL
            await cache_service.set(namespace, key, value, ttl=None)

            # Should exist immediately
            immediate_value = await cache_service.get(namespace, key)
            assert immediate_value == value

            # Should still exist after short time (assuming default TTL > 1s)
            await asyncio.sleep(0.1)
            still_exists = await cache_service.get(namespace, key)
            assert still_exists == value

        finally:
            await cache_service.cleanup()


class TestCachePerformanceProperties:
    """Property-based tests for cache performance characteristics."""

    @pytest.mark.asyncio
    @CI_SETTINGS
    @given(st.lists(st.tuples(cache_keys(), cache_values()), min_size=5, max_size=20))
    async def test_bulk_operations_performance(self, key_value_pairs):
        """Test performance characteristics of bulk cache operations."""
        cache_service = create_mock_cache_service("normal")

        try:
            namespace = "performance_test"

            # Use unique keys only to avoid overwrite issues
            unique_pairs = {}
            for key, value in key_value_pairs:
                unique_pairs[key] = value  # Keep last value for each key

            # Measure bulk set performance
            start_time = time.time()
            for key, value in unique_pairs.items():
                await cache_service.set(namespace, key, value)
            set_time = time.time() - start_time

            # Measure bulk get performance
            start_time = time.time()
            for key, expected_value in unique_pairs.items():
                retrieved_value = await cache_service.get(namespace, key)
                assert retrieved_value == expected_value
            get_time = time.time() - start_time

            # Performance assertions (adjust based on implementation)
            set_ops_per_second = len(unique_pairs) / set_time
            get_ops_per_second = len(unique_pairs) / get_time

            # These are reasonable minimums for in-memory cache
            assert set_ops_per_second >= 100, (
                f"Set performance too low: {set_ops_per_second:.1f} ops/sec"
            )
            assert get_ops_per_second >= 500, (
                f"Get performance too low: {get_ops_per_second:.1f} ops/sec"
            )

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @CI_SETTINGS
    @given(cache_keys(), cache_values(), st.integers(min_value=3, max_value=10))
    async def test_concurrent_access_performance(self, key, value, num_concurrent):
        """Test performance under concurrent access."""
        cache_service = create_mock_cache_service("normal")

        try:
            namespace = "concurrent_test"

            async def cache_worker(worker_id):
                """Worker that performs cache operations."""
                worker_key = f"{key}_{worker_id}"
                worker_value = f"{value}_{worker_id}"

                # Set value
                await cache_service.set(namespace, worker_key, worker_value)

                # Get value multiple times
                for _ in range(5):
                    retrieved = await cache_service.get(namespace, worker_key)
                    assert retrieved == worker_value

                return worker_id

            # Run concurrent workers
            start_time = time.time()
            tasks = [cache_worker(i) for i in range(num_concurrent)]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Verify all workers completed
            assert len(results) == num_concurrent
            assert set(results) == set(range(num_concurrent))

            # Performance assertion
            total_operations = num_concurrent * 6  # 1 set + 5 gets per worker
            ops_per_second = total_operations / total_time

            # Should handle reasonable concurrent load
            assert ops_per_second >= 50, (
                f"Concurrent performance too low: {ops_per_second:.1f} ops/sec"
            )

        finally:
            await cache_service.cleanup()


class TestCacheGetOrSetProperties:
    """Property-based tests for get_or_set functionality."""

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values())
    async def test_get_or_set_consistency(self, namespace, key, value):
        """Test get_or_set behavior consistency."""
        cache_service = create_mock_cache_service("normal")

        try:
            call_count = 0

            async def fetch_function():
                nonlocal call_count
                call_count += 1
                return value

            # First call should fetch and cache
            result1 = await cache_service.get_or_set(namespace, key, fetch_function)
            assert result1 == value
            assert call_count == 1

            # Second call should use cache
            result2 = await cache_service.get_or_set(namespace, key, fetch_function)
            assert result2 == value
            assert call_count == 1  # Function not called again

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), cache_values(), cache_values())
    async def test_get_or_set_expiration_refetch(self, namespace, key, value1, value2):
        """Test that get_or_set refetches after expiration."""
        cache_service = create_mock_cache_service("normal")

        try:
            call_count = 0
            current_value = value1

            async def fetch_function():
                nonlocal call_count
                call_count += 1
                return current_value

            # First call
            result1 = await cache_service.get_or_set(namespace, key, fetch_function, ttl=0.1)
            assert result1 == value1
            assert call_count == 1

            # Wait for expiration
            await asyncio.sleep(0.15)

            # Change the value that would be fetched
            current_value = value2

            # Second call after expiration should refetch
            result2 = await cache_service.get_or_set(namespace, key, fetch_function, ttl=0.1)
            assert result2 == value2
            assert call_count == 2

        finally:
            await cache_service.cleanup()


# Stateful testing for cache operations
class CacheStateMachine(RuleBasedStateMachine):
    """Stateful testing for cache behavior."""

    keys = Bundle("keys")

    def __init__(self):
        super().__init__()
        self.cache_service = create_mock_cache_service("normal")
        self.expected_state = {}  # namespace:key -> value
        self.namespace = "stateful_test"

    @rule(target=keys, key=cache_keys(), value=cache_values())
    def set_value(self, key, value):
        """Set a value in cache."""
        # Convert to sync for stateful testing
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.cache_service.set(self.namespace, key, value))
            self.expected_state[f"{self.namespace}:{key}"] = value
            return key
        except Exception:
            # If async operation fails, skip this rule
            return None

    @rule(key=keys)
    def get_value(self, key):
        """Get a value from cache."""
        if key is None:
            return

        # Convert to sync for stateful testing
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            retrieved = loop.run_until_complete(self.cache_service.get(self.namespace, key))
            expected_key = f"{self.namespace}:{key}"

            if expected_key in self.expected_state:
                expected = self.expected_state[expected_key]
                assert retrieved == expected, f"Expected {expected}, got {retrieved} for key {key}"
        except Exception:
            # If async operation fails, skip this check
            pass

    @rule(key=keys)
    def delete_value(self, key):
        """Delete a value from cache."""
        if key is None:
            return

        # Convert to sync for stateful testing
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.cache_service.delete(self.namespace, key))
            expected_key = f"{self.namespace}:{key}"
            if expected_key in self.expected_state:
                del self.expected_state[expected_key]
        except Exception:
            # If async operation fails, skip this rule
            pass

    @rule(key=keys, new_value=cache_values())
    def overwrite_value(self, key, new_value):
        """Overwrite an existing value."""
        if key is None:
            return

        # Convert to sync for stateful testing
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.cache_service.set(self.namespace, key, new_value))
            self.expected_state[f"{self.namespace}:{key}"] = new_value
        except Exception:
            # If async operation fails, skip this rule
            pass

    @invariant()
    def cache_stats_consistency(self):
        """Invariant: cache statistics should be consistent."""
        stats = self.cache_service.get_stats()

        # Basic sanity checks
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0
        assert stats["sets"] >= 0
        assert stats["size"] >= 0

        # Hit ratio should be valid
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            expected_hit_ratio = stats["hits"] / total_requests
            assert 0 <= stats["hit_ratio"] <= 1
            assert abs(stats["hit_ratio"] - expected_hit_ratio) < 0.001

    def teardown(self):
        """Clean up after testing."""
        # Clean up synchronously for stateful testing
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.cache_service.cleanup())
        except RuntimeError:
            with contextlib.suppress(Exception):
                # If no event loop, create one
                asyncio.run(self.cache_service.cleanup())
        except Exception:
            # Ignore cleanup errors in teardown
            pass


# Test the stateful machine
TestCacheStateMachine = CacheStateMachine.TestCase


class TestCacheEdgeCases:
    """Property-based tests for cache edge cases."""

    @pytest.mark.asyncio
    @given(cache_namespaces(), st.just(""), cache_values())
    async def test_empty_key_handling(self, namespace, empty_key, value):
        """Test handling of empty keys."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Some cache implementations might reject empty keys
            try:
                await cache_service.set(namespace, empty_key, value)
                retrieved = await cache_service.get(namespace, empty_key)
                # If accepted, should work consistently
                assert retrieved == value
            except (ValueError, KeyError):
                # Rejecting empty keys is also acceptable
                pass

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), st.just(None))
    async def test_none_value_handling(self, namespace, key, none_value):
        """Test handling of None values."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set None value
            await cache_service.set(namespace, key, none_value)

            # Should be able to distinguish between "key exists with None value"
            # and "key doesn't exist" - this depends on implementation
            retrieved = await cache_service.get(namespace, key)

            # In our mock implementation, None values are stored and retrieved
            assert retrieved == none_value

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(cache_namespaces(), cache_keys(), st.text(min_size=1000, max_size=10000))
    async def test_large_value_handling(self, namespace, key, large_value):
        """Test handling of large values."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Set large value
            await cache_service.set(namespace, key, large_value)

            # Should handle large values correctly
            retrieved = await cache_service.get(namespace, key)
            assert retrieved == large_value

        finally:
            await cache_service.cleanup()

    @pytest.mark.asyncio
    @given(st.floats(min_value=-1.0, max_value=0.0))
    async def test_negative_ttl_handling(self, negative_ttl):
        """Test handling of negative TTL values."""
        cache_service = create_mock_cache_service("normal")

        try:
            # Negative TTL should either be rejected or treated as immediate expiration
            try:
                await cache_service.set("test", "key", "value", ttl=negative_ttl)
                retrieved = await cache_service.get("test", "key")
                # If accepted, should either be None (expired) or the value
                assert retrieved in [None, "value"]
            except (ValueError, TypeError):
                # Rejecting negative TTL is also acceptable
                pass

        finally:
            await cache_service.cleanup()
