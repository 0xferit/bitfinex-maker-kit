"""
Authentication and API client management for Bitfinex CLI.
"""

import contextlib
import os
import sys
from typing import Any

from ..bitfinex_client import create_wrapper_client

# Module-level flag to track if we've shown the env file message
_shown_env_message = False


def get_credentials() -> tuple[str, str]:
    """Get API credentials from environment variables or .env file"""
    global _shown_env_message

    # First try environment variables (support both legacy and BITFINEX_* names)
    api_key = (
        os.getenv("BFX_API_KEY")
        or os.getenv("BITFINEX_API_KEY")
        or os.getenv("BFX_API_PAPER_KEY")
        or os.getenv("BITFINEX_API_PAPER_KEY")
    )
    api_secret = (
        os.getenv("BFX_API_SECRET")
        or os.getenv("BITFINEX_API_SECRET")
        or os.getenv("BFX_API_PAPER_SECRET")
        or os.getenv("BITFINEX_API_PAPER_SECRET")
    )

    # If not found in env vars, try loading from .env file
    if not api_key or not api_secret:
        # Look for .env file in project root (two levels up from utilities/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        env_file_path = os.path.join(project_root, ".env")

        # Fallback: also check current working directory
        if not os.path.exists(env_file_path):
            env_file_path = os.path.join(os.getcwd(), ".env")

        if os.path.exists(env_file_path):
            try:
                with open(env_file_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")

                            if key in {
                                "BFX_API_KEY",
                                "BITFINEX_API_KEY",
                                "BFX_API_PAPER_KEY",
                                "BITFINEX_API_PAPER_KEY",
                            }:
                                api_key = value
                            elif key in {
                                "BFX_API_SECRET",
                                "BITFINEX_API_SECRET",
                                "BFX_API_PAPER_SECRET",
                                "BITFINEX_API_PAPER_SECRET",
                            }:
                                api_secret = value

                if api_key and api_secret and not _shown_env_message:
                    # Only show this message once per session
                    print("📁 Loaded API credentials from .env file")
                    _shown_env_message = True
            except Exception as e:
                print(f"⚠️  Error reading .env file: {e}")

    if not api_key or not api_secret:
        print("❌ Error: Missing required API credentials!")
        print()

        # Show which specific credential is missing
        if not api_key and not api_secret:
            print("  ⚠️  Both API key and API secret are missing")
        elif not api_key:
            print("  ⚠️  API key is missing (API secret found)")
        else:
            print("  ⚠️  API secret is missing (API key found)")

        print()
        print("📋 Set credentials using one of these methods:")
        print()
        print("Method 1: Environment Variables (Recommended)")
        print("  export BITFINEX_API_KEY='your_api_key_here'")
        print("  export BITFINEX_API_SECRET='your_api_secret_here'")
        print()
        print("  Alternative names (also supported):")
        print("  • BFX_API_KEY / BFX_API_SECRET")
        print("  • BITFINEX_API_PAPER_KEY / BITFINEX_API_PAPER_SECRET (for paper trading)")
        print()
        print("Method 2: Create a .env file in your project directory:")
        print("  echo 'BITFINEX_API_KEY=your_api_key_here' > .env")
        print("  echo 'BITFINEX_API_SECRET=your_api_secret_here' >> .env")
        print()
        print("📖 To get API keys:")
        print("  1. Log into Bitfinex (https://www.bitfinex.com)")
        print("  2. Go to Account → API Keys")
        print("  3. Create new key with 'Orders' and 'Wallets' permissions")
        print("  4. Save the API key and secret securely")
        print()
        print("🔐 Security Tips:")
        print("  • Never commit API keys to version control")
        print("  • Use paper trading keys for testing")
        print("  • Restrict API permissions to only what's needed")
        sys.exit(1)

    return api_key, api_secret


def create_client() -> Any:
    """
    Create and return a Bitfinex wrapper client with POST_ONLY enforcement.

    DEPRECATED: Use dependency injection through ServiceContainer instead.
    This function is maintained for backward compatibility during transition.
    """
    api_key, api_secret = get_credentials()
    return create_wrapper_client(api_key, api_secret)


def test_api_connection() -> bool:
    """Test API connection by calling wallets endpoint"""
    print("Testing API connection...")

    try:
        client = create_client()
    except SystemExit:
        return False

    try:
        wallets = client.get_wallets()
        print("✅ API connection successful!")
        print(f"Found {len(wallets)} wallets")
        return True
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False


def test_websocket_connection() -> bool:
    """Test WebSocket connection and authentication using focused helper functions."""
    print("Testing WebSocket connection...")

    try:
        client = create_client()
    except SystemExit:
        return False

    try:
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FutureTimeoutError

        # Use threading approach with focused helper functions
        result_container: dict[str, Any] = {
            "success": False,
            "error": None,
            "authenticated": False,
            "wallets": [],
        }

        # Run WebSocket test in thread with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_websocket_test_worker, client, result_container)

            try:
                # Wait for completion with timeout
                future.result(timeout=25)  # 25 second total timeout

                # Check results
                return _process_websocket_test_results(result_container)

            except FutureTimeoutError:
                print("❌ WebSocket test timed out (25s)")
                return False

    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


def _websocket_test_worker(client: Any, result_container: dict[str, Any]) -> None:
    """Worker function to test WebSocket in separate thread."""
    import asyncio

    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the async test
        loop.run_until_complete(_test_websocket_async(client, result_container))

    except Exception as e:
        result_container["error"] = f"WebSocket test worker error: {e}"
    finally:
        with contextlib.suppress(Exception):
            loop.close()


async def _test_websocket_async(client: Any, result_container: dict[str, Any]) -> None:
    """Async function to test WebSocket connection with focused handlers."""
    wss = client.wss

    # Set up event handlers for testing
    _setup_websocket_test_handlers(wss, client, result_container)

    try:
        # Start WebSocket connection
        print("   🔌 Establishing WebSocket connection...")
        await wss.start()

        # Wait for test completion with timeout
        await _wait_for_websocket_test_completion(result_container)

    except Exception as ws_error:
        result_container["error"] = f"WebSocket connection error: {ws_error}"
    finally:
        # Clean up - try to close WebSocket connection
        with contextlib.suppress(Exception):
            await wss.close()


def _setup_websocket_test_handlers(wss: Any, client: Any, result_container: dict[str, Any]) -> None:
    """Set up WebSocket event handlers for testing."""

    @wss.on("authenticated")
    async def on_authenticated(data: Any) -> None:
        print("✅ WebSocket authenticated successfully!")
        result_container["authenticated"] = True

        # Test WebSocket operations
        try:
            # 1. Subscribe to a ticker channel for testing
            await wss.subscribe("ticker", symbol="tBTCUSD")
            print("✅ WebSocket subscription test successful!")

            # 2. Test wallet retrieval via REST API (for comparison)
            print("   📊 Testing wallet retrieval via REST...")
            try:
                wallets = client.get_wallets()
                result_container["wallets"] = wallets
                print("✅ WebSocket + REST wallet test successful!")
                print(f"Found {len(wallets)} wallets (via REST after WebSocket auth)")
            except Exception as wallet_error:
                print(f"⚠️  Wallet retrieval failed: {wallet_error}")
                # Don't fail the test for wallet issues

        except Exception as sub_error:
            print(f"⚠️  WebSocket test operations failed: {sub_error}")
            # Don't fail the test for subscription issues

        # Mark test as complete and close connection
        result_container["success"] = True
        try:
            await wss.close()
            print("   🔌 WebSocket test completed - connection closed")
        except Exception:
            pass  # nosec B110 - Expected behavior: ignore WebSocket close errors during cleanup

    @wss.on("on-req-notification")
    def on_notification(notification: Any) -> None:
        # Handle any notifications during testing
        if hasattr(notification, "status") and notification.status == "ERROR":
            result_container["error"] = f"WebSocket notification error: {notification.text}"


async def _wait_for_websocket_test_completion(result_container: dict[str, Any]) -> None:
    """Wait for WebSocket test completion with proper timeout handling."""
    import asyncio

    max_wait_time = 18.0  # 18 seconds timeout for testing
    wait_time = 0.0

    while wait_time < max_wait_time:
        await asyncio.sleep(0.5)
        wait_time += 0.5

        # Check if we got an error
        if result_container["error"]:
            break

        # Check if test completed successfully
        if result_container["success"]:
            break

        # Check if we're stuck waiting for authentication
        if wait_time > 10 and not result_container["authenticated"]:
            result_container["error"] = "WebSocket authentication timed out"
            break

    # If we exit the loop without completing, it's a timeout
    if not result_container["error"] and not result_container["success"]:
        if not result_container["authenticated"]:
            result_container["error"] = "WebSocket authentication timed out"
        else:
            result_container["error"] = "WebSocket test timed out"


def _process_websocket_test_results(result_container: dict[str, Any]) -> bool:
    """Process WebSocket test results and return success status."""
    if result_container["error"]:
        print(f"❌ WebSocket test failed: {result_container['error']}")
        return False
    elif result_container["success"]:
        return True
    else:
        print("❌ WebSocket test failed: Unknown error")
        return False


def test_comprehensive() -> bool:
    """Test both REST API and WebSocket connections"""
    print("🧪 Running Comprehensive API Tests...")
    print("=" * 50)

    rest_success = False
    websocket_success = False

    # Test 1: REST API Connection
    print("\n1️⃣  Testing REST API Connection")
    print("-" * 30)
    rest_success = test_api_connection()

    # Test 2: WebSocket Connection
    print("\n2️⃣  Testing WebSocket Connection")
    print("-" * 30)
    websocket_success = test_websocket_connection()

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    print(f"REST API:     {'✅ PASS' if rest_success else '❌ FAIL'}")
    print(f"WebSocket:    {'✅ PASS' if websocket_success else '❌ FAIL'}")
    print("-" * 50)

    if rest_success and websocket_success:
        print("🎉 All tests passed! Your Bitfinex API connection is fully functional.")
        return True
    elif rest_success:
        print(
            "⚠️  REST API works but WebSocket failed. Order updates and real-time features may not work."
        )
        return False
    elif websocket_success:
        print("⚠️  WebSocket works but REST API failed. Basic operations may not work.")
        return False
    else:
        print(
            "❌ Both REST API and WebSocket tests failed. Check your API credentials and network connection."
        )
        return False
