"""
Property-based tests for domain objects.

Uses Hypothesis to generate test cases and verify mathematical properties,
invariants, and edge cases for domain value objects.
"""

from decimal import Decimal

import pytest
from hypothesis import assume, example, given
from hypothesis import strategies as st
from hypothesis.stateful import Bundle, RuleBasedStateMachine, initialize, invariant, rule

from bitfinex_maker_kit.domain.amount import Amount
from bitfinex_maker_kit.domain.order_id import OrderId
from bitfinex_maker_kit.domain.price import Price
from bitfinex_maker_kit.domain.symbol import Symbol


# Custom strategies for domain objects
@st.composite
def valid_symbols(draw):
    """Generate valid trading symbols."""
    base_currencies = ["BTC", "ETH", "PNK", "LTC", "XRP", "ADA", "DOT", "SOL"]
    quote_currencies = ["USD", "EUR", "GBP", "JPY", "BTC", "ETH"]
    prefixes = ["t", "f"]

    prefix = draw(st.sampled_from(prefixes))
    base = draw(st.sampled_from(base_currencies))
    quote = draw(st.sampled_from(quote_currencies))

    # Ensure base != quote for valid pairs
    assume(base != quote)

    return f"{prefix}{base}{quote}"


@st.composite
def valid_prices(draw):
    """Generate valid price values."""
    # Generate positive prices with various scales
    price_strategies = st.one_of(
        st.decimals(min_value=Decimal("0.00001"), max_value=Decimal("0.1"), places=8),
        st.decimals(min_value=Decimal("0.1"), max_value=Decimal("1000"), places=6),
        st.decimals(min_value=Decimal("1000"), max_value=Decimal("100000"), places=2),
        st.decimals(min_value=Decimal("100000"), max_value=Decimal("10000000"), places=2),
    )

    price_decimal = draw(price_strategies)
    assume(price_decimal > 0)

    return str(price_decimal)


@st.composite
def valid_amounts(draw):
    """Generate valid amount values (positive only)."""
    # Generate amounts with various scales
    amount_strategies = st.one_of(
        st.decimals(min_value=Decimal("0.00000001"), max_value=Decimal("1000"), places=8),
        st.decimals(min_value=Decimal("0.000001"), max_value=Decimal("100"), places=6),
        st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("10"), places=4),
    )

    amount_decimal = draw(amount_strategies)
    assume(amount_decimal > 0)  # Amounts must be positive

    return str(amount_decimal)


@st.composite
def valid_order_ids(draw):
    """Generate valid order IDs."""
    return draw(st.integers(min_value=10000000, max_value=99999999))


class TestSymbolProperties:
    """Property-based tests for Symbol domain object."""

    @given(valid_symbols())
    def test_symbol_string_roundtrip(self, symbol_str):
        """Test that symbol string conversion is consistent."""
        symbol = Symbol(symbol_str)
        assert str(symbol) == symbol_str

    @given(valid_symbols())
    def test_symbol_equality_reflexive(self, symbol_str):
        """Test that symbol equality is reflexive."""
        symbol1 = Symbol(symbol_str)
        symbol2 = Symbol(symbol_str)
        assert symbol1 == symbol2
        assert symbol2 == symbol1

    @given(valid_symbols(), valid_symbols())
    def test_symbol_equality_consistency(self, symbol_str1, symbol_str2):
        """Test symbol equality consistency."""
        symbol1 = Symbol(symbol_str1)
        symbol2 = Symbol(symbol_str2)

        if symbol_str1 == symbol_str2:
            assert symbol1 == symbol2
            assert hash(symbol1) == hash(symbol2)
        else:
            assert symbol1 != symbol2

    @given(valid_symbols())
    def test_symbol_hash_consistency(self, symbol_str):
        """Test that equal symbols have equal hashes."""
        symbol1 = Symbol(symbol_str)
        symbol2 = Symbol(symbol_str)
        assert hash(symbol1) == hash(symbol2)

    @given(st.text())
    def test_symbol_validation_properties(self, invalid_symbol):
        """Test symbol validation rejects invalid inputs."""
        # Filter out valid symbols to test only invalid ones
        valid_prefixes = ["t", "f"]
        if len(invalid_symbol) >= 7 and invalid_symbol[0] in valid_prefixes:
            # Skip potentially valid symbols
            assume(False)

        with pytest.raises((ValueError, TypeError)):
            Symbol(invalid_symbol)


