"""
Authentication and API client management for Bitfinex CLI.
"""

import os
import sys
from .bitfinex_client import create_wrapper_client


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