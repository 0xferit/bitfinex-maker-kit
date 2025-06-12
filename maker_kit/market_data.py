"""
Market data operations for Bitfinex CLI.
"""

from .auth import create_client


def get_ticker_data(symbol: str):
    """Get ticker data for a symbol"""
    client = create_client()
    
    try:
        ticker = client.get_ticker(symbol)
        return {
            'bid': float(ticker.bid),
            'ask': float(ticker.ask),
            'last_price': float(ticker.last_price),
            'bid_size': float(ticker.bid_size),
            'ask_size': float(ticker.ask_size)
        }
    except Exception as e:
        print(f"❌ Failed to get ticker data: {e}")
        return None


def get_last_trade(symbol: str):
    """Get the most recent trade for a symbol"""
    client = create_client()
    
    try:
        trades = client.get_trades(symbol, limit=1)
        if trades:
            return float(trades[0].price)
        else:
            print("No recent trades found")
            return None
    except Exception as e:
        print(f"❌ Failed to get trade data: {e}")
        return None


def suggest_price_centers(symbol: str):
    """Suggest appropriate price centers based on market data"""
    print(f"Analyzing market data for {symbol}...")
    
    ticker = get_ticker_data(symbol)
    if not ticker:
        return None
    
    last_trade = get_last_trade(symbol)
    
    print(f"\n📊 Market Data for {symbol}:")
    print(f"   Best Bid: ${ticker['bid']:.6f} (Size: {ticker['bid_size']:.2f})")
    print(f"   Best Ask: ${ticker['ask']:.6f} (Size: {ticker['ask_size']:.2f})")
    print(f"   Last Price: ${ticker['last_price']:.6f}")
    if last_trade:
        print(f"   Latest Trade: ${last_trade:.6f}")
    
    mid_price = (ticker['bid'] + ticker['ask']) / 2
    spread = ticker['ask'] - ticker['bid']
    spread_pct = (spread / mid_price) * 100
    
    print(f"\n💡 Suggested Price Centers:")
    print(f"   1. Mid Price: ${mid_price:.6f} (between bid/ask)")
    print(f"   2. Last Price: ${ticker['last_price']:.6f}")
    if last_trade and abs(last_trade - ticker['last_price']) > 0.000001:
        print(f"   3. Latest Trade: ${last_trade:.6f}")
    
    print(f"\n📈 Market Info:")
    print(f"   Spread: ${spread:.6f} ({spread_pct:.3f}%)")
    
    return {
        'mid_price': mid_price,
        'last_price': ticker['last_price'],
        'latest_trade': last_trade,
        'bid': ticker['bid'],
        'ask': ticker['ask'],
        'spread': spread,
        'spread_pct': spread_pct
    }


def validate_center_price(symbol: str, center_price: float, ignore_validation: bool = False):
    """Validate that center price is within the current bid-ask spread"""
    ticker = get_ticker_data(symbol)
    if not ticker:
        print("❌ Failed to get market data for validation")
        return False, None

    bid = ticker['bid']
    ask = ticker['ask']

    if ignore_validation:
        print(f"⚠️  Price validation IGNORED - using center price ${center_price:.6f}")
        print(f"   Current spread: ${bid:.6f} - ${ask:.6f}")
        return True, {'bid': bid, 'ask': ask}

    if center_price <= bid:
        print(f"❌ Invalid center price: ${center_price:.6f} is at or below current best bid (${bid:.6f})")
        print(f"   Center price must be above the best bid for meaningful market making")
        print(f"   💡 Valid range: ${bid:.6f} < center price < ${ask:.6f}")
        print(f"   💡 Use --ignore-validation flag to bypass this check")
        return False, {'bid': bid, 'ask': ask}

    if center_price >= ask:
        print(f"❌ Invalid center price: ${center_price:.6f} is at or above current best ask (${ask:.6f})")
        print(f"   Center price must be below the best ask for meaningful market making")
        print(f"   💡 Valid range: ${bid:.6f} < center price < ${ask:.6f}")
        print(f"   💡 Use --ignore-validation flag to bypass this check")
        return False, {'bid': bid, 'ask': ask}

    print(f"✅ Center price ${center_price:.6f} is valid (within spread: ${bid:.6f} - ${ask:.6f})")
    return True, {'bid': bid, 'ask': ask}


def resolve_center_price(symbol: str, center_input: str):
    """Resolve center price from string input (numeric value or 'mid-range')"""
    if center_input.lower() == "mid-range":
        ticker = get_ticker_data(symbol)
        if not ticker:
            print("❌ Failed to get market data for mid-range calculation")
            return None
        
        mid_price = (ticker['bid'] + ticker['ask']) / 2
        print(f"📍 Using mid-range center: ${mid_price:.6f}")
        return mid_price
    else:
        try:
            center_price = float(center_input)
            print(f"📍 Using custom center: ${center_price:.6f}")
            return center_price
        except ValueError:
            print(f"❌ Invalid center value: '{center_input}'. Use a number or 'mid-range'")
            return None 