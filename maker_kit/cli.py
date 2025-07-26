"""
Command-line interface for Bitfinex CLI tool.

REFACTORED: Now uses focused components for argument parsing and command routing,
providing better separation of concerns and maintainability.
"""

from .cli.argument_parser import create_cli_parser
from .cli.command_router import create_command_router
from .utilities.console import print_error


def main():
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
            parser.parser.print_help()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1  # Exit with error code


if __name__ == "__main__":
    main() 