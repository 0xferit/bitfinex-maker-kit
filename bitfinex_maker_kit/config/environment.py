"""
Environment-specific configuration for Maker-Kit.

Handles different environment configurations (development, testing, production)
and provides utilities for loading configuration from various sources.
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .trading_config import TradingConfig


class Environment(Enum):
    """Environment types for configuration."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, env_str: str) -> "Environment":
        """Create Environment from string."""
        env_str = env_str.lower()
        for env in cls:
            if env.value == env_str:
                return env
        return cls.DEVELOPMENT  # Default fallback


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration settings."""

    environment: Environment
    debug_mode: bool
    log_level: str
    api_timeout: int
    websocket_timeout: int
    max_retries: int
    enable_console_output: bool
    dry_run_default: bool

    @classmethod
    def for_development(cls) -> "EnvironmentConfig":
        """Development environment configuration."""
        return cls(
            environment=Environment.DEVELOPMENT,
            debug_mode=True,
            log_level="DEBUG",
            api_timeout=30,
            websocket_timeout=60,
            max_retries=3,
            enable_console_output=True,
            dry_run_default=False,
        )

    @classmethod
    def for_testing(cls) -> "EnvironmentConfig":
        """Testing environment configuration."""
        return cls(
            environment=Environment.TESTING,
            debug_mode=True,
            log_level="DEBUG",
            api_timeout=5,
            websocket_timeout=10,
            max_retries=1,
            enable_console_output=False,
            dry_run_default=True,
        )

    @classmethod
    def for_production(cls) -> "EnvironmentConfig":
        """Production environment configuration."""
        return cls(
            environment=Environment.PRODUCTION,
            debug_mode=False,
            log_level="INFO",
            api_timeout=30,
            websocket_timeout=60,
            max_retries=3,
            enable_console_output=True,
            dry_run_default=False,
        )


def get_current_environment() -> Environment:
    """
    Get the current environment from environment variables.

    Returns:
        Current Environment enum value
    """
    env_str = os.getenv("MAKER_KIT_ENV", "development")
    return Environment.from_string(env_str)


def get_environment_config(environment: Environment | None = None) -> EnvironmentConfig:
    """
    Get configuration for the specified environment.

    Args:
        environment: Target environment (defaults to current)

    Returns:
        EnvironmentConfig for the specified environment
    """
    if environment is None:
        environment = get_current_environment()

    if environment == Environment.DEVELOPMENT:
        return EnvironmentConfig.for_development()
    elif environment == Environment.TESTING:
        return EnvironmentConfig.for_testing()
    elif environment == Environment.PRODUCTION:
        return EnvironmentConfig.for_production()
    else:
        # Fallback to development
        return EnvironmentConfig.for_development()


def load_config_from_file(file_path: str) -> dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        file_path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with open(file_path) as f:
        config: dict[str, Any] = json.load(f)

    return config


def create_trading_config_for_environment(
    environment: Environment | None = None,
    config_file: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> TradingConfig:
    """
    Create a TradingConfig for the specified environment.

    Args:
        environment: Target environment (defaults to current)
        config_file: Optional configuration file path
        overrides: Optional configuration overrides

    Returns:
        Configured TradingConfig instance
    """
    if environment is None:
        environment = get_current_environment()

    # Get base environment config
    env_config = get_environment_config(environment)

    # Start with base trading config
    if environment == Environment.TESTING:
        trading_config = TradingConfig.for_testing()
    elif environment == Environment.PRODUCTION:
        trading_config = TradingConfig.for_production()
    else:
        trading_config = TradingConfig()

    # Apply environment-specific settings
    trading_config.log_level = env_config.log_level
    trading_config.api_timeout_seconds = env_config.api_timeout
    trading_config.websocket_timeout_seconds = env_config.websocket_timeout
    trading_config.max_retries = env_config.max_retries
    trading_config.enable_console_output = env_config.enable_console_output
    trading_config.dry_run_mode = env_config.dry_run_default

    # Load from file if specified
    if config_file and os.path.exists(config_file):
        try:
            file_config = load_config_from_file(config_file)
            for key, value in file_config.items():
                if hasattr(trading_config, key):
                    setattr(trading_config, key, value)
        except Exception as e:
            # Log warning but continue with default config
            print(f"Warning: Could not load config file {config_file}: {e}")

    # Apply overrides
    if overrides:
        for key, value in overrides.items():
            if hasattr(trading_config, key):
                setattr(trading_config, key, value)

    return trading_config


def get_default_config_paths() -> dict[str, str]:
    """
    Get default configuration file paths for different environments.

    Returns:
        Dictionary mapping environment names to config file paths
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return {
        "development": os.path.join(base_dir, "config", "development.json"),
        "testing": os.path.join(base_dir, "config", "testing.json"),
        "production": os.path.join(base_dir, "config", "production.json"),
    }


def save_config_to_file(config: TradingConfig, file_path: str) -> None:
    """
    Save configuration to a JSON file.

    Args:
        config: TradingConfig to save
        file_path: Target file path
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    config_dict = config.to_dict()

    with open(file_path, "w") as f:
        json.dump(config_dict, f, indent=2, sort_keys=True)


def validate_environment_setup() -> dict[str, Any]:
    """
    Validate that the environment is properly set up.

    Returns:
        Dictionary with validation results
    """
    results: dict[str, Any] = {
        "environment": get_current_environment().value,
        "credentials_available": False,
        "config_file_exists": False,
        "warnings": [],
        "errors": [],
    }

    # Check for API credentials
    api_key = os.getenv("BFX_API_KEY")
    api_secret = os.getenv("BFX_API_SECRET")

    if api_key and api_secret:
        results["credentials_available"] = True
    else:
        if isinstance(results["errors"], list):
            results["errors"].append("API credentials not found in environment variables")

    # Check for config file
    env = get_current_environment()
    config_paths = get_default_config_paths()
    config_path = config_paths.get(env.value)

    if config_path and os.path.exists(config_path):
        results["config_file_exists"] = True
        results["config_file_path"] = config_path
    else:
        if isinstance(results["warnings"], list):
            results["warnings"].append(f"No config file found at {config_path}")

    # Environment-specific validations
    if (
        env == Environment.PRODUCTION
        and os.getenv("MAKER_KIT_DRY_RUN", "").lower()
        in [
            "true",
            "1",
            "yes",
        ]
        and isinstance(results["warnings"], list)
    ):
        results["warnings"].append("Dry run mode enabled in production environment")

    return results
