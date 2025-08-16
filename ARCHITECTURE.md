# Bitfinex Maker-Kit Architecture

## Overview
Simplified, minimal architecture using an explicit POST_ONLY flag at the API boundary.
The Service layer depends on a small `TradingClient` Protocol for clarity, testability, and maintainability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERACTION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  $ maker-kit market-make --levels 5 --spread 1.0                                │
│  $ maker-kit put --symbol tBTCUSD --side buy --price 50000 --size 0.001        │
│  $ maker-kit monitor                                                            │
│                                                                                   │
└────────────────────────┬─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               CLI COMMAND LAYER                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  put.py  │  │cancel.py │  │ list.py  │  │market_   │  │monitor.py│         │
│  │          │  │          │  │          │  │make.py   │  │          │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │              │              │              │              │               │
│       └──────────────┴──────────────┴──────────────┴──────────────┘              │
│                                     │                                             │
└─────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                         TradingService                                  │     │
│  ├────────────────────────────────────────────────────────────────────────┤     │
│  │  • High-level trading operations                                       │     │
│  │  • Domain object handling (Price, Amount, Symbol)                      │     │
│  │  • Business logic and validation                                       │     │
│  │  • Delegates to TradingClient (protocol)                               │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                     │                                             │
│  ┌──────────────────────┐  ┌───────┴────────┐  ┌────────────────────────┐     │
│  │  ServiceContainer    │  │  Utilities      │  │  Domain Objects        │     │
│  │  • Dependency        │  │  • auth.py      │  │  • Price               │     │
│  │    injection         │  │  • market_data  │  │  • Amount              │     │
│  │  • Service lifecycle │  │  • formatters   │  │  • Symbol              │     │
│  └──────────────────────┘  └────────────────┘  └────────────────────────┘     │
│                                                                                   │
└─────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           API CLIENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                       TradingClient (Protocol)                          │     │
│  ├────────────────────────────────────────────────────────────────────────┤     │
│  │  • Methods required by service (submit/cancel/update/get_*)            │     │
│  │  • Concrete impl: BitfinexAPIClient                                    │     │
│  │  • Explicit POST_ONLY flag (flags=4096) for safety                      │     │
│  │  • Market order rejection                                              │     │
│  └────────────────────────────┬───────────────────────────────────────────┘     │
│                               │                                                   │
│         Methods:              │              WebSocket Access:                    │
│         • submit_order() ─────┴──────► • wss property                           │
│         • get_orders()                  • Real-time data                        │
│         • cancel_order()                • Event subscriptions                   │
│         • update_order()                                                        │
│         • get_wallets()                                                         │
│         • get_ticker()                                                          │
│                                                                                   │
└─────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           LIBRARY LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │                     bitfinex-api-py (>=3.0.0)                          │     │
│  ├────────────────────────────────────────────────────────────────────────┤     │
│  │  • Standard Bitfinex Python API library                                │     │
│  │  • REST API: client.rest.auth.* / client.rest.public.*               │     │
│  │  • WebSocket: client.wss.*                                            │     │
│  │  • We explicitly pass POST_ONLY flag (4096) for all limit orders      │     │
│  └────────────────────────────┬───────────────────────────────────────────┘     │
│                               │                                                   │
└───────────────────────────────┼───────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         BITFINEX EXCHANGE API                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  • Receives orders with POST_ONLY flag (4096)                                   │
│  • Ensures maker-only execution                                                 │
│  • Provides rebates instead of fees                                            │
│  • Rejects orders that would cross the spread                                  │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Placing a Market Making Order

```
1. User Command
   └─► $ maker-kit market-make --levels 3 --spread 1.0

2. CLI Layer (market_make.py)
   └─► Parses arguments, validates input
   
3. Service Layer (TradingService)
   └─► Creates Price/Amount domain objects
   └─► Calculates order levels
   
4. API Client (BitfinexAPIClient)
   └─► submit_order(symbol, side, amount, price)
   └─► Adds POST_ONLY flag (4096) explicitly
   
5. Library (bitfinex-api-py)
   └─► client.rest.auth.submit_order(flags=4096)
   
6. Bitfinex API
   └─► Validates POST_ONLY
   └─► Places maker-only order
   └─► Returns order confirmation
```

## Key Safety Features

### 1. POST_ONLY Enforcement
- **Explicit Flag**: BitfinexAPIClient explicitly passes `flags=4096` (POST_ONLY)
- **Market Order Rejection**: Rejects any order without a price
- **Library Level**: Using standard bitfinex-api-py with explicit flag passing

### 2. Simplified Architecture
**Before Refactoring (4 layers):**
```
Commands → BitfinexClientWrapper → TradingFacade → BitfinexAPIClient → bfxapi
```

**After Refactoring (2 layers):**
```
Commands → BitfinexAPIClient → bitfinex-api-py
```

### 3. Benefits of Simplification
- **50% fewer layers** between commands and API
- **Single responsibility** - each component has one clear purpose
- **Explicit safety** - POST_ONLY flag clearly visible in code
- **Easier debugging** - fewer abstraction layers to trace through
- **Better maintainability** - simpler codebase with less indirection

## Component Responsibilities

### TradingClient Protocol (`core/types.py`)
- Minimal contract for client capabilities used by services
- Structural typing enables clean mocks and future client swaps

### BitfinexAPIClient (`core/api_client.py`)
- Direct API communication
- Explicit POST_ONLY flag enforcement
- Parameter validation
- Error handling and retries

### TradingService (`services/trading_service.py`)
- High-level trading operations
- Domain object management
- Business logic
- Delegates to TradingClient (protocol)

### CLI Commands (`commands/*.py`)
- Argument parsing
- User interaction
- Output formatting
- Calls service layer or API client

### Utilities
- **auth.py**: Credential management
- **market_data.py**: Market data helpers (reads fresh data only)
- **formatters.py**: Output formatting
- **constants.py**: Shared constants including POST_ONLY_FLAG (4096)

## WebSocket Architecture

```
Monitor Command
      │
      ▼
BitfinexAPIClient.wss
      │
      ▼
WebSocket Handlers
├── on_authenticated
├── on_ticker_update  
├── on_book_snapshot
├── on_book_update
├── on_trades
└── on_order_*

Real-time Updates:
• Order book changes
• Trade executions
• User order updates
• Market data streaming
```

## Error Handling Flow

```
User Input
    │
    ▼
Validation Layer
    ├── CLI argument validation
    ├── Domain object validation
    └── API parameter validation
         │
         ▼
    API Execution
         ├── Success → Return result
         └── Failure → OrderSubmissionError
                       with detailed message
```

## Security & Safety

1. **Credentials**: Loaded from environment or `.env` file
2. **POST_ONLY**: Explicitly enforced at API boundary
3. **No Market Orders**: Rejected at client level
4. **Validation**: Multi-layer input validation
5. **Robustness Metrics**: Tracked continuously (API response time, error rate, CPU, memory)
6. **Error Handling**: Comprehensive error messages

## Technology Stack

- **Language**: Python 3.12+
- **API Library**: bitfinex-api-py (>=3.0.0)
- **CLI Framework**: Click
- **Async Support**: asyncio, aiohttp
- **WebSocket**: Built into bitfinex-api-py
- **Testing**: pytest, unittest

## Policy

- No caches in trading paths. All trading decisions use live data.
- Simplicity first: fewer layers, explicit boundaries, structural typing.
- Maker-only: explicit POST_ONLY flag at the API boundary.

The architecture prioritizes clarity and maintainability with the minimum viable surface area.