# Makefile for Bitfinex Maker-Kit
# Simple quality workflow automation

.PHONY: help install format lint type-check security test quality clean

# Default target
help:
	@echo "Bitfinex Maker-Kit - Simple Quality Workflow"
	@echo ""
	@echo "Available commands:"
	@echo "  install     Install development dependencies"
	@echo "  format      Format code automatically"
	@echo "  lint        Run linter (with auto-fix)"
	@echo "  type-check  Run type checking"
	@echo "  security    Run security scanning"
	@echo "  test        Run tests with coverage"
	@echo "  quality     Run all quality checks (recommended)"
	@echo "  clean       Clean up generated files"
	@echo ""
	@echo "Quick start: make install && make quality"

# Install development dependencies
install:
	@echo "📦 Installing development dependencies..."
	pip install -e ".[dev]"
	pre-commit install
	@echo "✅ Installation complete!"

# Format code automatically
format:
	@echo "🎨 Formatting code..."
	ruff format .
	@echo "✅ Code formatted!"

# Run linter with auto-fix
lint:
	@echo "🔍 Running linter..."
	ruff check . --fix
	@echo "✅ Linting complete!"

# Run type checking
type-check:
	@echo "🔎 Running type checks..."
	mypy maker_kit/
	@echo "✅ Type checking complete!"

# Run security scanning
security:
	@echo "🔒 Running security scan..."
	bandit -r maker_kit/ --skip B101 --quiet
	@echo "✅ Security scan complete!"

# Run tests with coverage
test:
	@echo "🧪 Running tests..."
	pytest --cov=maker_kit --cov-report=term-missing --cov-report=html
	@echo "✅ Tests complete!"

# Run all quality checks (main command)
quality: format lint type-check security
	@echo ""
	@echo "🎉 All quality checks passed!"
	@echo "Your code is ready for commit."

# Clean up generated files
clean:
	@echo "🧹 Cleaning up..."
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete!"

# Development workflow shortcuts
dev-setup: install
	@echo "🚀 Development environment ready!"

quick-check: lint type-check
	@echo "⚡ Quick checks complete!"

full-check: quality test
	@echo "🔥 Full quality validation complete!"