class TestPriceProperties:
    """Property-based tests for Price domain object."""

    @given(valid_prices())
    def test_price_always_positive(self, price_str):
        """Test that all valid prices are positive."""
        price = Price(price_str)
        assert price.value > 0

    @given(valid_prices())
    def test_price_decimal_precision(self, price_str):
        """Test price maintains decimal precision."""
        original_decimal = Decimal(price_str)
        price = Price(price_str)
        assert price.value == original_decimal

    @given(valid_prices(), valid_prices())
    def test_price_addition_commutative(self, price1_str, price2_str):
        """Test that price addition is commutative."""
        price1 = Price(price1_str)
        price2 = Price(price2_str)

        result1 = price1 + price2
        result2 = price2 + price1

        assert result1.value == result2.value

    @given(valid_prices(), valid_prices(), valid_prices())
    def test_price_addition_associative(self, price1_str, price2_str, price3_str):
        """Test that price addition is associative."""
        price1 = Price(price1_str)
        price2 = Price(price2_str)
        price3 = Price(price3_str)

        result1 = (price1 + price2) + price3
        result2 = price1 + (price2 + price3)

        assert result1.value == result2.value

    @given(valid_prices())
    def test_price_comparison_reflexive(self, price_str):
        """Test that price comparison is reflexive."""
        price1 = Price(price_str)
        price2 = Price(price_str)

        assert price1 == price2
        assert price1 <= price2
        assert price1 >= price2
        assert not (price1 < price2)
        assert not (price1 > price2)

    @given(valid_prices(), valid_prices())
    def test_price_comparison_transitive(self, price1_str, price2_str):
        """Test price comparison transitivity."""
        price1 = Price(price1_str)
        price2 = Price(price2_str)

        # Generate third price based on comparison
        if price1.value < price2.value:
            price3_decimal = price2.value + Decimal("1.0")
        elif price1.value > price2.value:
            price3_decimal = (
                Decimal("0.01") if price1.value > Decimal("0.02") else price1.value + Decimal("1.0")
            )
        else:
            price3_decimal = price1.value + Decimal("1.0")

        price3 = Price(str(price3_decimal))

        # Test transitivity
        if price1 < price2 and price2 < price3:
            assert price1 < price3
        if price1 > price2 and price2 > price3:
            assert price1 > price3

    @given(valid_prices())
    @example("0.000001")  # Edge case: very small price
    @example("1000000.0")  # Edge case: very large price
    def test_price_multiplication_identity(self, price_str):
        """Test that multiplying by 1 returns equivalent price."""
        price = Price(price_str)
        result = price * Decimal("1")
        assert result.value == price.value

    @given(valid_prices())
    def test_price_string_conversion_consistency(self, price_str):
        """Test price to string conversion consistency."""
        price = Price(price_str)
        # Converting back should give equivalent value
        price2 = Price(str(price))
        assert price.value == price2.value


