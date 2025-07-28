"""
Real-time market monitoring command using WebSocket connections.

Provides a live dashboard showing order book, trades, user orders,
and connection statistics in real-time using WebSocket feeds.
"""

import asyncio
import contextlib
import signal
from typing import Any

from ..bitfinex_client import BitfinexClientWrapper
from ..utilities.auth import get_credentials
from ..utilities.constants import DEFAULT_SYMBOL
from .monitor_display import MonitorDisplay
from .monitor_websocket import MonitorWebSocketHandlers


async def monitor_command(symbol: str = DEFAULT_SYMBOL, levels: int = 40) -> None:
    """
    Main async monitoring function that sets up WebSocket connections and displays real-time data.

    Args:
        symbol: Trading symbol to monitor (e.g., 'tBTCUSD')
        levels: Number of order book levels to display
    """
    # Get API credentials
    try:
        api_key, api_secret = get_credentials()
    except Exception as e:
        print(f"❌ Error getting credentials: {e}")
        return

    if not api_key or not api_secret:
        print("❌ API credentials not found. Please check your .env file.")
        return

    # Initialize display and WebSocket client
    try:
        client = BitfinexClientWrapper(api_key, api_secret)
        display = MonitorDisplay(symbol, levels, api_key)
        display.client = client  # Pass client for order fetching
        display.add_event("Starting market monitor...", "SYS")
        display.add_debug_event(
            f"Terminal size: {display.terminal_width}x{display.terminal_height} (cols x rows)"
        )

        # Set up WebSocket handlers
        handlers = MonitorWebSocketHandlers(display, symbol)

        # Create WebSocket connection
        wss = client.wss
        handlers.setup_websocket_handlers(wss)

        display.add_event("Initializing WebSocket connection...", "CONN")

        # Set up graceful shutdown
        shutdown_event = asyncio.Event()

        def signal_handler(_signum: int, _frame: Any) -> None:
            print("\n🛑 Shutdown signal received...")
            shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start WebSocket connection in background
        websocket_task = asyncio.create_task(wss.run())

        try:
            # Main display loop
            while not shutdown_event.is_set():
                display.render_display()

                # Check if websocket is still running
                if websocket_task.done():
                    exception = websocket_task.exception()
                    if exception:
                        display.add_event(f"WebSocket error: {exception}", "ERR")
                    else:
                        display.add_event("WebSocket connection closed", "DISC")
                    break

                # Short sleep to prevent excessive CPU usage while keeping display responsive
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            display.add_event("Keyboard interrupt received", "SYS")
        except Exception as e:
            display.add_event(f"Monitor error: {e}", "ERR")
        finally:
            # Cleanup
            display.add_event("Shutting down monitor...", "SYS")

            # Cancel the websocket task
            if "websocket_task" in locals() and not websocket_task.done():
                websocket_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await websocket_task

            # Close WebSocket connection
            if "wss" in locals():
                await wss.close()

        print("\n✅ Market monitor stopped")

    except Exception as e:
        print(f"❌ Failed to initialize monitor: {e}")
        return


def monitor_command_sync(symbol: str = DEFAULT_SYMBOL, levels: int = 40) -> None:
    """
    Synchronous wrapper for the monitor command.

    Args:
        symbol: Trading symbol to monitor
        levels: Number of order book levels to display
    """
    try:
        asyncio.run(monitor_command(symbol, levels))
    except KeyboardInterrupt:
        print("\n🛑 Monitor interrupted by user")
    except Exception as e:
        print(f"❌ Monitor error: {e}")
