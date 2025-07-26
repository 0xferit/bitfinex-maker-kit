"""
Unit tests for utility modules.

Tests for utility functions including validators, formatters,
and helper functions without external dependencies.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch
from maker_kit.utilities.validators import (
    validate_symbol, validate_price, validate_amount,
    validate_order_params, ValidationError
)
from maker_kit.utilities.formatters import (
    format_price, format_amount, format_percentage,
    format_currency, format_order_summary
)
from maker_kit.utilities.response_parser import OrderResponseParser
from maker_kit.utilities.trading_helpers import (
    calculate_spread, calculate_mid_price, 
    generate_levels, calculate_order_total
)


class TestValidators:
    """Test cases for validation utilities."""
    
    def test_validate_symbol_valid(self):
        """Test valid symbol validation."""
        valid_symbols = ["tBTCUSD", "tETHUSD", "tPNKUSD", "fBTCUSD"]
        
        for symbol in valid_symbols:
            # Should not raise exception
            validate_symbol(symbol)
    
    def test_validate_symbol_invalid(self):
        """Test invalid symbol validation."""
        invalid_symbols = ["", "BTC", "INVALID", "tBTC", "123", None, "tbtcusd"]
        
        for symbol in invalid_symbols:
            with pytest.raises(ValidationError):
                validate_symbol(symbol)
    
    def test_validate_price_valid(self):
        """Test valid price validation."""
        valid_prices = ["0.01", "1.0", "50000.50", "999999.99", 50000, 50000.50]
        
        for price in valid_prices:
            # Should not raise exception
            validate_price(price)
    
    def test_validate_price_invalid(self):
        """Test invalid price validation."""
        invalid_prices = ["0", "-1", "-50000", "abc", "", None, 0, -1]
        
        for price in invalid_prices:
            with pytest.raises(ValidationError):
                validate_price(price)
    
    def test_validate_amount_valid(self):
        """Test valid amount validation."""
        valid_amounts = ["0.001", "1.0", "-1.0", "1000.5", "-1000.5", 1.5, -1.5]
        
        for amount in valid_amounts:
            # Should not raise exception
            validate_amount(amount)
    
    def test_validate_amount_invalid(self):
        """Test invalid amount validation."""
        invalid_amounts = ["0", "abc", "", None, 0]
        
        for amount in invalid_amounts:
            with pytest.raises(ValidationError):
                validate_amount(amount)
    
    def test_validate_order_params_valid(self):
        """Test valid order parameter validation."""
        valid_params = {
            'symbol': 'tBTCUSD',
            'amount': '1.0',
            'price': '50000.0',
            'side': 'buy',
            'type': 'EXCHANGE LIMIT'
        }
        
        # Should not raise exception
        validate_order_params(valid_params)
    
    def test_validate_order_params_invalid(self):
        """Test invalid order parameter validation."""
        # Missing required field
        invalid_params1 = {
            'symbol': 'tBTCUSD',
            'amount': '1.0',
            'price': '50000.0'
            # Missing 'side'
        }
        
        with pytest.raises(ValidationError):
            validate_order_params(invalid_params1)
        
        # Invalid field value
        invalid_params2 = {
            'symbol': 'INVALID',
            'amount': '1.0',
            'price': '50000.0',
            'side': 'buy'
        }
        
        with pytest.raises(ValidationError):
            validate_order_params(invalid_params2)


class TestFormatters:
    """Test cases for formatting utilities."""
    
    def test_format_price(self):
        """Test price formatting."""
        assert format_price(50000.50) == "50,000.50"
        assert format_price(1.23456, decimals=2) == "1.23"
        assert format_price(1000000) == "1,000,000.00"
    
    def test_format_amount(self):
        """Test amount formatting."""
        assert format_amount(1.23456) == "1.234560"
        assert format_amount(-1.23456) == "-1.234560"
        assert format_amount(1.23456, decimals=2) == "1.23"
    
    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(0.1234) == "12.34%"
        assert format_percentage(0.1234, decimals=1) == "12.3%"
        assert format_percentage(-0.0567) == "-5.67%"
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(1234.56, currency="EUR") == "€1,234.56"
        assert format_currency(-1234.56) == "-$1,234.56"
    
    def test_format_order_summary(self):
        """Test order summary formatting."""
        order = {
            'id': 12345678,
            'symbol': 'tBTCUSD',
            'amount': '1.0',
            'price': '50000.0',
            'side': 'buy',
            'status': 'ACTIVE'
        }
        
        summary = format_order_summary(order)
        assert "12345678" in summary
        assert "tBTCUSD" in summary
        assert "buy" in summary
        assert "ACTIVE" in summary


class TestResponseParser:
    """Test cases for response parser utilities."""
    
    def test_extract_order_id_from_response(self):
        """Test order ID extraction from API response."""
        response = {
            'id': 12345678,
            'symbol': 'tBTCUSD',
            'amount': '1.0',
            'price': '50000.0'
        }
        
        order_id = OrderResponseParser.extract_order_id(response)
        assert order_id == 12345678
    
    def test_extract_order_id_from_list(self):
        """Test order ID extraction from list response."""
        response_list = [
            {'id': 12345678, 'symbol': 'tBTCUSD'},
            {'id': 12345679, 'symbol': 'tETHUSD'}
        ]
        
        order_ids = OrderResponseParser.extract_order_ids(response_list)
        assert order_ids == [12345678, 12345679]
    
    def test_extract_order_id_missing(self):
        """Test order ID extraction when missing."""
        response = {
            'symbol': 'tBTCUSD',
            'amount': '1.0'
            # Missing 'id'
        }
        
        with pytest.raises(KeyError):
            OrderResponseParser.extract_order_id(response)
    
    def test_parse_order_status(self):
        """Test order status parsing."""
        response = {
            'id': 12345678,
            'status': 'ACTIVE',
            'amount': '1.0',
            'amount_orig': '1.0',
            'executed_amount': '0.0'
        }
        
        status = OrderResponseParser.parse_order_status(response)
        assert status['status'] == 'ACTIVE'
        assert status['fill_percentage'] == 0.0
    
    def test_parse_order_status_partial(self):
        """Test order status parsing for partial fill."""
        response = {
            'id': 12345678,
            'status': 'PARTIALLY_FILLED',
            'amount': '0.5',  # Remaining
            'amount_orig': '1.0',  # Original
            'executed_amount': '0.5'  # Filled
        }
        
        status = OrderResponseParser.parse_order_status(response)
        assert status['status'] == 'PARTIALLY_FILLED'
        assert status['fill_percentage'] == 50.0


class TestTradingHelpers:
    """Test cases for trading helper utilities."""
    
    def test_calculate_spread(self):
        """Test spread calculation."""
        bid = 49950.0
        ask = 50050.0
        
        spread = calculate_spread(bid, ask)
        assert spread == 100.0
        
        spread_pct = calculate_spread(bid, ask, as_percentage=True)
        assert abs(spread_pct - 0.2) < 0.01  # ~0.2%
    
    def test_calculate_mid_price(self):
        """Test mid price calculation."""
        bid = 49950.0
        ask = 50050.0
        
        mid_price = calculate_mid_price(bid, ask)
        assert mid_price == 50000.0
    
    def test_generate_levels(self):
        """Test level generation for market making."""
        center_price = 50000.0
        spread_pct = 0.1
        levels = 3
        
        bid_levels, ask_levels = generate_levels(center_price, spread_pct, levels)
        
        assert len(bid_levels) == levels
        assert len(ask_levels) == levels
        
        # Bids should be below center, asks above
        for bid in bid_levels:
            assert bid < center_price
        
        for ask in ask_levels:
            assert ask > center_price
        
        # Levels should be evenly spaced
        bid_diffs = [bid_levels[i] - bid_levels[i+1] for i in range(len(bid_levels)-1)]
        ask_diffs = [ask_levels[i+1] - ask_levels[i] for i in range(len(ask_levels)-1)]
        
        # All differences should be approximately equal
        for diff in bid_diffs[1:]:
            assert abs(diff - bid_diffs[0]) < 0.01
        
        for diff in ask_diffs[1:]:
            assert abs(diff - ask_diffs[0]) < 0.01
    
    def test_calculate_order_total(self):
        """Test order total calculation."""
        price = 50000.0
        amount = 1.5
        
        total = calculate_order_total(price, amount)
        assert total == 75000.0
        
        # With fees
        total_with_fees = calculate_order_total(price, amount, fee_rate=0.001)
        assert total_with_fees == 75075.0  # 75000 + 0.1% fee
    
    def test_calculate_order_total_sell(self):
        """Test order total calculation for sell orders."""
        price = 50000.0
        amount = -1.5  # Negative for sell
        
        total = calculate_order_total(price, amount)
        assert total == -75000.0  # Negative total for sell
    
    @pytest.mark.parametrize("bid,ask,expected_spread", [
        (100.0, 101.0, 1.0),
        (50000.0, 50100.0, 100.0),
        (0.1, 0.11, 0.01),
    ])
    def test_calculate_spread_parametrized(self, bid, ask, expected_spread):
        """Test spread calculation with various inputs."""
        spread = calculate_spread(bid, ask)
        assert abs(spread - expected_spread) < 0.001
    
    @pytest.mark.parametrize("center,spread_pct,levels,expected_range", [
        (100.0, 1.0, 3, (97.0, 103.0)),  # 1% spread, 3 levels
        (50000.0, 0.1, 5, (49750.0, 50250.0)),  # 0.1% spread, 5 levels
    ])
    def test_generate_levels_parametrized(self, center, spread_pct, levels, expected_range):
        """Test level generation with various parameters."""
        bid_levels, ask_levels = generate_levels(center, spread_pct, levels)
        
        min_bid = min(bid_levels)
        max_ask = max(ask_levels)
        
        assert min_bid >= expected_range[0]
        assert max_ask <= expected_range[1]


class TestUtilityEdgeCases:
    """Test edge cases for utility functions."""
    
    def test_validation_with_none_values(self):
        """Test validation with None values."""
        with pytest.raises((ValidationError, TypeError)):
            validate_symbol(None)
        
        with pytest.raises((ValidationError, TypeError)):
            validate_price(None)
        
        with pytest.raises((ValidationError, TypeError)):
            validate_amount(None)
    
    def test_formatting_with_edge_values(self):
        """Test formatting with edge case values."""
        # Very large numbers
        assert "1,000,000,000.00" in format_price(1000000000)
        
        # Very small numbers
        assert format_amount(0.000001, decimals=6) == "0.000001"
        
        # Zero values (where allowed)
        assert format_percentage(0.0) == "0.00%"
    
    def test_trading_helpers_edge_cases(self):
        """Test trading helpers with edge cases."""
        # Equal bid and ask (no spread)
        spread = calculate_spread(100.0, 100.0)
        assert spread == 0.0
        
        # Very small spread
        spread = calculate_spread(100.0, 100.01)
        assert spread == 0.01
        
        # Single level generation
        bid_levels, ask_levels = generate_levels(100.0, 0.1, 1)
        assert len(bid_levels) == 1
        assert len(ask_levels) == 1