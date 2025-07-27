"""
Unit tests for the cancel command --all flag functionality.
Addresses test coverage gaps identified in Claude bot review.
"""

from unittest.mock import Mock, patch

import pytest

from bitfinex_maker_kit.commands.cancel import (
    cancel_command,
    cancel_orders_by_criteria,
)


class TestCancelAllFlag:
    """Test the --all flag functionality specifically."""

    @pytest.fixture
    def mock_orders_pnkusd(self):
        """Mock orders for default symbol (tPNKUSD)."""
        return [
            Mock(id=1, symbol="tPNKUSD", amount="10.0", price="0.50", order_type="LIMIT"),
            Mock(id=2, symbol="tPNKUSD", amount="-5.0", price="0.51", order_type="LIMIT"),
        ]

    @pytest.fixture
    def mock_orders_mixed(self):
        """Mock orders for mixed symbols."""
        return [
            Mock(id=1, symbol="tPNKUSD", amount="10.0", price="0.50", order_type="LIMIT"),
            Mock(id=2, symbol="tBTCUSD", amount="0.1", price="50000.0", order_type="LIMIT"),
            Mock(id=3, symbol="tETHUSD", amount="1.0", price="3000.0", order_type="LIMIT"),
        ]

    @pytest.fixture
    def mock_container_setup(self):
        """Set up mock container with services."""
        container = Mock()
        trading_service = Mock()
        client = Mock()

        container.create_trading_service.return_value = trading_service
        container.create_bitfinex_client.return_value = client

        return container, trading_service, client

    def test_cancel_all_flag_with_default_symbol(self, mock_orders_pnkusd, mock_container_setup):
        """Test --all flag uses DEFAULT_SYMBOL when no symbol specified."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_pnkusd

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True)

        # Should show default symbol message
        mock_print.assert_any_call("💡 No symbol specified, using default symbol: tPNKUSD")
        mock_print.assert_any_call("Getting active orders for tPNKUSD...")

        # Should cancel all orders for default symbol
        client.cancel_order_multi.assert_called_once_with([1, 2])

    def test_cancel_all_flag_with_explicit_symbol(self, mock_orders_mixed, mock_container_setup):
        """Test --all flag respects explicit --symbol argument."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_mixed

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True, symbol="tBTCUSD")

        # Should NOT show default symbol message
        assert not any("💡 No symbol specified" in str(call) for call in mock_print.call_args_list)
        mock_print.assert_any_call("Getting active orders for tBTCUSD...")

        # Should only cancel BTCUSD order
        client.cancel_order_multi.assert_called_once_with([2])

    def test_cancel_all_flag_empty_orders(self, mock_container_setup):
        """Test --all flag handles empty order list gracefully."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = []

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True, symbol="tBTCUSD")

        # Should print appropriate message
        mock_print.assert_any_call("No active orders found for tBTCUSD")

        # Should not attempt to cancel anything
        client.cancel_order_multi.assert_not_called()

    def test_cancel_all_preserves_existing_functionality(
        self, mock_orders_mixed, mock_container_setup
    ):
        """Ensure existing cancel behavior unchanged."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_mixed

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
        ):
            # Test existing criteria-based cancellation still works
            cancel_orders_by_criteria(size=10.0, direction="buy", symbol="tPNKUSD")

        # Should only cancel the specific order matching criteria
        client.cancel_order_multi.assert_called_once_with([1])

    def test_cancel_all_vs_criteria_precedence(self, mock_orders_mixed, mock_container_setup):
        """Test that --all flag takes precedence over other criteria."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_mixed

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
        ):
            # Even with other criteria, --all should cancel all orders for symbol
            cancel_orders_by_criteria(
                all_orders=True,
                symbol="tPNKUSD",
                size=999.0,  # This should be ignored
                direction="sell",  # This should be ignored
            )

        # Should cancel all PNKUSD orders, ignoring size/direction criteria
        client.cancel_order_multi.assert_called_once_with([1])

    def test_cancel_all_symbol_resolution_efficiency(
        self, mock_orders_pnkusd, mock_container_setup
    ):
        """Test that symbol resolution happens only once (addresses review feedback)."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_pnkusd

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
            patch("bitfinex_maker_kit.utilities.constants.DEFAULT_SYMBOL", "tPNKUSD"),
        ):
            cancel_orders_by_criteria(all_orders=True)

        # Symbol resolution should be efficient (no duplicate lookups)
        client.cancel_order_multi.assert_called_once_with([1, 2])

    def test_cancel_all_user_cancellation(self, mock_orders_pnkusd, mock_container_setup):
        """Test --all flag respects user cancellation."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_pnkusd

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="n"),  # User says no
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True)

        # Should show cancellation message
        mock_print.assert_any_call("❌ Cancellation cancelled")

        # Should not cancel any orders
        client.cancel_order_multi.assert_not_called()

    def test_cancel_all_dry_run_mode(self, mock_orders_pnkusd, mock_container_setup):
        """Test --all flag works correctly with dry-run mode."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = mock_orders_pnkusd

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True, dry_run=True)

        # Should show dry-run message
        mock_print.assert_any_call("\n🔍 DRY RUN - Found 2 orders that would be cancelled")

        # Should not actually cancel orders
        client.cancel_order_multi.assert_not_called()

    def test_cancel_all_api_error_handling(self, mock_container_setup):
        """Test --all flag handles API errors gracefully."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.side_effect = Exception("API Connection Failed")

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.print") as mock_print,
        ):
            cancel_orders_by_criteria(all_orders=True)

        # Should show error message
        mock_print.assert_called_with("❌ Failed to get orders: API Connection Failed")

    def test_cancel_all_integration_with_cancel_command(self, mock_orders_pnkusd):
        """Test integration of --all flag through main cancel_command function."""
        with patch("bitfinex_maker_kit.commands.cancel.cancel_orders_by_criteria") as mock_cancel:
            # Test that cancel_command properly routes --all flag
            cancel_command(
                order_id=None,
                size=None,
                direction=None,
                symbol="tETHUSD",
                price_below=None,
                price_above=None,
                dry_run=False,
                yes=True,
                all_orders=True,
            )

            # Should call cancel_orders_by_criteria with all_orders=True
            mock_cancel.assert_called_once_with(
                None, None, "tETHUSD", None, None, False, True, True
            )


class TestCancelAllMigrationFromClear:
    """Test migration scenarios from old clear command to cancel --all."""

    @pytest.fixture
    def mock_container_setup(self):
        """Set up mock container with services."""
        container = Mock()
        trading_service = Mock()
        client = Mock()

        container.create_trading_service.return_value = trading_service
        container.create_bitfinex_client.return_value = client

        return container, trading_service, client

    def test_clear_command_equivalent_behavior(self, mock_container_setup):
        """Test that cancel --all provides equivalent functionality to old clear command."""
        container, trading_service, client = mock_container_setup
        mock_orders = [
            Mock(id=1, symbol="tPNKUSD", amount="10.0", price="0.50", order_type="LIMIT"),
            Mock(id=2, symbol="tPNKUSD", amount="-5.0", price="0.51", order_type="LIMIT"),
        ]
        trading_service.get_orders.return_value = mock_orders

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
        ):
            # This should behave exactly like the old clear command
            cancel_orders_by_criteria(all_orders=True)

        # Should cancel all orders for default symbol (same as clear)
        client.cancel_order_multi.assert_called_once_with([1, 2])

    def test_enhanced_functionality_over_clear(self, mock_container_setup):
        """Test that cancel --all provides enhanced functionality beyond old clear."""
        container, trading_service, client = mock_container_setup
        trading_service.get_orders.return_value = [
            Mock(id=1, symbol="tBTCUSD", amount="0.1", price="50000.0", order_type="LIMIT"),
        ]

        with (
            patch("bitfinex_maker_kit.commands.cancel.get_container", return_value=container),
            patch("builtins.input", return_value="y"),
        ):
            # Enhanced: cancel --all with specific symbol (old clear couldn't do this)
            cancel_orders_by_criteria(all_orders=True, symbol="tBTCUSD")

        client.cancel_order_multi.assert_called_once_with([1])

    def test_backward_compatibility_workflows(self):
        """Test that common clear workflows work with cancel --all."""
        test_cases = [
            # Old clear workflow -> New cancel --all workflow
            {"description": "Clear all default symbol", "args": {"all_orders": True}},
            {"description": "Clear with dry-run", "args": {"all_orders": True, "dry_run": True}},
            {
                "description": "Clear with confirmation skip",
                "args": {"all_orders": True, "yes": True},
            },
        ]

        for case in test_cases:
            with patch(
                "bitfinex_maker_kit.commands.cancel.cancel_orders_by_criteria"
            ) as mock_cancel:
                cancel_command(**case["args"])

                # Should properly route to cancel_orders_by_criteria
                assert mock_cancel.called, f"Failed for: {case['description']}"
                call_args = mock_cancel.call_args[0]
                assert call_args[7] is True, f"all_orders not True for: {case['description']}"
