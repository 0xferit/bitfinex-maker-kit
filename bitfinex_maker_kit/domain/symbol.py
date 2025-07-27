"""
Symbol value object for trading pairs.

Provides type-safe symbol representation with validation for Bitfinex format.
"""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Symbol:
    """
    Immutable trading symbol value object with Bitfinex format validation.

    Ensures symbols follow Bitfinex naming conventions (e.g., tBTCUSD, tETHUSD)
    and provides utilities for symbol manipulation and validation.
    """

    value: str

    # Bitfinex symbol pattern: starts with 't' or 'f', followed by base and quote currencies
    _BITFINEX_PATTERN: ClassVar = re.compile(r"^[tf][A-Z]{3,5}[A-Z]{3,4}$")

    # Paper trading test symbols (special case for testing environments)
    _PAPER_TRADING_SYMBOLS: ClassVar = {"tTESTBTCTESTUSD", "tTESTBTCTESTUSDT"}

    def __post_init__(self) -> None:
        """Validate symbol after initialization."""
        if not self.value:
            raise ValueError("Symbol cannot be empty")

        if not isinstance(self.value, str):
            raise ValueError(f"Symbol must be a string, got: {type(self.value)}")

        # Allow paper trading test symbols (bypass normal validation)
        if self.value in self._PAPER_TRADING_SYMBOLS:
            return

        # Validate Bitfinex format for regular symbols
        if not self._BITFINEX_PATTERN.match(self.value):
            raise ValueError(
                f"Invalid Bitfinex symbol format: {self.value}. "
                f"Expected format: [t|f]<BASE><QUOTE> (e.g., tBTCUSD, fBTCUSD, tETHUSD) "
                f"or paper trading symbols: {', '.join(self._PAPER_TRADING_SYMBOLS)}"
            )

    @classmethod
    def from_currencies(cls, base: str, quote: str) -> "Symbol":
        """
        Create Symbol from base and quote currencies.

        Args:
            base: Base currency (e.g., 'BTC', 'ETH')
            quote: Quote currency (e.g., 'USD', 'EUR')
        """
        if not base or not quote:
            raise ValueError("Base and quote currencies cannot be empty")

        # Ensure uppercase
        base = base.upper().strip()
        quote = quote.upper().strip()

        symbol_value = f"t{base}{quote}"
        return cls(symbol_value)

    def get_base_currency(self) -> str:
        """Extract base currency from symbol (e.g., 'BTC' from 'tBTCUSD')."""
        # Handle paper trading test symbols specially
        if self.value == "tTESTBTCTESTUSD" or self.value == "tTESTBTCTESTUSDT":
            return "TESTBTC"

        # Remove 't' prefix and extract base currency
        # Most symbols are 6-7 chars: t + 3-4 base + 3 quote
        # Some special cases exist, so we need to handle various lengths
        symbol_without_t = self.value[1:]  # Remove 't'

        # Common patterns:
        # - 6 chars: 3 base + 3 quote (e.g., BTCUSD)
        # - 7 chars: 4 base + 3 quote (e.g., ETHRUSD) or 3 base + 4 quote (e.g., BTCEUR)
        # We'll assume 3-char quote currencies are most common (USD, EUR, GBP)

        if len(symbol_without_t) == 6:
            return symbol_without_t[:3]
        elif len(symbol_without_t) == 7:
            # Try common 3-char quote currencies first
            if symbol_without_t.endswith(("USD", "EUR", "GBP", "JPY", "CHF")):
                return symbol_without_t[:-3]
            else:
                # Assume 4-char base, 3-char quote
                return symbol_without_t[:4]
        elif len(symbol_without_t) == 8:
            # 4-char base + 4-char quote, or 5-char base + 3-char quote
            if symbol_without_t.endswith(("USD", "EUR", "GBP", "JPY", "CHF")):
                return symbol_without_t[:-3]
            else:
                return symbol_without_t[:4]
        else:
            # Fallback: assume 3-char quote
            return symbol_without_t[:-3]

    def get_quote_currency(self) -> str:
        """Extract quote currency from symbol (e.g., 'USD' from 'tBTCUSD')."""
        # Handle paper trading test symbols specially
        if self.value == "tTESTBTCTESTUSD":
            return "TESTUSD"
        elif self.value == "tTESTBTCTESTUSDT":
            return "TESTUSDT"

        symbol_without_t = self.value[1:]  # Remove 't'
        base = self.get_base_currency()
        return symbol_without_t[len(base) :]

    def get_currencies(self) -> tuple[str, str]:
        """Get both base and quote currencies as a tuple."""
        return (self.get_base_currency(), self.get_quote_currency())

    def is_crypto_pair(self) -> bool:
        """Check if this is a crypto-to-crypto pair (not fiat)."""
        quote = self.get_quote_currency()
        fiat_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"}
        return quote not in fiat_currencies

    def is_fiat_pair(self) -> bool:
        """Check if this is a crypto-to-fiat pair."""
        return not self.is_crypto_pair()

    def is_stablecoin_pair(self) -> bool:
        """Check if quote currency is a stablecoin."""
        quote = self.get_quote_currency()
        stablecoins = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP"}
        return quote in stablecoins

    def to_display_format(self) -> str:
        """Convert to human-readable format (e.g., 'BTC/USD')."""
        base, quote = self.get_currencies()
        return f"{base}/{quote}"

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, Symbol):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash(self.value)

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Symbol('{self.value}')"
