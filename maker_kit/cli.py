"""
Command-line interface for Bitfinex CLI tool.
"""

import argparse
from typing import Optional

from .utilities.constants import DEFAULT_SYMBOL, DEFAULT_LEVELS, DEFAULT_SPREAD_PCT, DEFAULT_ORDER_SIZE
from .commands import (
    test_command, wallet_command, clear_command, cancel_command, put_command, update_command,
    list_command, market_make_command, auto_market_make_command, fill_spread_command
)
from .utilities.console import print_error


def main():
    parser = argparse.ArgumentParser(description="Bitfinex API CLI Tool (using official library)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Test subcommand
    parser_test = subparsers.add_parser("test", help="Test REST API and WebSocket connections")
    
    # Wallet subcommand
    parser_wallet = subparsers.add_parser("wallet", help="Show wallet balances")
    
    # Clear subcommand
    parser_clear = subparsers.add_parser("clear", help="Clear all orders on PNK-USD pair")
    
    # Cancel subcommand
    parser_cancel = subparsers.add_parser("cancel", help="Cancel orders by ID or by criteria (size, direction, price)")
    parser_cancel.add_argument("order_id", type=int, nargs='?', help="Order ID to cancel (required if not using criteria filters)")
    parser_cancel.add_argument("--size", type=float, help="Cancel all orders with this size")
    parser_cancel.add_argument("--direction", choices=['buy', 'sell'], help="Filter by order direction (buy/sell)")
    parser_cancel.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Filter by symbol (default: {DEFAULT_SYMBOL})")
    parser_cancel.add_argument("--price-below", type=float, help="Cancel orders with price below this value")
    parser_cancel.add_argument("--price-above", type=float, help="Cancel orders with price above this value")
    parser_cancel.add_argument("--dry-run", action="store_true", help="Show matching orders without cancelling them")
    parser_cancel.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    # Put subcommand
    parser_put = subparsers.add_parser("put", help="Place a single order")
    parser_put.add_argument("side", choices=['buy', 'sell'], help="Order side: buy or sell")
    parser_put.add_argument("amount", type=float, help="Order amount (quantity)")
    parser_put.add_argument("price", nargs='?', help="Order price (omit for market order)")
    parser_put.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Trading symbol (default: {DEFAULT_SYMBOL})")
    parser_put.add_argument("--dry-run", action="store_true", help="Show order details without placing it")
    parser_put.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    # Update subcommand
    parser_update = subparsers.add_parser("update", help="Update existing orders atomically")
    parser_update.add_argument("order_id", type=int, nargs='?', help="Order ID to update (required if not using filter criteria)")
    
    # Update parameters
    parser_update.add_argument("--price", type=float, help="New price for the order(s)")
    parser_update.add_argument("--amount", type=float, help="New absolute amount for the order(s)")
    parser_update.add_argument("--delta", type=float, help="Amount to add/subtract from current amount (use + or - values)")
    
    # Filter criteria for bulk updates
    parser_update.add_argument("--filter-size", type=float, help="Update all orders with this size")
    parser_update.add_argument("--filter-direction", choices=['buy', 'sell'], help="Filter by order direction (buy/sell)")
    parser_update.add_argument("--filter-symbol", default=None, help="Filter by symbol (e.g., tPNKUSD)")
    
    parser_update.add_argument("--dry-run", action="store_true", help="Show update details without modifying orders")
    parser_update.add_argument("--use-cancel-recreate", action="store_true", help="Use cancel-and-recreate method instead of WebSocket atomic update (riskier)")
    parser_update.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    # List subcommand
    parser_list = subparsers.add_parser("list", help="List active orders")
    parser_list.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Filter orders by symbol (default: {DEFAULT_SYMBOL})")
    parser_list.add_argument("--summary", action="store_true", help="Show summary statistics instead of detailed orders")
    
    # Market-make subcommand
    parser_mm = subparsers.add_parser("market-make", help="Create staircase market making orders")
    parser_mm.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Trading symbol (default: {DEFAULT_SYMBOL})")
    parser_mm.add_argument("--center", help="Center price (numeric value, 'mid-range' for mid-price, or omit for suggestions)")
    parser_mm.add_argument("--levels", type=int, default=DEFAULT_LEVELS, help=f"Number of price levels on each side (default: {DEFAULT_LEVELS})")
    parser_mm.add_argument("--spread", type=float, default=DEFAULT_SPREAD_PCT, help=f"Spread percentage per level (default: {DEFAULT_SPREAD_PCT}%%)")
    parser_mm.add_argument("--size", type=float, default=DEFAULT_ORDER_SIZE, help=f"Order size for each level (default: {DEFAULT_ORDER_SIZE})")
    parser_mm.add_argument("--dry-run", action="store_true", help="Show orders without placing them")
    parser_mm.add_argument("--ignore-validation", action="store_true", help="Ignore center price validation (allows orders outside bid-ask spread)")
    parser_mm.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    # Mutually exclusive group for side selection
    side_group = parser_mm.add_mutually_exclusive_group()
    side_group.add_argument("--buy-only", action="store_true", help="Place only buy orders below center price")
    side_group.add_argument("--sell-only", action="store_true", help="Place only sell orders above center price")
    
    # Auto-market-make subcommand
    parser_amm = subparsers.add_parser("auto-market-make", help="Automated market making with dynamic center adjustment")
    parser_amm.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Trading symbol (default: {DEFAULT_SYMBOL})")
    parser_amm.add_argument("--center", required=True, help="Initial center price (numeric value or 'mid-range' for mid-price)")
    parser_amm.add_argument("--levels", type=int, default=DEFAULT_LEVELS, help=f"Number of price levels on each side (default: {DEFAULT_LEVELS})")
    parser_amm.add_argument("--spread", type=float, default=DEFAULT_SPREAD_PCT, help=f"Spread percentage per level (default: {DEFAULT_SPREAD_PCT}%%)")
    parser_amm.add_argument("--size", type=float, default=DEFAULT_ORDER_SIZE, help=f"Order size for each level (default: {DEFAULT_ORDER_SIZE})")
    parser_amm.add_argument("--test-only", action="store_true", help="Place orders and exit without WebSocket monitoring (for testing)")
    parser_amm.add_argument("--ignore-validation", action="store_true", help="Ignore center price validation (allows orders outside bid-ask spread)")
    parser_amm.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    # Mutually exclusive group for side selection in auto market maker
    auto_side_group = parser_amm.add_mutually_exclusive_group()
    auto_side_group.add_argument("--buy-only", action="store_true", help="Place only buy orders below center price")
    auto_side_group.add_argument("--sell-only", action="store_true", help="Place only sell orders above center price")
    
    # Fill-spread subcommand
    parser_fill = subparsers.add_parser("fill-spread", help="Fill the bid-ask spread gap with equally spaced orders")
    parser_fill.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Trading symbol (default: {DEFAULT_SYMBOL})")
    parser_fill.add_argument("--target-spread", type=float, required=True, help="Target maximum spread percentage (final spread will be less than this)")
    parser_fill.add_argument("--size", type=float, required=True, help="Order size for each fill order")
    parser_fill.add_argument("--center", help="Center price for orders (numeric price or 'mid-range' to use mid-price)")
    parser_fill.add_argument("--dry-run", action="store_true", help="Show orders without placing them")
    parser_fill.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    # Route commands to their respective functions
    def run_command():
        if args.command == "test":
            test_command()
        elif args.command == "wallet":
            wallet_command()
        elif args.command == "clear":
            clear_command()
        elif args.command == "cancel":
            cancel_command(args.order_id, args.size, args.direction, args.symbol, 
                         args.price_below, args.price_above, args.dry_run, args.yes)
        elif args.command == "put":
            put_command(args.side, args.amount, args.price, args.symbol, args.dry_run, args.yes)
        elif args.command == "update":
            update_command(args.order_id, args.price, args.amount, args.delta,
                         args.filter_size, args.filter_direction, args.filter_symbol, args.dry_run, args.yes, args.use_cancel_recreate)
        elif args.command == "list":
            list_command(args.symbol, args.summary)
        elif args.command == "market-make":
            market_make_command(args.symbol, args.center, args.levels, args.spread, 
                              args.size, args.dry_run, args.buy_only, args.sell_only,
                              args.ignore_validation, args.yes)
        elif args.command == "auto-market-make":
            auto_market_make_command(args.symbol, args.center, args.levels, args.spread, 
                                   args.size, args.buy_only, args.sell_only, args.test_only,
                                   args.ignore_validation, args.yes)
        elif args.command == "fill-spread":
            fill_spread_command(args.symbol, args.target_spread, args.size, args.center, args.dry_run, args.yes)
        else:
            parser.print_help()
    
    # Run the command
    try:
        run_command()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1  # Exit with error code


if __name__ == "__main__":
    main() 