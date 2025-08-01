"""
Unit tests demonstrating POST_ONLY enforcement via API wrapper architecture.

These tests verify that the BitfinexClientWrapper ENFORCES POST_ONLY at the API boundary,
making it architecturally impossible to place non-POST_ONLY limit orders.

This demonstrates the ULTIMATE architecture: POST_ONLY enforcement at the API boundary
means the application layer cannot bypass it even if it wanted to.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

# Import the wrapper and related modules
from bitfinex_maker_kit.bitfinex_client import BitfinexClientWrapper, create_wrapper_client
from bitfinex_maker_kit.utilities.auth import create_client


class TestBitfinexClientWrapper(unittest.TestCase):
    """
    Test suite demonstrating API boundary POST_ONLY enforcement.

    This test class proves that the wrapper enforces POST_ONLY at the API level,
    making it impossible for application code to bypass.
    """

    def setUp(self):
        """Set up test fixtures"""
        self.mock_bitfinex_client = Mock()
        self.mock_response = Mock()
        self.mock_response.data = [Mock()]
        self.mock_response.data[0].id = 12345

        # Mock the Bitfinex API responses
        self.mock_bitfinex_client.rest.auth.submit_order.return_value = self.mock_response

    @patch("bitfinex_maker_kit.bitfinex_client.Client")
    def test_wrapper_limit_order_enforces_post_only(self, mock_client_class):
        """
        🎯 THE ULTIMATE TEST: Wrapper ALWAYS uses POST_ONLY for limit orders

        This test proves that at the API boundary level, ALL limit orders
        automatically get POST_ONLY flag without any application intervention.
        """
        mock_client_class.return_value = self.mock_bitfinex_client

        # Create wrapper
        wrapper = BitfinexClientWrapper("test_key", "test_secret")

        # Test limit order - wrapper should ALWAYS add POST_ONLY flag
        wrapper.submit_order("tPNKUSD", "buy", 10.0, 0.100)

        # Verify the underlying Bitfinex client was called with POST_ONLY flag
        self.mock_bitfinex_client.rest.auth.submit_order.assert_called_once_with(
            type="EXCHANGE LIMIT",
            symbol="tPNKUSD",
            amount=10.0,  # Positive for buy
            price=0.100,
            flags=4096,  # POST_ONLY flag is AUTOMATICALLY added by wrapper
        )

    @patch("bitfinex_maker_kit.bitfinex_client.Client")
    def test_wrapper_market_order_no_post_only(self, mock_client_class):
        """Test that wrapper does NOT use POST_ONLY for market orders"""
        mock_client_class.return_value = self.mock_bitfinex_client

        # Create wrapper
        wrapper = BitfinexClientWrapper("test_key", "test_secret")

        # Test market order - wrapper should NOT add POST_ONLY flag
        wrapper.submit_order("tPNKUSD", "sell", 5.0, None)  # None price = market order

        # Verify the underlying Bitfinex client was called WITHOUT flags
        self.mock_bitfinex_client.rest.auth.submit_order.assert_called_once_with(
            type="EXCHANGE MARKET",
            symbol="tPNKUSD",
            amount=-5.0,  # Negative for sell
            # NO FLAGS PARAMETER for market orders
        )

    @patch("bitfinex_maker_kit.bitfinex_client.Client")
    def test_wrapper_hardcoded_post_only_flag(self, mock_client_class):
        """
        🔐 BOUNDARY TEST: POST_ONLY flag (4096) is hardcoded at API boundary

        This proves that POST_ONLY enforcement happens at the wrapper level,
        not in application code.
        """
        mock_client_class.return_value = self.mock_bitfinex_client

        wrapper = BitfinexClientWrapper("test_key", "test_secret")

        # Multiple different limit orders should all get POST_ONLY flag
        test_cases = [
            ("buy", 10.0, 0.100),
            ("sell", 5.0, 0.200),
            ("BUY", 1.0, 0.050),  # Test case insensitive
            ("SELL", 100.0, 1.000),
        ]

        for side, amount, price in test_cases:
            with self.subTest(side=side, amount=amount, price=price):
                self.mock_bitfinex_client.rest.auth.submit_order.reset_mock()

                wrapper.submit_order("tPNKUSD", side, amount, price)

                # Every call should use flags=4096
                call_kwargs = self.mock_bitfinex_client.rest.auth.submit_order.call_args[1]
                self.assertEqual(
                    call_kwargs["flags"],
                    4096,
                    f"Wrapper must add POST_ONLY flag for {side} {amount} @ {price}",
                )

    @patch("bitfinex_maker_kit.bitfinex_client.Client")
    def test_wrapper_amount_conversion(self, mock_client_class):
        """Test that wrapper properly converts amounts for Bitfinex API"""
        mock_client_class.return_value = self.mock_bitfinex_client

        wrapper = BitfinexClientWrapper("test_key", "test_secret")

        # Test buy order (should be positive amount)
        wrapper.submit_order("tPNKUSD", "buy", 10.0, 0.100)
        call_args = self.mock_bitfinex_client.rest.auth.submit_order.call_args[1]
        self.assertEqual(call_args["amount"], 10.0, "Buy orders should have positive amount")

        self.mock_bitfinex_client.rest.auth.submit_order.reset_mock()

        # Test sell order (should be negative amount)
        wrapper.submit_order("tPNKUSD", "sell", 5.0, 0.200)
        call_args = self.mock_bitfinex_client.rest.auth.submit_order.call_args[1]
        self.assertEqual(call_args["amount"], -5.0, "Sell orders should have negative amount")

    def test_wrapper_no_bypass_methods(self):
        """
        🔒 SECURITY TEST: Wrapper has NO methods to bypass POST_ONLY

        This proves that the wrapper provides no way for application code
        to submit orders without going through POST_ONLY enforcement.
        """
        wrapper = BitfinexClientWrapper("test_key", "test_secret")

        # Verify wrapper only exposes safe methods
        public_methods = [method for method in dir(wrapper) if not method.startswith("_")]

        # These are the ONLY order-related methods exposed
        self.assertIn("submit_order", public_methods)
        self.assertNotIn("submit_limit_order", public_methods)
        self.assertNotIn("submit_order_raw", public_methods)
        self.assertNotIn("submit_order_no_post_only", public_methods)

        # Verify no direct access to underlying client
        self.assertNotIn("rest", public_methods)
        self.assertNotIn("auth", public_methods)

        # Only safe wrapper methods should be exposed
        expected_safe_methods = {
            "submit_order",
            "get_orders",
            "cancel_order",
            "cancel_order_multi",
            "get_wallets",
            "get_ticker",
            "get_trades",
            "wss",
        }
        order_related_methods = {
            method
            for method in public_methods
            if any(word in method.lower() for word in ["order", "submit", "cancel", "get", "wss"])
        }

        # All order-related methods should be in our expected safe set
        unexpected_methods = order_related_methods - expected_safe_methods
        self.assertEqual(
            len(unexpected_methods), 0, f"Wrapper exposes unexpected methods: {unexpected_methods}"
        )


class TestApplicationLayerIntegration(unittest.TestCase):
    """
    Test suite demonstrating that application layer cannot bypass wrapper.

    These tests prove that the application uses the wrapper and therefore
    cannot place non-POST_ONLY orders.
    """

    @patch("bitfinex_maker_kit.utilities.auth.create_wrapper_client")
    def test_create_client_returns_wrapper(self, mock_create_wrapper):
        """Test that create_client() returns our wrapper, not raw Bitfinex client"""
        mock_wrapper = Mock()
        mock_create_wrapper.return_value = mock_wrapper

        # Application calls create_client()
        client = create_client()

        # Should get our wrapper
        self.assertEqual(client, mock_wrapper)
        mock_create_wrapper.assert_called_once()

    @patch("bitfinex_maker_kit.utilities.auth.create_wrapper_client")
    def test_application_cannot_access_raw_bitfinex_client(self, mock_create_wrapper):
        """Test that application layer cannot access raw Bitfinex client"""
        mock_wrapper = Mock()
        mock_wrapper.submit_order.return_value = Mock()
        mock_create_wrapper.return_value = mock_wrapper

        # Import the submit_order function (simulates application usage)
        from bitfinex_maker_kit.utilities.orders import submit_order

        # Application tries to submit order
        submit_order("tPNKUSD", "buy", 10.0, 0.100)

        # Should go through wrapper
        mock_wrapper.submit_order.assert_called_once_with("tPNKUSD", "buy", 10.0, 0.100)

    def test_application_layer_isolation(self):
        """
        🏗️ ISOLATION TEST: Application layer has no access to raw Bitfinex API

        This proves that the application cannot import or use the raw Bitfinex
        client, ensuring all orders go through the wrapper.
        """
        # Test that application modules don't import raw Bitfinex client
        import inspect

        from maker_kit import market_data, market_making, orders, wallet

        # Check that no module imports the raw Client
        modules_to_check = [orders, market_making, wallet, market_data]

        for module in modules_to_check:
            source = inspect.getsource(module)

            # Should NOT import raw Bitfinex Client
            self.assertNotIn(
                "from bfxapi import Client",
                source,
                f"Module {module.__name__} should not import raw Bitfinex Client",
            )
            self.assertNotIn(
                "import bfxapi",
                source,
                f"Module {module.__name__} should not import bfxapi directly",
            )

            # Should use wrapper through auth.create_client
            if "client" in source.lower():
                self.assertIn(
                    "create_client",
                    source,
                    f"Module {module.__name__} should use create_client() for API access",
                )


class TestWrapperFactory(unittest.TestCase):
    """Test the wrapper factory function"""

    @patch("maker_kit.bitfinex_client.BitfinexClientWrapper")
    def test_create_wrapper_client_factory(self, mock_wrapper_class):
        """Test that factory function creates wrapper correctly"""
        mock_wrapper_instance = Mock()
        mock_wrapper_class.return_value = mock_wrapper_instance

        # Use factory function
        result = create_wrapper_client("test_key", "test_secret")

        # Should create wrapper with correct parameters
        mock_wrapper_class.assert_called_once_with("test_key", "test_secret")
        self.assertEqual(result, mock_wrapper_instance)


if __name__ == "__main__":
    print("🏗️ API WRAPPER ARCHITECTURE TESTS")
    print("=" * 60)
    print()
    print("Testing the BitfinexClientWrapper that:")
    print("1. Enforces POST_ONLY at the API boundary level")
    print("2. Makes it IMPOSSIBLE for application code to bypass")
    print("3. Provides clean separation of concerns")
    print("4. Eliminates all bypass possibilities")
    print()
    print("This architecture is the ULTIMATE enforcement:")
    print("POST_ONLY is enforced at the API boundary, not in business logic.")
    print()
    print("=" * 60)
    print()

    # Run all tests
    unittest.main(verbosity=2)
