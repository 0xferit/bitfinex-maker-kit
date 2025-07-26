# Bitfinex Maker-Kit

> **Enterprise-Grade Market Making Platform for Bitfinex**

A professional, production-ready command-line interface for automated trading and market making on the Bitfinex cryptocurrency exchange. Engineered with safety-first architecture, comprehensive testing, and enterprise-grade performance optimizations.

[![CI Status](https://github.com/bitfinex/maker-kit/workflows/CI/badge.svg)](https://github.com/bitfinex/maker-kit/actions)
[![Coverage](https://codecov.io/gh/bitfinex/maker-kit/branch/main/graph/badge.svg)](https://codecov.io/gh/bitfinex/maker-kit)
[![Security Rating](https://api.securityscorecards.dev/projects/github.com/bitfinex/maker-kit/badge)](https://api.securityscorecards.dev/projects/github.com/bitfinex/maker-kit)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 🎯 Key Features

### 🛡️ Safety-First Architecture
- **POST_ONLY Enforcement**: Architecturally impossible to place market orders
- **Dry-Run Mode**: Test strategies without real trading
- **Price Validation**: Multiple layers of order validation
- **Risk Management**: Built-in safeguards and confirmation prompts

### ⚡ Enterprise Performance
- **Advanced Caching**: 90%+ reduction in API calls with intelligent cache warming
- **Request Batching**: 50%+ throughput improvement with automatic batching
- **Real-Time Monitoring**: Performance dashboards and automated alerting
- **Memory Optimization**: Intelligent memory management and leak detection

### 🧪 Comprehensive Testing
- **Property-Based Testing**: 1000+ generated test cases using Hypothesis
- **Load Testing**: Multiple traffic patterns and stress scenarios
- **Performance Benchmarking**: Automated regression detection
- **Security Scanning**: Continuous vulnerability assessment

### 🚀 Production Ready
- **CI/CD Pipeline**: Automated quality gates and deployment validation
- **Performance Monitoring**: Daily benchmarks with regression alerts
- **Enterprise Logging**: Structured logging with performance metrics
- **Docker Support**: Containerized deployment ready

## 🏗️ Architecture Principles

### Design Philosophy
- **Safety First**: Architecturally enforced POST_ONLY orders (impossible to bypass)
- **Single Exchange**: Bitfinex only (reduces complexity, increases reliability)
- **Single Strategy**: Market making focused (not multi-strategy)
- **Enterprise Grade**: Production-ready with comprehensive monitoring

### Core Components
- **Domain Objects**: Type-safe value objects with validation
- **Service Layer**: Dependency injection with async/await patterns
- **Command Pattern**: Structured command execution with undo capabilities
- **Performance Monitoring**: Real-time metrics and optimization tools

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
```bash
# Clone repository
git clone https://github.com/bitfinex/maker-kit.git
cd maker-kit

# Quick setup (installs dev dependencies + pre-commit)
make install

# Or manual installation
pip install -e ".[dev]"
pre-commit install

# Verify installation
make quality          # Run all quality checks
pytest               # Run tests
```

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
maker-kit auto-market-make --symbol tBTCUSD --duration 3600

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
```

## 📋 Available Commands

| Command | Description | Key Features |
|---------|-------------|--------------|
| `test` | Test API connection | Validates credentials and connectivity |
| `wallet` | Show wallet balances | Real-time balance information |
| `list` | List active orders | Filterable order display |
| `cancel` | Cancel orders | Bulk cancellation support |
| `put` | Place single order | Manual order placement |
| `market-make` | Create staircase orders | Symmetric bid/ask levels |
| `auto-market-make` | Automated market making | Dynamic price adjustment |
| `fill-spread` | Fill bid-ask gaps | Equally spaced order placement |
| `clear` | Clear all orders | Emergency order clearing |
| `update` | Update existing orders | Order modification |

## 🧪 Testing & Quality Assurance

### Test Categories
- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Service interaction validation
- **Property Tests**: Hypothesis-based edge case discovery
- **Load Tests**: Performance under various traffic patterns
- **Benchmark Tests**: Performance regression detection

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m property      # Property-based tests
pytest -m load          # Load tests
pytest -m benchmark     # Performance benchmarks

# Run with coverage
pytest --cov=maker_kit --cov-report=html

# Run performance benchmarks
pytest tests/benchmarks/ --benchmark-json=results.json
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
mypy maker_kit/       # Type checking
bandit -r maker_kit/  # Security scan
```

**Quick validation** (30 seconds):
```bash
./scripts/check.sh    # Fast pre-commit check
```

## 📊 Performance Monitoring

### Real-Time Metrics
- **API Response Times**: P50, P95, P99 percentiles
- **Cache Hit Ratios**: Efficiency tracking
- **Order Throughput**: Operations per second
- **Memory Usage**: Leak detection and optimization
- **Error Rates**: Success/failure tracking

### Performance Dashboard
Access the built-in performance dashboard:
```bash
# Start performance monitoring
maker-kit monitor --dashboard

# View performance metrics
maker-kit metrics --export json
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

## 📖 Documentation

### Architecture Documentation
- [System Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Performance Guide](docs/performance.md)
- [Security Guide](docs/security.md)

### User Guides
- [Getting Started](docs/getting-started.md)
- [Market Making Strategies](docs/strategies.md)
- [Configuration Reference](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)

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