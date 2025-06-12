"""
Command-line interface for Bitfinex CLI tool.
"""

import argparse
import asyncio
from typing import Optional

from .constants import DEFAULT_SYMBOL, DEFAULT_LEVELS, DEFAULT_SPREAD_PCT, DEFAULT_ORDER_SIZE
from .auth import test_api_connection
from .wallet import get_wallets
from .orders import list_orders, cancel_single_order, clear_orders, cancel_orders_by_criteria, put_order
from .market_making import market_make, fill_spread
from .market_data import suggest_price_centers, resolve_center_price
from .auto_market_maker import auto_market_make
from .utils import print_error


def main():
    parser = argparse.ArgumentParser(description="Bitfinex API CLI Tool (using official library)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Test subcommand
    parser_test = subparsers.add_parser("test", help="Test API connection")
    
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
    
    # Put subcommand
    parser_put = subparsers.add_parser("put", help="Place a single order")
    parser_put.add_argument("side", choices=['buy', 'sell'], help="Order side: buy or sell")
    parser_put.add_argument("amount", type=float, help="Order amount (quantity)")
    parser_put.add_argument("price", nargs='?', help="Order price (omit for market order)")
    parser_put.add_argument("--symbol", default=DEFAULT_SYMBOL, help=f"Trading symbol (default: {DEFAULT_SYMBOL})")
    parser_put.add_argument("--dry-run", action="store_true", help="Show order details without placing it")
    
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
    
    args = parser.parse_args()
    
    # Most commands are now synchronous, only async ones need special handling
    def run_command():
        if args.command == "test":
            test_api_connection()
        elif args.command == "wallet":
            get_wallets()
        elif args.command == "clear":
            clear_orders()
        elif args.command == "cancel":
            if args.order_id:
                # Cancel by order ID
                cancel_single_order(args.order_id)
            elif (args.size is not None or args.direction or args.symbol != DEFAULT_SYMBOL or 
                  args.price_below is not None or args.price_above is not None):
                # Cancel by criteria
                cancel_orders_by_criteria(args.size, args.direction, args.symbol, 
                                        args.price_below, args.price_above, args.dry_run)
            else:
                print_error("Must provide either order_id or criteria (--size, --direction, --symbol, --price-below, --price-above)")
                print("Use 'maker-kit cancel --help' for usage information")
        elif args.command == "put":
            put_order(args.symbol, args.side, args.amount, args.price, args.dry_run)
        elif args.command == "list":
            list_orders(args.symbol, args.summary)
        elif args.command == "market-make":
            # Determine side filter
            side_filter = None
            if args.buy_only:
                side_filter = "buy"
            elif args.sell_only:
                side_filter = "sell"
            
            if args.center:
                # Resolve center price from string input
                center_price = resolve_center_price(args.symbol, args.center)
                if center_price is None:
                    return  # Error already printed by resolve_center_price
                
                market_make(args.symbol, center_price, args.levels, args.spread, args.size, args.dry_run, side_filter, args.ignore_validation)
            else:
                centers = suggest_price_centers(args.symbol)
                if centers:
                    side_suffix = ""
                    if side_filter == "buy":
                        side_suffix = " --buy-only"
                    elif side_filter == "sell":
                        side_suffix = " --sell-only"
                    
                    print(f"\nTo create market making orders, run:")
                    print(f"maker-kit market-make --symbol {args.symbol} --center PRICE --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
                    print(f"\nExample using mid price:")
                    print(f"maker-kit market-make --symbol {args.symbol} --center {centers['mid_price']:.6f} --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
                    print(f"\nExample using mid-range:")
                    print(f"maker-kit market-make --symbol {args.symbol} --center mid-range --levels {args.levels} --spread {args.spread} --size {args.size}{side_suffix}")
        elif args.command == "auto-market-make":
            # Determine side filter
            side_filter = None
            if args.buy_only:
                side_filter = "buy"
            elif args.sell_only:
                side_filter = "sell"
            
            # Resolve center price from string input
            center_price = resolve_center_price(args.symbol, args.center)
            if center_price is None:
                return  # Error already printed by resolve_center_price
            
            asyncio.run(auto_market_make(args.symbol, center_price, args.levels, args.spread, args.size, side_filter, args.test_only, args.ignore_validation))
        elif args.command == "fill-spread":
            # Resolve center price if provided
            center_price = None
            if args.center:
                center_price = resolve_center_price(args.symbol, args.center)
                if center_price is None:
                    return  # Error already printed by resolve_center_price
            
            fill_spread(args.symbol, args.target_spread, args.size, center_price, args.dry_run)
        else:
            parser.print_help()
    
    # Run the command (only auto-market-make needs async)
    try:
        run_command()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1  # Exit with error code


if __name__ == "__main__":
    main() 