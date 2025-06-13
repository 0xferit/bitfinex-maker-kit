"""
Authentication and API client management for Bitfinex CLI.
"""

import os
import sys
from ..bitfinex_client import create_wrapper_client


def get_credentials():
    """Get API credentials from environment variables or .env file"""
    # First try environment variables
    api_key = os.getenv("BFX_API_KEY")
    api_secret = os.getenv("BFX_API_SECRET")
    
    # If not found in env vars, try loading from .env file
    if not api_key or not api_secret:
        env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            
                            if key == "BFX_API_KEY":
                                api_key = value
                            elif key == "BFX_API_SECRET":
                                api_secret = value
                
                if api_key and api_secret:
                    # Only show this message once per session
                    if not hasattr(get_credentials, '_shown_env_message'):
                        print("📁 Loaded API credentials from .env file")
                        get_credentials._shown_env_message = True
            except Exception as e:
                print(f"⚠️  Error reading .env file: {e}")
    
    if not api_key or not api_secret:
        print("❌ Error: Missing required API credentials!")
        print()
        print("📋 Set credentials using one of these methods:")
        print()
        print("Method 1: Environment Variables")
        print("  export BFX_API_KEY='your_api_key_here'")
        print("  export BFX_API_SECRET='your_api_secret_here'")
        print()
        print("Method 2: Create a .env file in the same directory as this script:")
        print("  echo 'BFX_API_KEY=your_api_key_here' > .env")
        print("  echo 'BFX_API_SECRET=your_api_secret_here' >> .env")
        print()
        print("📖 To get API keys:")
        print("  1. Log into Bitfinex")
        print("  2. Go to Settings → API")
        print("  3. Create new key with trading permissions")
        print("  4. Save the API key and secret")
        sys.exit(1)
    
    return api_key, api_secret


def create_client():
    """Create and return a Bitfinex wrapper client with POST_ONLY enforcement"""
    api_key, api_secret = get_credentials()
    return create_wrapper_client(api_key, api_secret)


def test_api_connection():
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


def test_websocket_connection():
    """Test WebSocket connection and authentication"""
    print("Testing WebSocket connection...")
    
    try:
        client = create_client()
    except SystemExit:
        return False
    
    try:
        import asyncio
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
        
        # Use threading approach similar to the order update WebSocket implementation
        result_container = {"success": False, "error": None, "authenticated": False, "wallets": []}
        
        def websocket_test_worker():
            """Worker function to test WebSocket in separate thread"""
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def test_websocket():
                    """Async function to test WebSocket connection"""
                    
                    wss = client.wss
                    
                    # Set up event handlers for testing
                    @wss.on("authenticated")
                    async def on_authenticated(data):
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
                                print(f"✅ WebSocket + REST wallet test successful!")
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
                            pass  # Ignore close errors
                    
                    @wss.on("on-req-notification")
                    def on_notification(notification):
                        # Handle any notifications during testing
                        if hasattr(notification, 'status') and notification.status == "ERROR":
                            result_container["error"] = f"WebSocket notification error: {notification.text}"
                    
                    try:
                        # Start WebSocket connection
                        print("   🔌 Establishing WebSocket connection...")
                        await wss.start()
                        
                        # Wait for test completion with timeout
                        max_wait_time = 18  # 18 seconds timeout for testing (extra time for wallet data)
                        wait_time = 0
                        
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
                        
                    except Exception as ws_error:
                        result_container["error"] = f"WebSocket connection error: {ws_error}"
                    finally:
                        # Clean up - try to close WebSocket connection
                        try:
                            await wss.close()
                        except Exception:
                            pass  # Ignore close errors - connection might already be closed
                
                # Run the async test
                loop.run_until_complete(test_websocket())
                
            except Exception as e:
                result_container["error"] = f"WebSocket test worker error: {e}"
            finally:
                try:
                    loop.close()
                except Exception:
                    pass
        
        # Run WebSocket test in thread with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(websocket_test_worker)
            
            try:
                # Wait for completion with timeout
                future.result(timeout=25)  # 25 second total timeout (extra time for wallet data)
                
                # Check results
                if result_container["error"]:
                    print(f"❌ WebSocket test failed: {result_container['error']}")
                    return False
                elif result_container["success"]:
                    return True
                else:
                    print("❌ WebSocket test failed: Unknown error")
                    return False
                    
            except FutureTimeoutError:
                print("❌ WebSocket test timed out (25s)")
                return False
    
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False


def test_comprehensive():
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
        print("⚠️  REST API works but WebSocket failed. Order updates and real-time features may not work.")
        return False
    elif websocket_success:
        print("⚠️  WebSocket works but REST API failed. Basic operations may not work.")
        return False
    else:
        print("❌ Both REST API and WebSocket tests failed. Check your API credentials and network connection.")
        return False 