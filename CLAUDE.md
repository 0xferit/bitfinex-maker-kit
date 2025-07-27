# Bitfinex Maker-Kit - AI Assistant Context

## Project Overview

**Bitfinex Maker-Kit** is a specialized command-line interface (CLI) tool for automated trading and market making on the Bitfinex cryptocurrency exchange. This is a safety-first, production-ready trading automation tool with architectural safeguards.

### Key Characteristics
- **Language**: Python 3.12+ (strictly enforced)
- **License**: MIT (open source)
- **Version**: 4.0.0 (production-ready)
- **Purpose**: Market making and automated trading on Bitfinex
- **Architecture**: Single exchange, single strategy, safety-focused design

## Architecture & Safety Features

### Core Design Philosophy
- **Safety First**: Architecturally enforced POST_ONLY orders (impossible to bypass)
- **Single Exchange**: Bitfinex only (reduces complexity)
- **Single Strategy**: Market making focused (not multi-strategy)
- **Reliability**: Consistent, predictable behavior

### Critical Safety Features
- **POST_ONLY Enforcement**: The `BitfinexClientWrapper` class enforces POST_ONLY at the API boundary level
- **Dry-run Mode**: Available for testing without real trades
- **Price Validation**: Multiple layers of validation
- **Confirmation Prompts**: User confirmation for critical operations

## Codebase Structure

```
bitfinex_maker_kit/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point for CLI
├── cli.py                   # Main command-line interface
├── bitfinex_client.py       # API wrapper with POST_ONLY enforcement
├── commands/                # Individual CLI command modules
│   ├── cancel.py            # Cancel orders by ID or criteria (supports --all flag)
│   ├── fill_spread.py       # Fill bid-ask gaps with equally spaced orders
│   ├── list.py              # List active orders
│   ├── market_make.py       # Create staircase market making orders
│   ├── put.py               # Place single order
│   ├── test.py              # Test API connection
│   ├── update.py            # Update existing orders
│   └── wallet.py            # Show wallet balances
└── utilities/               # Shared utility modules
    ├── auth.py              # Authentication handling
    ├── console.py           # Console output utilities
    ├── constants.py         # Application constants
    ├── formatters.py        # Data formatting utilities
    ├── market_data.py       # Market data handling
    ├── orders.py            # Order management utilities
    ├── trading_helpers.py   # Trading logic helpers
    └── validators.py        # Input validation utilities
```

## Available Commands

| Command | Description | Key Features |
|---------|-------------|--------------|
| `test` | Test API connection | Validates credentials and connectivity |
| `wallet` | Show wallet balances | Displays available funds |
| `list` | List active orders | Shows current open orders |
| `cancel` | Cancel orders | Cancel by ID, symbol, criteria, or --all for clearing |
| `put` | Place single order | Manual order placement |
| `market-make` | Create staircase orders | Symmetric bid/ask levels |
| `fill-spread` | Fill bid-ask gaps | Equally spaced orders across spread |
| `update` | Update existing orders | Modify order parameters |

## Development Setup

### Installation
```bash
# Development installation
pipx install -e .

# Production installation  
pipx install .
```

### Dependencies
- **Core**: `bitfinex-api-py>=3.0.0`
- **Python**: 3.12+ (strictly enforced)
- **Environment**: Requires `.env` file with API credentials

### Configuration
- **Default Symbol**: `tPNKUSD`
- **Default Levels**: 3
- **Default Spread**: 1.0%
- **Default Order Size**: 10.0
- **Configurable**: Via command line arguments

## Key Technical Details

### API Wrapper Architecture
The `BitfinexClientWrapper` class in `bitfinex_client.py` provides:
- POST_ONLY enforcement at API boundary
- Error handling and retry logic
- Rate limiting compliance
- Authentication management

### Utilities System
- **auth.py**: Handles API credential management
- **console.py**: Provides consistent terminal output
- **market_data.py**: Market data fetching and processing
- **orders.py**: Order management and tracking
- **validators.py**: Input validation and safety checks

### Testing Strategy
Located in `tests/` directory:
- `test_post_only_enforcement.py`: Validates POST_ONLY constraints
- `test_python_version_requirement.py`: Version compliance checks
- `test_wrapper_architecture.py`: Architecture validation

## Important Safety Considerations

1. **POST_ONLY Orders**: All orders are architecturally constrained to be POST_ONLY (maker orders)
2. **No Market Orders**: Cannot accidentally place market orders that would take liquidity
3. **Confirmation Required**: Critical operations require user confirmation
4. **Dry Run Available**: Test mode available for strategy validation
5. **Price Validation**: Multiple validation layers prevent erroneous orders

## Usage Guidelines

### Best Practices
- Always test with small amounts first
- Use dry-run mode for strategy validation
- Monitor orders regularly using `list` command
- Keep API credentials secure in `.env` file
- Understand market conditions before market-making

### Common Workflows
1. **Setup**: Test connection → Check wallet → Start small
2. **Manual Trading**: Use `put` for individual orders
3. **Market Making**: Use `market-make` for symmetric levels
4. **Management**: Use `list`, `update`, `cancel` for order management

## Environment Variables Required
```
BITFINEX_API_KEY=your_api_key
BITFINEX_API_SECRET=your_api_secret
```

## Command Examples
```bash
# Test connection
python -m bitfinex_maker_kit test

# Show wallet
python -m bitfinex_maker_kit wallet

# List orders
python -m bitfinex_maker_kit list

# Market make with 5 levels, 2% spread
python -m bitfinex_maker_kit market-make --levels 5 --spread 2.0
```