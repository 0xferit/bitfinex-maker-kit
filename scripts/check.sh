#!/bin/bash
# Quick quality check script for Maker-Kit
# Usage: ./scripts/check.sh

set -e  # Exit on first error

echo "🚀 Running quick quality checks..."
echo ""

# Check if tools are installed
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ $1 not found. Run 'make install' first."
        exit 1
    fi
}

echo "📋 Checking tool availability..."
check_tool ruff
check_tool mypy
check_tool bandit

echo "✅ All tools available"
echo ""

# Format check (don't auto-format, just check)
echo "🎨 Checking code formatting..."
if ruff format --check . --quiet; then
    echo "✅ Code formatting is correct"
else
    echo "❌ Code formatting issues found. Run 'make format' to fix."
    exit 1
fi

# Linting
echo "🔍 Running linter..."
if ruff check . --quiet; then
    echo "✅ No linting issues found"
else
    echo "❌ Linting issues found. Run 'make lint' to auto-fix."
    exit 1
fi

# Type checking
echo "🔎 Running type checks..."
if mypy maker_kit/ --quiet; then
    echo "✅ No type issues found"
else
    echo "❌ Type checking failed. Check output above."
    exit 1
fi

# Security scanning
echo "🔒 Running security scan..."
if bandit -r maker_kit/ --skip B101 --quiet --format json > /dev/null 2>&1; then
    echo "✅ No security issues found"
else
    echo "⚠️  Security scan found potential issues. Run 'make security' for details."
fi

echo ""
echo "🎉 All checks passed! Your code is ready for commit."
echo ""
echo "💡 Tip: Run 'make quality' for full checks with auto-fixes"