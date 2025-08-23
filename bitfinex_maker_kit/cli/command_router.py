"""
Command routing for Maker-Kit CLI.

Handles routing parsed arguments to appropriate command implementations,
separated from argument parsing for better maintainability.
"""

import argparse
from collections.abc import Callable

from ..commands import (
    cancel_command,
    fill_spread_command,
    list_command,
    market_make_command,
    monitor_command,
    put_command,
    test_command,
    update_command,
    wallet_command,
)


class CommandRouter:
    """
    Routes parsed CLI arguments to appropriate command implementations.

    Provides clean separation between argument parsing and command execution,
    making the system easier to test and maintain.
    """

    def __init__(self) -> None:
        """Initialize command router with command mappings."""
        self.command_map: dict[str, Callable] = {
            "test": self._route_test,
            "wallet": self._route_wallet,
            "cancel": self._route_cancel,
            "put": self._route_put,
            "update": self._route_update,
            "list": self._route_list,
            "market-make": self._route_market_make,
            "fill-spread": self._route_fill_spread,
            "monitor": self._route_monitor,
        }

    def route_command(self, args: argparse.Namespace) -> None:
        """
        Route parsed arguments to the appropriate command.

        Args:
            args: Parsed command line arguments

        Raises:
            ValueError: If command is not recognized
        """
        if not args.command:
            raise ValueError("No command specified")

        if args.command not in self.command_map:
            raise ValueError(f"Unknown command: {args.command}")

        # Route to the appropriate command handler
        handler = self.command_map[args.command]
        handler(args)

    def _route_test(self, args: argparse.Namespace) -> None:
        """Route test command."""
        test_command()

    def _route_wallet(self, args: argparse.Namespace) -> None:
        """Route wallet command."""
        wallet_command()

    def _route_cancel(self, args: argparse.Namespace) -> None:
        """Route cancel command."""
        cancel_command(
            args.order_id,
            args.size,
            args.direction,
            args.symbol,
            args.price_below,
            args.price_above,
            args.dry_run,
            args.yes,
            args.all,
        )

    def _route_put(self, args: argparse.Namespace) -> None:
        """Route put command."""
        put_command(args.side, args.amount, args.price, args.symbol, args.dry_run, args.yes)

    def _route_update(self, args: argparse.Namespace) -> None:
        """Route update command."""
        update_command(
            args.order_id,
            args.price,
            args.amount,
            args.delta,
            args.filter_size,
            args.filter_direction,
            args.filter_symbol,
            args.dry_run,
            args.yes,
            args.use_cancel_recreate,
        )

    def _route_list(self, args: argparse.Namespace) -> None:
        """Route list command."""
        list_command(args.symbol, args.summary)

    def _route_market_make(self, args: argparse.Namespace) -> None:
        """Route market-make command."""
        market_make_command(
            args.symbol,
            args.center,
            args.levels,
            args.spread,
            args.size,
            args.dry_run,
            args.buy_only,
            args.sell_only,
            args.ignore_validation,
            args.yes,
        )

    def _route_fill_spread(self, args: argparse.Namespace) -> None:
        """Route fill-spread command."""
        fill_spread_command(
            args.symbol, args.target_spread, args.size, args.center, args.dry_run, args.yes
        )

    def _route_monitor(self, args: argparse.Namespace) -> None:
        """Route monitor command."""
        monitor_command(args.symbol, args.levels)

    def get_available_commands(self) -> list[str]:
        """Get list of available commands."""
        return list(self.command_map.keys())


def create_command_router() -> CommandRouter:
    """
    Factory function to create command router.

    Returns:
        Configured CommandRouter instance
    """
    return CommandRouter()
