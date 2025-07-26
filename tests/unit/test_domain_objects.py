"""
Unit tests for domain objects.

Tests for domain value objects including Symbol, Price, Amount, and OrderId
focusing on validation, conversion, and business logic.
"""

from decimal import Decimal, InvalidOperation

import pytest

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.order_id import OrderId
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol


class TestSymbol:
    """Test cases for Symbol domain object."""

    def test_valid_symbol_creation(self):
        """Test creating valid symbols."""
        symbol = Symbol("tBTCUSD")
        assert str(symbol) == "tBTCUSD"
        assert symbol.value == "tBTCUSD"

    def test_symbol_validation(self):
        """Test symbol validation rules."""
        # Valid symbols
        valid_symbols = ["tBTCUSD", "tETHUSD", "tPNKUSD", "fBTCUSD"]
        for symbol_str in valid_symbols:
            symbol = Symbol(symbol_str)
            assert str(symbol) == symbol_str

    def test_invalid_symbol_creation(self):
        """Test invalid symbol creation raises errors."""
        invalid_symbols = ["", "BTC", "INVALID", "tBTC", "123", None]

        for invalid_symbol in invalid_symbols:
            with pytest.raises((ValueError, TypeError)):
                Symbol(invalid_symbol)

    def test_symbol_equality(self):
        """Test symbol equality comparison."""
        symbol1 = Symbol("tBTCUSD")
        symbol2 = Symbol("tBTCUSD")
        symbol3 = Symbol("tETHUSD")

        assert symbol1 == symbol2
        assert symbol1 != symbol3
        assert symbol1 == "tBTCUSD"
        assert symbol1 != "tETHUSD"

    def test_symbol_hash(self):
        """Test symbol hashing for use in sets/dicts."""
        symbol1 = Symbol("tBTCUSD")
        symbol2 = Symbol("tBTCUSD")
        symbol3 = Symbol("tETHUSD")

        assert hash(symbol1) == hash(symbol2)
        assert hash(symbol1) != hash(symbol3)

        # Test in set
        symbol_set = {symbol1, symbol2, symbol3}
        assert len(symbol_set) == 2  # symbol1 and symbol2 are same

    def test_symbol_representation(self):
        """Test symbol string representation."""
        symbol = Symbol("tBTCUSD")
        assert repr(symbol) == "Symbol('tBTCUSD')"
        assert str(symbol) == "tBTCUSD"

    def test_symbol_case_sensitivity(self):
        """Test symbol case sensitivity."""
        with pytest.raises(ValueError):
            Symbol("tbtcusd")  # Should be uppercase

        with pytest.raises(ValueError):
            Symbol("TBTCUSD")  # Should start with lowercase 't'


class TestPrice:
    """Test cases for Price domain object."""

    def test_valid_price_creation(self):
        """Test creating valid prices."""
        # From string
        price1 = Price("50000.50")
        assert price1.value == Decimal("50000.50")

        # From int
        price2 = Price(50000)
        assert price2.value == Decimal("50000")

        # From float
        price3 = Price(50000.50)
        assert price3.value == Decimal("50000.50")

        # From Decimal
        price4 = Price(Decimal("50000.50"))
        assert price4.value == Decimal("50000.50")

    def test_price_validation(self):
        """Test price validation rules."""
        # Valid prices
        valid_prices = ["0.01", "1.0", "50000.50", "999999.99"]
        for price_str in valid_prices:
            price = Price(price_str)
            assert price.value > 0

        # Invalid prices
        invalid_prices = ["0", "-1", "-50000", "abc", "", None]
        for invalid_price in invalid_prices:
            with pytest.raises((ValueError, TypeError, InvalidOperation)):
                Price(invalid_price)

    def test_price_precision(self):
        """Test price precision handling."""
        price = Price("50000.123456789")
        # Should maintain precision
        assert str(price.value) == "50000.123456789"

    def test_price_arithmetic(self):
        """Test price arithmetic operations."""
        price1 = Price("50000.50")
        price2 = Price("1000.25")

        # Addition
        result_add = price1 + price2
        assert result_add.value == Decimal("51000.75")

        # Subtraction
        result_sub = price1 - price2
        assert result_sub.value == Decimal("49000.25")

        # Multiplication
        result_mul = price1 * Decimal("2")
        assert result_mul.value == Decimal("100001.00")

        # Division
        result_div = price1 / Decimal("2")
        assert result_div.value == Decimal("25000.25")

    def test_price_comparison(self):
        """Test price comparison operations."""
        price1 = Price("50000.50")
        price2 = Price("50000.50")
        price3 = Price("60000.00")
        price4 = Price("40000.00")

        # Equality
        assert price1 == price2
        assert price1 != price3

        # Comparison
        assert price1 < price3
        assert price1 > price4
        assert price1 <= price2
        assert price1 >= price2

    def test_price_representation(self):
        """Test price string representation."""
        price = Price("50000.50")
        assert str(price) == "50000.50"
        assert repr(price) == "Price('50000.50')"


