"""
CLI module for Maker-Kit.

Provides focused command-line interface components with proper
separation of concerns between argument parsing and command execution.
"""

from ..utilities.console import print_error
from .argument_parser import create_cli_parser
from .command_router import create_command_router


def main() -> int:
    """
    Main CLI entry point using focused components.

    Separates argument parsing from command routing for better organization.
    """
    # Create focused components
    parser = create_cli_parser()
    router = create_command_router()

    try:
        # Parse arguments
        args = parser.parse_args()

        # Route to appropriate command
        if args.command:
            router.route_command(args)
        else:
            parser.print_help()

    except Exception as e:
        print_error(f"Error: {e}")
        return 1

    return 0


__all__ = ["create_cli_parser", "create_command_router", "main"]
