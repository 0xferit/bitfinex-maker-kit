# Trading Safety Guidelines

## Core Safety Principles

### 1. **NO CACHING - FRESH DATA ALWAYS**
- **Never cache market data, prices, or order states**
- **Always fetch live data from Bitfinex API**
- **Stale data can cause catastrophic trading losses**
- **Performance costs are acceptable for data accuracy**

### 2. **POST_ONLY ORDERS EXCLUSIVELY**
- **All orders MUST be POST_ONLY (maker orders)**
- **Never place market orders (taker orders)**
- **Architecturally enforced at API client level**
- **Prevents accidental market taking and slippage**

### 3. **Real-Time Data Requirements**
- **Order status**: Always fetch current state
- **Account balances**: Always fetch live balances
- **Market prices**: Always fetch live ticker/orderbook
- **Position data**: Always fetch current positions

## Implementation Guidelines

### Data Fetching
```python
# ✅ CORRECT - Always fetch live data
current_price = await api_client.get_ticker(symbol)
account_balance = await api_client.get_account_balance()
order_status = await api_client.get_order_status(order_id)

# ❌ WRONG - Never use cached data
cached_price = await cache.get("ticker", symbol)  # DANGEROUS!
```

### Order Placement
```python
# ✅ CORRECT - POST_ONLY enforced
order = await api_client.submit_order(
    symbol=symbol,
    amount=amount,
    price=price,
    flags=POST_ONLY_FLAG  # Architecturally enforced
)

# ❌ WRONG - Market orders prohibited
order = await api_client.submit_market_order(...)  # FORBIDDEN!
```

## Risk Management

### Why No Caching?
1. **Price movements**: Crypto markets move rapidly
2. **Order state changes**: Orders can fill/cancel instantly  
3. **Balance updates**: Account balances change with each trade
4. **Regulatory compliance**: Real-time reporting requirements

### Why POST_ONLY?
1. **Predictable execution**: Known execution price
2. **No slippage**: Price guaranteed at order placement
3. **Market making**: Provides liquidity to market
4. **Fee optimization**: Maker rebates vs taker fees

## Monitoring

- Log all API calls for audit trail
- Monitor API response times vs cached performance
- Alert on any caching attempts in production
- Verify POST_ONLY flag on all orders

## Emergency Procedures

If stale data is detected:
1. **Immediately halt trading**
2. **Cancel all pending orders**
3. **Verify account state with live API calls**
4. **Investigate data source integrity**

**Remember: Better to be slow and accurate than fast and wrong.**