class TestAmount:
    """Test cases for Amount domain object."""

    def test_valid_amount_creation(self):
        """Test creating valid amounts."""
        # Positive amount
        amount1 = Amount("1.5")
        assert amount1.value == Decimal("1.5")

        # From various types
        amount2 = Amount(1.5)
        assert amount2.value == Decimal("1.5")

        amount3 = Amount(Decimal("1.5"))
        assert amount3.value == Decimal("1.5")

    def test_amount_validation(self):
        """Test amount validation rules."""
        # Valid amounts
        valid_amounts = ["0.001", "1.0", "1000.5"]
        for amount_str in valid_amounts:
            amount = Amount(amount_str)
            assert amount.value > 0

        # Invalid amounts (zero, negative, or non-numeric)
        invalid_amounts = ["0", "-1.0", "-1000.5", "abc", "", None]
        for invalid_amount in invalid_amounts:
            with pytest.raises((ValueError, TypeError, InvalidOperation)):
                Amount(invalid_amount)

    def test_amount_sign_operations(self):
        """Test amount sign operations."""
        amount = Amount("1.5")

        # Absolute value (should return self since all amounts are positive)
        assert amount.abs() is amount
        assert amount.abs().value == Decimal("1.5")

        # Sign checking (all amounts are positive)
        assert amount.is_positive()
        assert not amount.is_negative()

    def test_amount_arithmetic(self):
        """Test amount arithmetic operations."""
        amount1 = Amount("1.5")
        amount2 = Amount("0.5")

        # Addition
        result_add = amount1 + amount2
        assert result_add.value == Decimal("2.0")

        # Subtraction
        result_sub = amount1 - amount2
        assert result_sub.value == Decimal("1.0")

        # Multiplication
        result_mul = amount1 * Decimal("2")
        assert result_mul.value == Decimal("3.0")

        # Division
        result_div = amount1 / Decimal("3")
        assert result_div.value == Decimal("0.5")

    def test_amount_arithmetic_invariants(self):
        """Test that arithmetic operations maintain the positive, non-zero invariant."""
        amount1 = Amount("1.5")
        amount2 = Amount("0.5")

        # Test subtraction that would result in zero (should fail)
        with pytest.raises(ValueError, match="Subtraction would result in non-positive amount"):
            amount1 - amount1

        # Test multiplication by zero (should fail)
        with pytest.raises(ValueError, match="Multiplication factor must be positive"):
            amount1 * 0

        # Test multiplication by negative number (should fail)
        with pytest.raises(ValueError, match="Multiplication factor must be positive"):
            amount1 * -1

        # Test division by zero (should fail)
        with pytest.raises(ValueError, match="Division divisor must be positive"):
            amount1 / 0

        # Test division by negative number (should fail)
        with pytest.raises(ValueError, match="Division divisor must be positive"):
            amount1 / -1

        # Test division by extremely large number (should fail)
        with pytest.raises(
            ValueError,
            match="Division by extremely large number would result in effectively zero amount",
        ):
            amount1 / Decimal("1e20")

        # Test that valid operations work correctly
        result = amount1 + amount2
        assert result.value == Decimal("2.0")

        result = amount1 - amount2
        assert result.value == Decimal("1.0")

        result = amount1 * Decimal("2")
        assert result.value == Decimal("3.0")

        result = amount1 / Decimal("2")
        assert result.value == Decimal("0.75")

    def test_amount_arithmetic_edge_cases(self):
        """Test edge cases in amount arithmetic operations."""
        # Test with very small amounts
        small_amount = Amount("0.00000001")

        # Multiplication should work with positive factors
        result = small_amount * Decimal("2")
        assert result.value > 0

        # Division should work with reasonable divisors
        result = small_amount / Decimal("2")
        assert result.value > 0

        # Test that the add method also validates properly
        amount1 = Amount("1.0")
        amount2 = Amount("0.5")

        result = amount1.add(amount2)
        assert result.value == Decimal("1.5")

        # Test that multiply method validates factors
        with pytest.raises(ValueError, match="Multiplication factor must be positive"):
            amount1.multiply(0)

    def test_amount_comparison(self):
        """Test amount comparison operations."""
        amount1 = Amount("1.5")
        amount2 = Amount("1.5")
        amount3 = Amount("2.0")

        # Equality
        assert amount1 == amount2
        assert amount1 != amount3

        # Comparison
        assert amount1 < amount3
        assert amount1 <= amount2
        assert amount1 >= amount2