class TestAmountProperties:
    """Property-based tests for Amount domain object."""

    @given(valid_amounts())
    def test_amount_never_zero(self, amount_str):
        """Test that amounts are never zero."""
        amount = Amount(amount_str)
        assert amount.value != 0

    @given(valid_amounts())
    def test_amount_sign_operations(self, amount_str):
        """Test amount sign operations properties."""
        amount = Amount(amount_str)

        # Absolute value is always positive (returns self since all amounts are positive)
        abs_amount = amount.abs()
        assert abs_amount is amount
        assert abs_amount.value > 0

        # All amounts should be positive
        assert amount.is_positive()
        assert not amount.is_negative()

    @given(valid_amounts(), valid_amounts())
    def test_amount_addition_properties(self, amount1_str, amount2_str):
        """Test amount addition properties."""
        amount1 = Amount(amount1_str)
        amount2 = Amount(amount2_str)

        # Commutativity
        result1 = amount1 + amount2
        result2 = amount2 + amount1
        assert result1.value == result2.value

        # Addition should always result in positive amount
        assert result1.value > 0
        assert result2.value > 0

    @given(valid_amounts())
    def test_amount_multiplication_properties(self, amount_str):
        """Test amount multiplication properties."""
        amount = Amount(amount_str)

        # Multiplication by 1 preserves value
        identity_result = amount * Decimal("1")
        assert identity_result.value == amount.value

        # Multiplication by positive factor should result in positive amount
        factor = Decimal("2.5")
        result = amount * factor
        assert result.value > 0
        assert result.value == amount.value * factor

    @given(valid_amounts())
    def test_amount_is_positive_negative_consistency(self, amount_str):
        """Test amount sign checking consistency."""
        amount = Amount(amount_str)

        # All amounts should be positive
        assert amount.is_positive()
        assert not amount.is_negative()
        assert amount.value > 0


class TestOrderIdProperties:
    """Property-based tests for OrderId domain object."""

    @given(valid_order_ids())
    def test_order_id_always_positive(self, order_id_int):
        """Test that order IDs are always positive."""
        order_id = OrderId(order_id_int)
        assert order_id.value > 0

    @given(valid_order_ids())
    def test_order_id_string_conversion(self, order_id_int):
        """Test order ID string conversion."""
        order_id = OrderId(order_id_int)
        assert str(order_id) == str(order_id_int)

        # Can create from string representation
        order_id2 = OrderId(str(order_id_int))
        assert order_id.value == order_id2.value

    @given(valid_order_ids(), valid_order_ids())
    def test_order_id_comparison_consistency(self, id1, id2):
        """Test order ID comparison consistency."""
        order_id1 = OrderId(id1)
        order_id2 = OrderId(id2)

        if id1 == id2:
            assert order_id1 == order_id2
            assert hash(order_id1) == hash(order_id2)
        elif id1 < id2:
            assert order_id1 < order_id2
            assert order_id1 != order_id2
        else:
            assert order_id1 > order_id2
            assert order_id1 != order_id2

    @given(valid_order_ids())
    def test_order_id_hash_stability(self, order_id_int):
        """Test that order ID hash is stable."""
        order_id = OrderId(order_id_int)
        hash1 = hash(order_id)
        hash2 = hash(order_id)
        assert hash1 == hash2


class TestCrossObjectProperties:
    """Property-based tests for interactions between domain objects."""

    @given(valid_symbols(), valid_prices(), valid_amounts())
    def test_order_parameter_combination(self, symbol_str, price_str, amount_str):
        """Test valid combinations of order parameters."""
        symbol = Symbol(symbol_str)
        price = Price(price_str)
        amount = Amount(amount_str)

        # All objects should be valid
        assert str(symbol) == symbol_str
        assert price.value > 0
        assert amount.value > 0

        # Calculate order total
        total = price.value * amount.value
        assert total > 0

    @given(valid_prices(), valid_amounts())
    def test_price_amount_calculations(self, price_str, amount_str):
        """Test calculations involving price and amount."""
        price = Price(price_str)
        amount = Amount(amount_str)

        # Order value calculation
        order_value = price.value * amount.value
        assert order_value > 0

        # Average price calculation (simulate partial fills)
        if amount.value >= Decimal("0.001"):  # Avoid tiny amounts
            partial_amount = amount.value / Decimal("2")
            avg_price = (order_value / 2) / partial_amount
            assert avg_price > 0


