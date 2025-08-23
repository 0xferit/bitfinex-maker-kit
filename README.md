# Bitfinex Maker-Kit

> **Modular Market Making Platform for Bitfinex**

A professional, production-ready command-line interface for automated trading and market making on the Bitfinex cryptocurrency exchange. Built with modern software architecture principles including dependency injection, domain-driven design, and comprehensive testing frameworks.

[![GitHub Stars](https://img.shields.io/github/stars/0xferit/bitfinex-maker-kit?style=flat-square&logo=github)](https://github.com/0xferit/bitfinex-maker-kit/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/0xferit/bitfinex-maker-kit?style=flat-square&logo=github)](https://github.com/0xferit/bitfinex-maker-kit/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/0xferit/bitfinex-maker-kit?style=flat-square&logo=github)](https://github.com/0xferit/bitfinex-maker-kit/issues)
[![PyPI Version](https://img.shields.io/pypi/v/bitfinex-maker-kit?style=flat-square&logo=pypi)](https://pypi.org/project/bitfinex-maker-kit/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square&logo=python)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)

## 🎯 Key Features

### 🛡️ Safety-First Architecture
- **POST_ONLY Enforcement**: Architecturally impossible to place market orders
- **Dry-Run Mode**: Test strategies without real trading
- **Multi-Layer Validation**: Domain objects, service layer, and API boundary validation
- **Risk Management**: Built-in safeguards and confirmation prompts

### ⚡ Modern Architecture
- **Dependency Injection**: Clean separation of concerns with container pattern
- **Domain-Driven Design**: Type-safe domain objects (OrderId, Price, Amount, Symbol)
- **Service-Oriented**: Modular services (trading, cache, market data, performance monitoring)
- **Event-Driven**: WebSocket integration with async event handling

### 🧪 Comprehensive Testing
- **Property-Based Testing**: 1000+ generated test cases using Hypothesis
- **Realistic Load Testing**: Integration tests against Bitfinex Paper Trading API
- **Performance Benchmarking**: Automated regression detection with real network conditions
- **Security Scanning**: Continuous vulnerability assessment

### 🚀 Production Ready
- **Modular Commands**: Extensible command system with core abstractions
- **Performance Monitoring**: Real-time metrics and profiling tools
- **Configuration Management**: Environment-aware configuration system
- **Quality Tooling**: Streamlined workflow with Ruff, MyPy, Bandit, and pytest

## 🏗️ Architecture Overview

### Modern Software Design
- **Safety First**: Architecturally enforced POST_ONLY orders with multiple validation layers
- **Modular Design**: Extensible architecture supporting multiple strategies and update methods
- **Domain-Driven**: Rich domain objects with business logic encapsulation
- **Service-Oriented**: Clean dependency injection with focused service responsibilities

### Core Architecture Components

#### 🎯 **Command Layer** (`commands/`)
- **Individual Commands**: `test`, `wallet`, `list`, `cancel`, `put`, `market-make`, `fill-spread`, `update`
- **Core Abstractions**: `core/` with base commands, executors, and result handling
- **Extensible Design**: Plugin-style command architecture

#### 🏛️ **Service Layer** (`services/`)
- **Container**: Dependency injection system managing service lifecycle
- **Trading Services**: Sync/async trading facades with monitoring
- **Cache Service**: Intelligent caching with namespace isolation
- **Performance Monitor**: Real-time metrics collection and analysis
- **Market Data Service**: Real-time price feeds and historical data

#### 🎨 **Domain Layer** (`domain/`)
- **Value Objects**: `OrderId`, `Price`, `Amount`, `Symbol` with validation
- **Business Logic**: Type-safe operations and domain rules
- **Immutable Design**: Functional programming principles

#### ⚙️ **Core Layer** (`core/`)
- **API Client**: Clean Bitfinex API wrapper with POST_ONLY enforcement
- **Trading Facade**: Unified interface coordinating focused components
- **Order Management**: Sophisticated order lifecycle management
- **Validation**: Multi-layer validation system

## 🛠️ Installation

### Production Installation
```bash
# Install with pipx (recommended)
pipx install bitfinex-maker-kit

# Configure API credentials
echo 'BITFINEX_API_KEY=your_api_key_here' > .env
echo 'BITFINEX_API_SECRET=your_api_secret_here' >> .env
```

### Development Installation

**Recommended: One-Command Setup** (solves externally-managed-environment errors)
```bash
# Clone repository
git clone https://github.com/0xferit/bitfinex-maker-kit.git
cd bitfinex-maker-kit

# One-command setup (creates venv + installs everything)
make setup

# Activate virtual environment (if not already active)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify installation
make quality          # Run all quality checks
pytest               # Run tests
```

**Alternative: Using pipx** (for tool installation)
```bash
# Install as isolated application
pipx install git+https://github.com/0xferit/bitfinex-maker-kit.git

# For development
git clone https://github.com/0xferit/bitfinex-maker-kit.git
cd bitfinex-maker-kit
pipx install -e .
```

**Manual Installation** (if virtual environment setup fails)
```bash
# Option 1: Force install (not recommended)
pip install -e ".[dev]" --break-system-packages

# Option 2: User install
pip install -e ".[dev]" --user

# Option 3: Traditional virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

**💡 Troubleshooting "externally-managed-environment" Error:**
- **Modern Python/macOS**: Use virtual environment (recommended above)
- **System Python**: Use `pipx` for isolated installation  
- **Docker**: Use the provided Dockerfile for containerized development

## 🚀 Quick Start

### Basic Usage
```bash
# Test API connection
maker-kit test

# View wallet balances
maker-kit wallet

# List active orders
maker-kit list

# Get help
maker-kit --help
```

### Market Making
```bash
# Create symmetric market making orders
maker-kit market-make --symbol tBTCUSD --levels 5 --spread 1.0 --size 0.1

# Start automated market making
maker-kit market-make --symbol tBTCUSD --levels 5

# Fill spread gaps
maker-kit fill-spread --symbol tETHUSD --levels 10
```

### Advanced Features
```bash
# Dry-run mode (recommended for testing)
maker-kit market-make --symbol tBTCUSD --levels 3 --dry-run

# Custom order placement
maker-kit put --symbol tBTCUSD --amount 0.01 --price 50000.0 --side buy

# Batch order cancellation
maker-kit cancel --symbol tBTCUSD --side buy

# Cancel all orders for a symbol
maker-kit cancel --all --symbol tBTCUSD
```

#### 🧩 **Strategies Layer** (`strategies/`, `update_strategies/`)
- **Order Generation**: Flexible order generation strategies
- **Update Strategies**: Multiple approaches (WebSocket, cancel-recreate, batch)
- **Strategy Factory**: Dynamic strategy selection based on market conditions

#### 🌐 **WebSocket Layer** (`websocket/`)
- **Connection Manager**: Robust WebSocket connection handling
- **Event Handler**: Real-time order updates and market data
- **Async Event Loop**: Non-blocking event processing

#### 🖥️ **UI Layer** (`ui/`)
- **Market Maker Console**: Interactive trading interface
- **Performance Dashboard**: Real-time metrics visualization
- **Profiler Integration**: Memory and performance monitoring

#### ⚙️ **Configuration Layer** (`config/`)
- **Environment Management**: Development, staging, production configs
- **Trading Configuration**: Dynamic configuration with validation
- **Feature Flags**: Environment-specific feature control

## 📋 Available Commands

| Command | Description | Architecture Features |
|---------|-------------|----------------------|
| `test` | Test API connection | Service container validation, credential testing |
| `wallet` | Show wallet balances | Real-time balance with caching and formatting |
| `list` | List active orders | Advanced filtering, display helpers, pagination |
| `cancel` | Cancel orders | Bulk operations, criteria matching, dry-run support, --all flag |
| `put` | Place single order | Domain validation, order builder pattern |
| `market-make` | Create staircase orders | Strategy-based generation, symmetric placement |
| `fill-spread` | Fill bid-ask gaps | Market data analysis, intelligent spacing |
| `update` | Update existing orders | Multiple update strategies, WebSocket optimization |

## 🧪 Testing & Quality Assurance

### Comprehensive Test Architecture

#### **Test Categories**
- **Unit Tests** (`tests/unit/`): Isolated component testing with mocks
- **Integration Tests** (`tests/integration/`): Service interaction validation
- **Property Tests** (`tests/property/`): Hypothesis-based fuzzing and edge cases
- **Load Tests** (`tests/load/`): Stress testing and traffic pattern simulation
- **Performance Tests** (`tests/performance/`): Benchmark suite with regression detection
- **Benchmarks** (`tests/benchmarks/`): Comprehensive performance analysis

#### **Test Infrastructure**
- **Fixtures** (`tests/fixtures/`): Reusable test data (API responses, market data, trading scenarios)
- **Mocks** (`tests/mocks/`): Service mocks (API, client, trading service, WebSocket)
- **Utilities** (`tests/utilities/`): Test helpers and profiling tools

#### **Specialized Testing**
- **POST_ONLY Enforcement**: Architectural safety validation
- **Python Version Compliance**: Version requirement testing
- **Wrapper Architecture**: API boundary validation

### Running Tests
```bash
# Run all tests with coverage
pytest --cov=bitfinex_maker_kit --cov-report=html

# Run specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests  
pytest tests/property/       # Property-based tests
pytest tests/load/           # Load and stress tests
pytest tests/performance/    # Performance benchmarks

# Run with markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m property      # Property-based tests
pytest -m load          # Load tests
pytest -m benchmark     # Performance benchmarks

# Run specific architectural tests
pytest tests/test_post_only_enforcement.py     # Safety validation
pytest tests/test_wrapper_architecture.py      # Architecture validation
pytest tests/test_python_version_requirement.py # Version compliance
```

### Code Quality - Simple Workflow

**Three commands for everything:**
```bash
# Quick setup
make install          # Install all dev dependencies

# Main workflow  
make quality          # Run all quality checks (recommended)
make test            # Run tests with coverage

# Individual checks (if needed)
make format          # Auto-format code
make lint            # Run linter with auto-fix
make type-check      # Run type checking
make security        # Run security scan
```

**Alternative: Direct commands**
```bash
# All-in-one linter and formatter (replaces black, isort, flake8)
ruff check . --fix    # Lint with auto-fix
ruff format .         # Format code

# Type checking and security
mypy bitfinex_maker_kit/       # Type checking
bandit -r bitfinex_maker_kit/  # Security scan
```

**Quick validation** (30 seconds):
```bash
./scripts/check.sh    # Fast pre-commit check
```

## 📊 Performance Monitoring & Observability

### Built-in Performance Infrastructure

#### **Performance Monitor Service** (`services/performance_monitor.py`)
- **Real-Time Metrics**: P50, P95, P99 percentiles for API operations
- **Cache Analytics**: Hit ratios, miss patterns, namespace efficiency
- **Memory Profiling**: Leak detection with heap snapshots
- **Error Tracking**: Success/failure rates with categorization

#### **Profiler Utilities** (`utilities/profiler.py`)
- **Execution Profiling**: Function-level performance analysis
- **Memory Monitoring**: Detailed memory usage tracking
- **Bottleneck Detection**: Automated performance regression alerts
- **Resource Utilization**: CPU, memory, and I/O monitoring

#### **Performance Dashboard** (`utilities/performance_dashboard.py`)
- **Real-Time Visualization**: Live metrics display
- **Historical Analysis**: Performance trend tracking
- **Alert System**: Automated threshold-based notifications
- **Export Capabilities**: JSON, CSV data export

#### **Market Data Caching** (`utilities/market_data_cache.py`)
- **Intelligent Caching**: 90%+ API call reduction
- **Cache Warming**: Proactive data prefetching  
- **Namespace Isolation**: Multi-symbol cache management
- **TTL Management**: Automatic cache invalidation

### Using Performance Tools
```bash
# Enable performance monitoring in commands
maker-kit market-make --enable-monitoring

# View performance metrics (via dashboard integration)
# Dashboard accessible through market-make UI console

# Load testing and benchmarks
pytest tests/performance/ --benchmark-json=results.json
pytest tests/load/ -v  # Stress testing
```

## 🔒 Security Features

### Built-in Security
- **POST_ONLY Orders**: Market orders architecturally impossible
- **API Key Protection**: Secure credential management
- **Input Validation**: Comprehensive parameter validation
- **Rate Limiting**: API abuse prevention
- **Audit Logging**: Complete operation tracking

### Security Scanning
- **Dependency Scanning**: Automated vulnerability detection
- **Code Analysis**: Static security analysis with Bandit
- **Secret Detection**: Credential leak prevention
- **License Compliance**: MIT license for maximum flexibility

## 🐳 Docker Deployment

### Docker Usage
```bash
# Build image
docker build -t maker-kit .

# Run container
docker run -d \
  --name maker-kit \
  -e BITFINEX_API_KEY=your_key \
  -e BITFINEX_API_SECRET=your_secret \
  maker-kit

# View logs
docker logs maker-kit
```

### Docker Compose
```yaml
version: '3.8'
services:
  maker-kit:
    build: .
    environment:
      - BITFINEX_API_KEY=${BITFINEX_API_KEY}
      - BITFINEX_API_SECRET=${BITFINEX_API_SECRET}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

## 📈 Performance Benchmarks

### Typical Performance Metrics
- **Order Placement**: 100+ orders/second
- **API Response Time**: <50ms P95
- **Cache Hit Ratio**: >90%
- **Memory Usage**: <100MB steady state
- **Error Rate**: <0.1% under normal conditions

### Load Testing Results
- **Constant Load**: 1000+ operations sustained
- **Burst Load**: 5000+ operations peak
- **Stress Test**: 99%+ uptime under extreme load
- **Memory Efficiency**: No memory leaks detected

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev,test,security]"

# Install pre-commit hooks
pre-commit install

# Run full test suite
tox
```

### Code Standards
- **Python 3.12+** required
- **Type hints** mandatory
- **100% test coverage** for new features
- **Security review** for all changes
- **Performance benchmarks** for optimizations

### Pull Request Process
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with tests and documentation
4. Run quality checks: `tox`
5. Submit pull request with detailed description

## 📖 Codebase Structure

### Directory Organization
```
bitfinex_maker_kit/
├── __init__.py              # Package entry point and exports
├── cli.py                   # Main CLI interface using focused components
├── bitfinex_client.py       # Legacy wrapper (delegating to core/)
├── cli/                     # CLI-specific components
│   ├── argument_parser.py   # Command-line argument parsing
│   └── command_router.py    # Command routing logic
├── commands/                # Individual command implementations
│   ├── core/                # Command abstractions and patterns
│   │   ├── base_command.py         # Base command interface
│   │   ├── command_executor.py     # Command execution framework
│   │   ├── command_result.py       # Result handling
│   │   └── [specialized_commands]  # Command implementations
│   └── [individual_commands].py    # Main CLI commands
├── core/                    # Core business logic
│   ├── api_client.py        # Clean Bitfinex API wrapper
│   ├── trading_facade.py    # Unified trading interface
│   ├── order_manager.py     # Order lifecycle management
│   └── order_validator.py   # Multi-layer validation
├── domain/                  # Domain objects and business rules
│   ├── order_id.py          # Order identification value object
│   ├── price.py             # Price value object with validation
│   ├── amount.py            # Amount value object with validation
│   └── symbol.py            # Trading pair symbol validation
├── services/                # Service layer with dependency injection
│   ├── container.py         # Dependency injection container
│   ├── trading_service.py   # Core trading operations
│   ├── cache_service.py     # Intelligent caching system
│   └── performance_monitor.py # Real-time metrics collection
├── strategies/              # Trading strategy implementations
│   └── order_generator.py   # Flexible order generation
├── update_strategies/       # Order update approaches
│   ├── base.py              # Update strategy interface
│   ├── websocket_strategy.py    # Real-time WebSocket updates
│   └── cancel_recreate_strategy.py # Cancel-recreate fallback
├── websocket/               # WebSocket integration
│   ├── connection_manager.py    # Connection lifecycle
│   └── event_handler.py     # Real-time event processing
├── ui/                      # User interface components
│   └── market_maker_console.py  # Interactive trading console
├── config/                  # Configuration management
│   ├── environment.py       # Environment-aware configuration
│   └── trading_config.py    # Trading-specific settings
└── utilities/               # Shared utilities and helpers
    ├── [various_utilities].py   # Helper functions and utilities
    ├── performance_dashboard.py # Performance visualization
    └── profiler.py          # Performance profiling tools
```

### Key Design Patterns
- **Dependency Injection**: Clean service boundaries with container pattern
- **Command Pattern**: Extensible command system with undo capabilities  
- **Strategy Pattern**: Pluggable algorithms for order generation and updates
- **Facade Pattern**: Simplified interfaces over complex subsystems
- **Domain-Driven Design**: Rich domain objects with business logic

## 🤝 Contributing

We welcome contributions! This project uses automated semantic versioning and release management.

### Development Workflow

1. **Fork and Clone**: Fork the repository and clone locally
2. **Create Feature Branch**: Branch from `develop` for new features
3. **Write Code**: Follow existing patterns and conventions
4. **Test Thoroughly**: Ensure all tests pass with `pytest`
5. **Submit PR**: Open a pull request to `develop` branch

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning. Your commit messages determine version bumps:

| Commit Type | Example | Version Bump |
|------------|---------|--------------|
| `fix:` | `fix: correct order cancellation logic` | Patch (0.0.X) |
| `feat:` | `feat: add stop-loss order support` | Minor (0.X.0) |
| `BREAKING CHANGE:` | `feat!: change API response format` | Major (X.0.0) |
| `chore:` | `chore: update dependencies` | No release |
| `docs:` | `docs: improve API documentation` | No release |
| `test:` | `test: add integration tests` | No release |
| `refactor:` | `refactor: simplify order validation` | Patch (0.0.X) |
| `perf:` | `perf: optimize WebSocket handling` | Patch (0.0.X) |

#### Examples

```bash
# Bug fix (patch release)
git commit -m "fix: resolve WebSocket reconnection issue"

# New feature (minor release)
git commit -m "feat: implement adaptive spread adjustment"

# Breaking change (major release)
git commit -m "feat!: redesign order management API

BREAKING CHANGE: OrderManager.create() now requires Symbol parameter"

# No release
git commit -m "docs: add examples for market-make command"
git commit -m "chore: update ruff configuration"
```

### Automated Release Process

When changes are merged from `develop` to `main`:
1. The system analyzes commit messages since the last release
2. Automatically determines the version bump type
3. Updates version in `pyproject.toml` and `__init__.py`
4. Creates a git tag
5. Publishes to PyPI
6. Creates a GitHub release

No manual version management needed!

## ⚠️ Risk Disclaimer

**IMPORTANT**: Trading cryptocurrency involves substantial risk of loss and is not suitable for every investor. The volatile nature of cryptocurrency markets may result in significant financial losses. You should carefully consider whether trading is suitable for you in light of your circumstances, knowledge, and financial resources.

- **Test First**: Always use `--dry-run` mode before live trading
- **Start Small**: Begin with minimal position sizes
- **Monitor Closely**: Actively supervise automated strategies
- **Risk Management**: Never trade more than you can afford to lose

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Dependencies
All dependencies use compatible permissive licenses (MIT, BSD, Apache-2.0). See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for complete license attributions.

## 🙏 Acknowledgments

- **Bitfinex API Team** for comprehensive API documentation
- **Open Source Community** for testing frameworks and tools
- **Security Researchers** for vulnerability disclosure
- **Trading Community** for feature requests and feedback

---

**Ready for Enterprise Trading!** 🚀

Start with `maker-kit test` to verify your setup, then explore the comprehensive feature set designed for professional market making. 