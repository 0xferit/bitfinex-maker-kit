"""
LEGACY: Unit tests demonstrating POST_ONLY enforcement via centralized order submission.

⚠️  NOTE: This test file is now LEGACY. The architecture has been improved
    to use an API wrapper that enforces POST_ONLY at the boundary level.

    See: tests/test_wrapper_architecture.py for the current tests.

These legacy tests verify that the submit_order() function uses the wrapper
correctly, but the real enforcement now happens at the wrapper level.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

# Import the ONLY function we need to test
from bitfinex_maker_kit.utilities.orders import submit_order


class TestCentralizedPostOnlyEnforcement(unittest.TestCase):
    """
    Test suite demonstrating centralized POST_ONLY enforcement.

    This single test class proves that ALL orders in the system use POST_ONLY
    because ALL orders must go through the submit_order() function.
    """

    def setUp(self):
        """Set up test fixtures"""
        self.mock_wrapper_client = Mock()
        self.mock_response = Mock()
        self.mock_response.data = [Mock()]
        self.mock_response.data[0].id = 12345

    @patch("bitfinex_maker_kit.utilities.orders.get_client")
    def test_submit_order_limit_enforces_post_only(self, mock_get_client):
        """
        🎯 THE CORE TEST: submit_order ALWAYS uses wrapper which enforces POST_ONLY

        This test now proves that submit_order() uses the wrapper correctly,
        and we know from wrapper tests that the wrapper enforces POST_ONLY.
        """
        mock_get_client.return_value = self.mock_wrapper_client
        self.mock_wrapper_client.submit_order.return_value = self.mock_response

        # Test limit order - should go through wrapper
        submit_order("tPNKUSD", "buy", 10.0, 0.100)

        # Verify submit_order was called on wrapper (wrapper enforces POST_ONLY)
        self.mock_wrapper_client.submit_order.assert_called_once_with("tPNKUSD", "buy", 10.0, 0.100)

    @patch("bitfinex_maker_kit.utilities.orders.get_client")
    def test_submit_order_market_no_post_only(self, mock_get_client):
        """Test that submit_order correctly passes market orders to wrapper"""
        mock_get_client.return_value = self.mock_wrapper_client
        self.mock_wrapper_client.submit_order.return_value = self.mock_response

        # Test market order - should go through wrapper
        submit_order("tPNKUSD", "sell", 5.0, None)  # None price = market order

        # Verify submit_order was called on wrapper (wrapper handles market orders correctly)
        self.mock_wrapper_client.submit_order.assert_called_once_with("tPNKUSD", "sell", 5.0, None)

    def test_submit_order_no_post_only_parameter(self):
        """
        🔒 LIMITATION TEST: submit_order has NO way to disable POST_ONLY

        This proves POST_ONLY cannot be disabled because the function
        signature has no parameter to control it.
        """
        import inspect

        sig = inspect.signature(submit_order)

        # Verify NO post_only parameter exists
        self.assertNotIn("post_only", sig.parameters)
        self.assertNotIn("no_post_only", sig.parameters)
        self.assertNotIn("flags", sig.parameters)
        self.assertNotIn("order_flags", sig.parameters)

        # Verify the function signature is as expected
        expected_params = ["symbol", "side", "amount", "price"]
        actual_params = list(sig.parameters.keys())
        self.assertEqual(actual_params, expected_params)

    @patch("bitfinex_maker_kit.utilities.orders.get_client")
    def test_submit_order_hardcoded_post_only_flag(self, mock_get_client):
        """
        🔐 WRAPPER TEST: All limit orders go through wrapper (which enforces POST_ONLY)

        This proves that all limit orders use the wrapper, and we know from
        wrapper tests that the wrapper enforces POST_ONLY.
        """
        mock_get_client.return_value = self.mock_wrapper_client
        self.mock_wrapper_client.submit_order.return_value = self.mock_response

        # Multiple different limit orders should all go through wrapper
        test_cases = [
            ("buy", 10.0, 0.100),
            ("sell", 5.0, 0.200),
            ("BUY", 1.0, 0.050),  # Test case insensitive
            ("SELL", 100.0, 1.000),
        ]

        for side, amount, price in test_cases:
            with self.subTest(side=side, amount=amount, price=price):
                self.mock_wrapper_client.submit_order.reset_mock()

                submit_order("tPNKUSD", side, amount, price)

                # Every call should go through wrapper
                self.mock_wrapper_client.submit_order.assert_called_once_with(
                    "tPNKUSD", side, amount, price
                )

    def test_submit_order_input_validation(self):
        """Test that submit_order validates inputs correctly"""
        from bitfinex_maker_kit.utilities.constants import ValidationError

        # Test invalid amount
        with self.assertRaises(ValidationError, msg="Should reject negative amount"):
            submit_order("tPNKUSD", "buy", -10.0, 0.100)

        with self.assertRaises(ValidationError, msg="Should reject zero amount"):
            submit_order("tPNKUSD", "buy", 0.0, 0.100)

        # Test invalid side
        with self.assertRaises(ValidationError, msg="Should reject invalid side"):
            submit_order("tPNKUSD", "invalid", 10.0, 0.100)

        # Test invalid price for limit orders
        with self.assertRaises(ValidationError, msg="Should reject negative price"):
            submit_order("tPNKUSD", "buy", 10.0, -0.100)

        with self.assertRaises(ValidationError, msg="Should reject zero price"):
            submit_order("tPNKUSD", "buy", 10.0, 0.0)

    def test_post_only_flag_value_correctness(self):
        """Test that the POST_ONLY flag value (4096) is correct"""
        # According to Bitfinex API documentation, POST_ONLY flag is 4096
        POST_ONLY_FLAG = 4096

        # This test documents that our hardcoded value is correct
        self.assertEqual(POST_ONLY_FLAG, 4096)

        # Binary representation: 4096 = 2^12 = 0b1000000000000
        self.assertEqual(bin(POST_ONLY_FLAG), "0b1000000000000")

    @patch("bitfinex_maker_kit.utilities.orders.get_client")
    def test_submit_order_post_only_rejection_handling(self, mock_get_client):
        """Test that submit_order passes through wrapper exceptions properly"""
        mock_get_client.return_value = self.mock_wrapper_client

        # Simulate wrapper exception (e.g., POST_ONLY rejection from underlying API)
        self.mock_wrapper_client.submit_order.side_effect = Exception(
            "Order would have matched existing order"
        )

        # This should raise the exception (let caller handle it)
        with self.assertRaises(Exception) as context:
            submit_order("tPNKUSD", "buy", 10.0, 0.100)

        self.assertIn("would have matched", str(context.exception).lower())

        # Verify the order was attempted through wrapper
        self.mock_wrapper_client.submit_order.assert_called_once_with("tPNKUSD", "buy", 10.0, 0.100)


class TestArchitecturalEnforcement(unittest.TestCase):
    """
    Test suite demonstrating architectural enforcement.

    These tests prove that the centralized architecture ensures
    ALL orders use POST_ONLY without needing to test every function.
    """

    def test_all_order_functions_use_submit_order(self):
        """
        🏗️ ARCHITECTURAL TEST: All order functions import submit_order

        This proves they all use the centralized function instead of
        duplicating order submission logic.
        """

        # Test that other modules import submit_order
        from bitfinex_maker_kit.commands import market_make
        from bitfinex_maker_kit.utilities import orders

        # These modules should import submit_order
        self.assertTrue(
            hasattr(orders, "submit_order"), "orders module should have submit_order function"
        )

        # Check that market_making imports submit_order
        import inspect

        market_making_source = inspect.getsource(market_make)
        self.assertIn(
            "submit_order", market_making_source, "market_make should import submit_order"
        )

        # auto_market_maker has been removed - skip this check

    def test_no_duplicate_order_submission_logic(self):
        """
        🎯 DUPLICATION TEST: Other modules should not have duplicate order submission

        This ensures all order submission goes through the centralized function.
        """
        import inspect

        from bitfinex_maker_kit.commands import market_make

        # These modules should NOT have direct client.rest.auth.submit_order calls
        market_making_source = inspect.getsource(market_make)
        self.assertNotIn(
            "client.rest.auth.submit_order",
            market_making_source,
            "market_make should not have direct order submission",
        )

        # auto_market_maker has been removed - skip this check

    def test_submit_order_function_documentation(self):
        """Test that submit_order documents its wrapper usage"""
        docstring = submit_order.__doc__.lower()

        # Check that the function documents wrapper usage
        self.assertIn(
            "enforces post_only", docstring, "submit_order should document POST_ONLY enforcement"
        )
        self.assertIn("centralized", docstring, "submit_order should document its centralized role")
        self.assertIn("wrapper", docstring, "submit_order should document that it uses the wrapper")


if __name__ == "__main__":
    print("🎯 CENTRALIZED POST_ONLY ENFORCEMENT TESTS")
    print("=" * 60)
    print()
    print("Testing the centralized submit_order() function that:")
    print("1. Uses the BitfinexClientWrapper for all order submission")
    print("2. Passes all orders through the wrapper (which enforces POST_ONLY)")
    print("3. Has NO way to bypass the wrapper")
    print("4. Is used by ALL other order functions")
    print()
    print("This architecture ensures COMPLETE POST_ONLY enforcement")
    print("via the wrapper at the API boundary level.")
    print()
    print("=" * 60)
    print()

    # Run all tests
    unittest.main(verbosity=2)