# Stateful testing for domain object interactions
class DomainObjectStateMachine(RuleBasedStateMachine):
    """Stateful testing for domain object interactions."""

    symbols = Bundle("symbols")
    prices = Bundle("prices")
    amounts = Bundle("amounts")
    order_ids = Bundle("order_ids")

    @initialize()
    def setup(self):
        """Initialize state machine."""
        self.created_objects = {"symbols": [], "prices": [], "amounts": [], "order_ids": []}

    @rule(target=symbols, symbol_str=valid_symbols())
    def create_symbol(self, symbol_str):
        """Create a symbol and add to collection."""
        symbol = Symbol(symbol_str)
        self.created_objects["symbols"].append(symbol)
        return symbol

    @rule(target=prices, price_str=valid_prices())
    def create_price(self, price_str):
        """Create a price and add to collection."""
        price = Price(price_str)
        self.created_objects["prices"].append(price)
        return price

    @rule(target=amounts, amount_str=valid_amounts())
    def create_amount(self, amount_str):
        """Create an amount and add to collection."""
        amount = Amount(amount_str)
        self.created_objects["amounts"].append(amount)
        return amount

    @rule(target=order_ids, order_id=valid_order_ids())
    def create_order_id(self, order_id):
        """Create an order ID and add to collection."""
        oid = OrderId(order_id)
        self.created_objects["order_ids"].append(oid)
        return oid

    @rule(price1=prices, price2=prices)
    def test_price_arithmetic(self, price1, price2):
        """Test price arithmetic operations."""
        # Addition should always work
        result = price1 + price2
        assert result.value > 0
        assert result.value == price1.value + price2.value

        # Subtraction might go negative, but should be consistent
        if price1.value > price2.value:
            sub_result = price1 - price2
            assert sub_result.value == price1.value - price2.value

    @rule(amount1=amounts, amount2=amounts)
    def test_amount_arithmetic(self, amount1, amount2):
        """Test amount arithmetic operations."""
        # Addition
        add_result = amount1 + amount2
        assert add_result.value == amount1.value + amount2.value

        # Subtraction - only if result would be positive
        if amount1.value > amount2.value:
            sub_result = amount1 - amount2
            assert sub_result.value == amount1.value - amount2.value
        else:
            # Should raise ValueError for non-positive result
            with pytest.raises(ValueError, match="Subtraction would result in non-positive amount"):
                amount1 - amount2

    @rule(price=prices, amount=amounts)
    def test_order_calculations(self, price, amount):
        """Test order-related calculations."""
        # Calculate order value
        order_value = price.value * abs(amount.value)
        assert order_value > 0

        # Test fee calculations
        fee_rate = Decimal("0.001")  # 0.1% fee
        fee_amount = order_value * fee_rate
        total_cost = order_value + fee_amount
        assert total_cost > order_value

    @invariant()
    def all_objects_valid(self):
        """Invariant: all created objects remain valid."""
        for symbol in self.created_objects["symbols"]:
            assert len(str(symbol)) >= 7  # Minimum valid symbol length

        for price in self.created_objects["prices"]:
            assert price.value > 0

        for amount in self.created_objects["amounts"]:
            assert amount.value != 0

        for order_id in self.created_objects["order_ids"]:
            assert order_id.value > 0


# Test the stateful machine
TestDomainObjectStateMachine = DomainObjectStateMachine.TestCase


# Edge case testing with examples
class TestDomainEdgeCases:
    """Test domain objects with specific edge cases."""

    @given(valid_prices())
    @example("0.00000001")  # Minimum precision
    @example("99999999.99")  # Maximum reasonable price
    def test_price_extreme_values(self, price_str):
        """Test price with extreme but valid values."""
        price = Price(price_str)
        assert price.value > 0

        # Should be able to perform basic operations
        doubled = price * Decimal("2")
        assert doubled.value == price.value * 2

    @given(valid_amounts())
    @example("0.00000001")  # Minimum positive amount
    @example("999999.999999")  # Large positive amount
    def test_amount_extreme_values(self, amount_str):
        """Test amount with extreme values."""
        amount = Amount(amount_str)
        assert amount.value > 0
        assert amount.value != 0

    @given(valid_order_ids())
    @example(10000000)  # Minimum valid order ID
    @example(99999999)  # Maximum valid order ID
    def test_order_id_boundary_values(self, order_id_int):
        """Test order ID with boundary values."""
        order_id = OrderId(order_id_int)
        assert 10000000 <= order_id.value <= 99999999