class TestOrderId:
    """Test cases for OrderId domain object."""

    def test_valid_order_id_creation(self):
        """Test creating valid order IDs."""
        # From string
        order_id1 = OrderId("12345678")
        assert order_id1.value == 12345678

        # From int
        order_id2 = OrderId(12345678)
        assert order_id2.value == 12345678

    def test_order_id_validation(self):
        """Test order ID validation rules."""
        # Valid order IDs
        valid_ids = ["12345678", 12345678, "99999999", 99999999]
        for order_id in valid_ids:
            oid = OrderId(order_id)
            assert oid.value > 0

        # Invalid order IDs
        invalid_ids = ["0", 0, "-1", -1, "abc", "", None, "12345", 12345]
        for invalid_id in invalid_ids:
            with pytest.raises((ValueError, TypeError)):
                OrderId(invalid_id)

    def test_order_id_equality(self):
        """Test order ID equality comparison."""
        order_id1 = OrderId("12345678")
        order_id2 = OrderId(12345678)
        order_id3 = OrderId("87654321")

        assert order_id1 == order_id2
        assert order_id1 != order_id3
        assert order_id1 == 12345678
        assert order_id1 != 87654321

    def test_order_id_hash(self):
        """Test order ID hashing."""
        order_id1 = OrderId("12345678")
        order_id2 = OrderId(12345678)
        order_id3 = OrderId("87654321")

        assert hash(order_id1) == hash(order_id2)
        assert hash(order_id1) != hash(order_id3)

        # Test in set
        id_set = {order_id1, order_id2, order_id3}
        assert len(id_set) == 2  # order_id1 and order_id2 are same

    def test_order_id_representation(self):
        """Test order ID string representation."""
        order_id = OrderId("12345678")
        assert str(order_id) == "12345678"
        assert repr(order_id) == "OrderId(12345678)"

    def test_order_id_comparison(self):
        """Test order ID comparison operations."""
        order_id1 = OrderId("12345678")
        order_id2 = OrderId("12345678")
        order_id3 = OrderId("87654321")
        order_id4 = OrderId("11111111")

        # Equality
        assert order_id1 == order_id2
        assert order_id1 != order_id3

        # Comparison
        assert order_id1 < order_id3
        assert order_id1 > order_id4
        assert order_id1 <= order_id2
        assert order_id1 >= order_id2


# Parametrized tests for comprehensive validation
class TestDomainObjectsParametrized:
    """Parametrized tests for domain objects."""

    @pytest.mark.parametrize(
        "symbol_str,expected",
        [
            ("tBTCUSD", "tBTCUSD"),
            ("tETHUSD", "tETHUSD"),
            ("tPNKUSD", "tPNKUSD"),
            ("fBTCUSD", "fBTCUSD"),
        ],
    )
    def test_valid_symbols(self, symbol_str, expected):
        """Test various valid symbol formats."""
        symbol = Symbol(symbol_str)
        assert str(symbol) == expected

    @pytest.mark.parametrize(
        "price_input,expected_decimal",
        [
            ("50000.50", Decimal("50000.50")),
            (50000, Decimal("50000")),
            (50000.50, Decimal("50000.50")),
            (Decimal("50000.50"), Decimal("50000.50")),
        ],
    )
    def test_price_input_types(self, price_input, expected_decimal):
        """Test price creation from various input types."""
        price = Price(price_input)
        assert price.value == expected_decimal

    @pytest.mark.parametrize(
        "amount_input,expected_decimal",
        [
            ("1.5", Decimal("1.5")),
            (1.5, Decimal("1.5")),
            (Decimal("1.5"), Decimal("1.5")),
        ],
    )
    def test_amount_input_types(self, amount_input, expected_decimal):
        """Test amount creation from various input types."""
        amount = Amount(amount_input)
        assert amount.value == expected_decimal

    @pytest.mark.parametrize(
        "order_id_input,expected_int",
        [
            ("12345678", 12345678),
            (12345678, 12345678),
            ("99999999", 99999999),
            (99999999, 99999999),
        ],
    )
    def test_order_id_input_types(self, order_id_input, expected_int):
        """Test order ID creation from various input types."""
        order_id = OrderId(order_id_input)
        assert order_id.value == expected_int
