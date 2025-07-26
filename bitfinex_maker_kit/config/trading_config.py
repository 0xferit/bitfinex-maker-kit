"""
Trading configuration for Maker-Kit.

Centralizes all trading-related configuration including defaults,
validation rules, and API settings.
"""

import contextlib
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..domain.amount import Amount
from ..domain.symbol import Symbol
from ..utilities.constants import (
    DEFAULT_LEVELS,
    DEFAULT_ORDER_SIZE,
    DEFAULT_SPREAD_PCT,
    DEFAULT_SYMBOL,
    MIN_ORDER_SPACING_PCT,
    POST_ONLY_FLAG,
    REPLENISH_INTERVAL_SECONDS,
)


@dataclass
class TradingConfig:
    """
    Centralized trading configuration.

    Contains all trading parameters, validation rules, and API settings
    with environment-based overrides and validation.
    """

    # Default Trading Parameters
    default_symbol: str = DEFAULT_SYMBOL
    default_levels: int = DEFAULT_LEVELS
    default_spread_pct: float = DEFAULT_SPREAD_PCT
    default_order_size: float = DEFAULT_ORDER_SIZE

    # API Configuration
    post_only_flag: int = POST_ONLY_FLAG
    api_timeout_seconds: int = 30
    max_retries: int = 3

    # Validation Rules
    min_order_spacing_pct: float = MIN_ORDER_SPACING_PCT
    max_levels: int = 20
    min_levels: int = 1
    max_spread_pct: float = 50.0
    min_spread_pct: float = 0.01
    max_order_size: float = 1000000.0
    min_order_size: float = 0.001

    # Market Making Settings
    replenish_interval_seconds: int = REPLENISH_INTERVAL_SECONDS
    max_center_price_deviation_pct: float = 10.0
    enable_auto_adjustment: bool = True
    partial_fill_threshold_pct: float = 50.0

    # WebSocket Settings
    websocket_timeout_seconds: int = 60
    websocket_ping_interval: int = 30
    websocket_max_reconnect_attempts: int = 5

    # Logging and Output
    log_level: str = "INFO"
    enable_console_output: bool = True
    enable_order_preview: bool = True

    # Safety Settings
    enable_post_only_enforcement: bool = True
    enable_order_validation: bool = True
    enable_balance_checks: bool = True
    dry_run_mode: bool = False

    # Environment Overrides
    environment_overrides: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_configuration()
        self._apply_environment_overrides()

    def _validate_configuration(self) -> None:
        """Validate all configuration parameters."""
        # Validate levels
        if not self.min_levels <= self.default_levels <= self.max_levels:
            raise ValueError(
                f"Default levels {self.default_levels} must be between {self.min_levels} and {self.max_levels}"
            )

        # Validate spread
        if not self.min_spread_pct <= self.default_spread_pct <= self.max_spread_pct:
            raise ValueError(
                f"Default spread {self.default_spread_pct}% must be between {self.min_spread_pct}% and {self.max_spread_pct}%"
            )

        # Validate order size
        if not self.min_order_size <= self.default_order_size <= self.max_order_size:
            raise ValueError(
                f"Default order size {self.default_order_size} must be between {self.min_order_size} and {self.max_order_size}"
            )

        # Validate symbol format
        if not self.default_symbol.startswith("t"):
            raise ValueError(f"Default symbol {self.default_symbol} must start with 't'")

        # Validate timeouts
        if self.api_timeout_seconds <= 0:
            raise ValueError("API timeout must be positive")

        if self.websocket_timeout_seconds <= 0:
            raise ValueError("WebSocket timeout must be positive")

        # Validate safety settings
        if not self.enable_post_only_enforcement:
            raise ValueError("POST_ONLY enforcement cannot be disabled for safety")

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides."""
        # API timeout
        if timeout := os.getenv("MAKER_KIT_API_TIMEOUT"):
            with contextlib.suppress(ValueError):
                self.api_timeout_seconds = int(timeout)

        # Log level
        if (log_level := os.getenv("MAKER_KIT_LOG_LEVEL")) and log_level.upper() in [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]:
            self.log_level = log_level.upper()

        # Dry run mode
        if dry_run := os.getenv("MAKER_KIT_DRY_RUN"):
            self.dry_run_mode = dry_run.lower() in ["true", "1", "yes", "on"]

        # Default symbol
        if (symbol := os.getenv("MAKER_KIT_DEFAULT_SYMBOL")) and symbol.startswith("t"):
            self.default_symbol = symbol

        # Apply custom overrides
        for key, value in self.environment_overrides.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_default_symbol(self) -> Symbol:
        """Get the default symbol as a domain object."""
        return Symbol(self.default_symbol)

    def get_default_amount(self) -> Amount:
        """Get the default order size as a domain object."""
        return Amount(Decimal(str(self.default_order_size)))

    def validate_levels(self, levels: int) -> bool:
        """Validate if levels parameter is within allowed range."""
        return self.min_levels <= levels <= self.max_levels

    def validate_spread(self, spread_pct: float) -> bool:
        """Validate if spread percentage is within allowed range."""
        return self.min_spread_pct <= spread_pct <= self.max_spread_pct

    def validate_order_size(self, size: float) -> bool:
        """Validate if order size is within allowed range."""
        return self.min_order_size <= size <= self.max_order_size

    def get_api_config(self) -> dict[str, Any]:
        """Get API-specific configuration."""
        return {
            "timeout": self.api_timeout_seconds,
            "max_retries": self.max_retries,
            "post_only_flag": self.post_only_flag,
            "enable_validation": self.enable_order_validation,
        }

    def get_websocket_config(self) -> dict[str, Any]:
        """Get WebSocket-specific configuration."""
        return {
            "timeout": self.websocket_timeout_seconds,
            "ping_interval": self.websocket_ping_interval,
            "max_reconnect_attempts": self.websocket_max_reconnect_attempts,
        }

    def get_market_making_config(self) -> dict[str, Any]:
        """Get market making specific configuration."""
        return {
            "replenish_interval": self.replenish_interval_seconds,
            "max_center_deviation_pct": self.max_center_price_deviation_pct,
            "enable_auto_adjustment": self.enable_auto_adjustment,
            "partial_fill_threshold_pct": self.partial_fill_threshold_pct,
            "min_order_spacing_pct": self.min_order_spacing_pct,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "default_symbol": self.default_symbol,
            "default_levels": self.default_levels,
            "default_spread_pct": self.default_spread_pct,
            "default_order_size": self.default_order_size,
            "post_only_flag": self.post_only_flag,
            "api_timeout": self.api_timeout_seconds,
            "max_retries": self.max_retries,
            "log_level": self.log_level,
            "dry_run_mode": self.dry_run_mode,
            "enable_post_only_enforcement": self.enable_post_only_enforcement,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "TradingConfig":
        """Create configuration from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})

    @classmethod
    def for_testing(cls) -> "TradingConfig":
        """Create configuration optimized for testing."""
        return cls(
            dry_run_mode=True,
            api_timeout_seconds=5,
            websocket_timeout_seconds=10,
            max_retries=1,
            enable_console_output=False,
            log_level="DEBUG",
        )

    @classmethod
    def for_production(cls) -> "TradingConfig":
        """Create configuration optimized for production."""
        return cls(
            dry_run_mode=False,
            api_timeout_seconds=30,
            websocket_timeout_seconds=60,
            max_retries=3,
            enable_console_output=True,
            log_level="INFO",
        )
