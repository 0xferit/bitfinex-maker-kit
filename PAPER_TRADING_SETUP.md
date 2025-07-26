# Paper Trading Integration Tests Setup

This document explains how to set up Bitfinex Paper Trading for running realistic load tests in the Bitfinex-Maker-Kit project.

## Overview

The realistic load tests use Bitfinex's Paper Trading environment to test the system under real API conditions without risking actual funds. Paper Trading provides:

- Real API endpoints and authentication
- Realistic network latency and rate limiting  
- Actual error conditions and responses
- Safe testing environment with mock funds

## Setup Instructions

### 1. Create a Bitfinex Paper Trading Account

1. **Log into Bitfinex**: Go to [bitfinex.com](https://www.bitfinex.com) and log into your account
2. **Access Sub-Accounts**: Navigate to the Sub-Accounts section in the main navigation bar
3. **Create Paper Trading Sub-Account**: 
   - Click "Create new sub-account"
   - Select "Paper" as the account type
   - Give it a descriptive name like "api-testing" or "maker-kit-tests"

### 2. Generate API Credentials

1. **Access API Settings**: In your paper trading sub-account, go to API settings
2. **Create API Key**: 
   - Click "Create new API key"
   - Set permissions needed for testing:
     - ✅ Read orders
     - ✅ Create orders  
     - ✅ Cancel orders
     - ✅ Read wallets
     - ❌ Withdraw funds (not needed for testing)
3. **Save Credentials**: Copy the API key and secret immediately (secret is shown only once)

### 3. Set Environment Variables

Set the following environment variables with your Paper Trading credentials:

```bash
# For bash/zsh
export BITFINEX_PAPER_API_KEY="your_paper_trading_api_key_here"
export BITFINEX_PAPER_API_SECRET="your_paper_trading_api_secret_here"

# For fish shell
set -gx BITFINEX_PAPER_API_KEY "your_paper_trading_api_key_here"
set -gx BITFINEX_PAPER_API_SECRET "your_paper_trading_api_secret_here"
```

You can also create a `.env.testing` file in the project root:

```env
BITFINEX_PAPER_API_KEY=your_paper_trading_api_key_here
BITFINEX_PAPER_API_SECRET=your_paper_trading_api_secret_here
```

### 4. Verify Setup

Test your setup with a simple API call:

```bash
# Run a single integration test to verify credentials
pytest tests/integration/test_trading_service.py::TestTradingServiceIntegration::test_place_order_integration -v

# Check if paper trading tests are detected
pytest --collect-only -m paper_trading
```

## Running Realistic Load Tests

### Run All Realistic Load Tests

```bash
# Run all realistic load tests (requires paper trading credentials)
pytest tests/load/test_realistic_load.py -m realistic_load -v

# Run with more verbose output
pytest tests/load/test_realistic_load.py -m realistic_load -v -s
```

### Run Specific Test Categories

```bash
# Run only paper trading tests
pytest -m paper_trading -v

# Run load tests (includes both mock and realistic)
pytest -m load -v

# Run slow tests (includes realistic load tests)
pytest -m slow -v

# Skip paper trading tests if credentials not available
pytest -m "load and not paper_trading" -v
```

### Run Individual Tests

```bash
# Test realistic order placement load
pytest tests/load/test_realistic_load.py::TestRealisticTradingLoadScenarios::test_realistic_order_placement_load -v

# Test sustained trading session
pytest tests/load/test_realistic_load.py::TestRealisticTradingLoadScenarios::test_sustained_trading_session -v

# Test rate limit compliance
pytest tests/load/test_realistic_load.py::TestRealisticTradingLoadScenarios::test_rate_limit_compliance -v
```

## Test Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BITFINEX_PAPER_API_KEY` | Paper trading API key | Yes |
| `BITFINEX_PAPER_API_SECRET` | Paper trading API secret | Yes |

### Test Parameters

The realistic load tests use these parameters:

- **Rate Limits**: 1-20 operations per second (realistic API limits)
- **Test Duration**: 10-60 seconds per test
- **Order Sizes**: 0.001 BTC (small test amounts)
- **Symbols**: `tTESTBTCTESTUSD` (paper trading pairs)
- **Memory Limits**: 200MB maximum
- **Response Time**: 5 second maximum per API call

## Available Test Symbols

Bitfinex Paper Trading supports these test symbols:

- `tTESTBTCTESTUSD` - Test Bitcoin vs Test USD
- `tTESTBTCTESTUSDT` - Test Bitcoin vs Test USDT

Use these symbols in your tests to avoid issues with real trading pairs.

## Troubleshooting

### Common Issues

**Tests Skip with "Paper trading credentials not available"**
- Verify environment variables are set correctly
- Check API key and secret are from a Paper Trading sub-account
- Ensure the sub-account has API access enabled

**Rate Limit Errors**
- Paper trading has the same rate limits as live trading
- Tests automatically enforce rate limiting
- Reduce `max_operations_per_second` if needed

**Connection Errors**
- Verify internet connectivity
- Check Bitfinex API status at [status.bitfinex.com](https://status.bitfinex.com)
- Paper trading uses the authenticated endpoint: `api.bitfinex.com`

**Invalid Symbol Errors**
- Use paper trading symbols: `tTESTBTCTESTUSD` or `tTESTBTCTESTUSDT`
- Avoid live trading symbols in paper trading tests

### Debug Mode

Run tests with debug output:

```bash
# Enable verbose logging
pytest tests/load/test_realistic_load.py -v -s --log-cli-level=DEBUG

# Show all print statements
pytest tests/load/test_realistic_load.py -v -s --capture=no
```

### Manual API Testing

Test your credentials manually:

```python
import os
from bitfinex_maker_kit.services.container import get_container

# Configure with paper trading credentials
config = {
    "api_key": os.environ["BITFINEX_PAPER_API_KEY"],
    "api_secret": os.environ["BITFINEX_PAPER_API_SECRET"],
    "base_url": "https://api.bitfinex.com",
}

container = get_container()
container.configure(config)
service = container.create_trading_service()

# Test basic operations
orders = service.get_orders()
print(f"Current orders: {len(orders)}")

balances = service.get_wallet_balances()
print(f"Wallet balances: {balances}")
```

## Benefits of Realistic Load Testing

### What This Tests vs Mock Testing

| Aspect | Mock Tests | Realistic Load Tests |
|--------|------------|---------------------|
| **Throughput** | 12,000+ ops/sec (unrealistic) | 1-50 ops/sec (realistic) |
| **Network** | No network calls | Real network latency |
| **Rate Limits** | No rate limiting | Real API rate limits |
| **Errors** | Simulated errors | Real API error conditions |
| **Memory** | Mock object overhead | Real API client memory usage |
| **Latency** | Near-zero response time | Real network response times |

### Production Confidence

Realistic load tests provide confidence that:

- ✅ The system works with real API latency
- ✅ Rate limiting is handled correctly
- ✅ Network errors are recovered gracefully  
- ✅ Memory usage is reasonable under real conditions
- ✅ Response times meet expectations
- ✅ Error handling works with real API errors

## CI/CD Integration

For automated testing in CI/CD:

```yaml
# GitHub Actions example
env:
  BITFINEX_PAPER_API_KEY: ${{ secrets.BITFINEX_PAPER_API_KEY }}
  BITFINEX_PAPER_API_SECRET: ${{ secrets.BITFINEX_PAPER_API_SECRET }}

steps:
  - name: Run realistic load tests
    run: |
      pytest tests/load/test_realistic_load.py -m realistic_load -v
    # Only run if credentials are available
    if: env.BITFINEX_PAPER_API_KEY != ''
```

Add your paper trading credentials as repository secrets in GitHub Actions, GitLab CI, or your CI/CD platform.