# Bitfinex CLI Tool (Maker-Kit)

A command-line interface for automated trading and market making on Bitfinex with **guaranteed POST_ONLY orders**.

## 🛠️ Installation

```bash
# Clone and install with pipx (recommended)
git clone <repository-url>
cd maker-kit
brew install pipx  # if not installed
pipx install .

# Configure API credentials
echo 'BFX_API_KEY=your_api_key_here' > .env
echo 'BFX_API_SECRET=your_api_secret_here' >> .env
```

## 🚀 Usage

```bash
maker-kit test                    # Test API connection
maker-kit wallet                  # View balances
maker-kit --help                  # See all commands
```

## 👨‍💻 Development

For fast development with instant feedback:

```bash
# One-time setup
pipx install -e .

# Development workflow
# 1. Edit any .py file in maker_kit/
# 2. Run: maker-kit [command]
# 3. Changes reflected instantly!
```

## 🛡️ Safety Features

- **POST_ONLY enforcement** at API boundary (architecturally impossible to bypass)
- **Dry-run mode** for testing (`--dry-run` flag)
- **Price validation** prevents unrealistic orders

## 📋 Commands

| Command | Description |
|---------|-------------|
| `test` | Test API connection |
| `wallet` | Show wallet balances |
| `list` | List active orders |
| `cancel` | Cancel orders |
| `put` | Place single order |
| `market-make` | Create market making orders |
| `auto-market-make` | Automated market making |
| `fill-spread` | Fill bid-ask gaps |

## ⚠️ Requirements

- **Python 3.12+** required
- **Test first**: Use `--dry-run` before real orders
- **Trading involves risk**: Only trade what you can afford to lose

---

**Ready to trade!** Start with `maker-kit test` to verify your setup. 