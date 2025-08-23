#!/bin/bash

# Release automation script for Bitfinex Maker Kit
# Usage: ./scripts/release.sh [patch|minor|major]

set -euo pipefail
trap 'echo "Error on line $LINENO" >&2' ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if bump type is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please specify version bump type (patch, minor, or major)${NC}"
    echo "Usage: $0 [patch|minor|major]"
    exit 1
fi

BUMP_TYPE=$1

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
    echo -e "${RED}Error: Invalid bump type. Use patch, minor, or major${NC}"
    exit 1
fi

echo -e "${GREEN}Starting release process for $BUMP_TYPE version bump...${NC}"

# 1. Ensure we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: Not on main branch (currently on $CURRENT_BRANCH)${NC}"
    read -p "Switch to main branch? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git checkout main
        git pull origin main
    else
        echo -e "${RED}Aborting: Must be on main branch to release${NC}"
        exit 1
    fi
fi

# 2. Verify required tools
command -v python >/dev/null 2>&1 || { echo -e "${RED}Error: python is required${NC}"; exit 1; }
command -v ruff >/dev/null 2>&1 || { echo -e "${RED}Error: ruff is required${NC}"; exit 1; }
python -c "import twine" 2>/dev/null || { echo -e "${RED}Error: twine module is required (pip install twine)${NC}"; exit 1; }
python -c "import build" 2>/dev/null || { echo -e "${RED}Error: build module is required (pip install build)${NC}"; exit 1; }

# 3. Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    git status --short
    exit 1
fi

# 4. Pull latest changes
echo -e "${GREEN}Pulling latest changes...${NC}"
git pull origin main

# 5. Run tests
echo -e "${GREEN}Running tests...${NC}"
if ! python -m pytest tests/ -v --tb=short; then
    echo -e "${RED}Error: Tests failed. Fix issues before releasing.${NC}"
    exit 1
fi

# 6. Run linting
echo -e "${GREEN}Running linting checks...${NC}"
if ! ruff check .; then
    echo -e "${RED}Error: Linting failed. Fix issues before releasing.${NC}"
    exit 1
fi

# 7. Bump version
echo -e "${GREEN}Bumping version ($BUMP_TYPE)...${NC}"
OLD_VERSION=$(python -c "from bitfinex_maker_kit import __version__; print(__version__)")
if [ ! -f scripts/bump_version.py ]; then
    echo -e "${RED}Error: scripts/bump_version.py not found${NC}"
    exit 1
fi
python scripts/bump_version.py $BUMP_TYPE
NEW_VERSION=$(python -c "from bitfinex_maker_kit import __version__; print(__version__)")

echo -e "${GREEN}Version bumped from $OLD_VERSION to $NEW_VERSION${NC}"

# 8. Build package to verify
echo -e "${GREEN}Building package to verify...${NC}"
rm -rf dist/ build/ *.egg-info/
python -m build

# 9. Check package with twine
echo -e "${GREEN}Checking package with twine...${NC}"
if ! python -m twine check dist/*; then
    echo -e "${RED}Error: Package validation failed${NC}"
    exit 1
fi

# 10. Commit version bump
echo -e "${GREEN}Committing version bump...${NC}"
# Add all files that bump_version.py modifies
git add bitfinex_maker_kit/__init__.py pyproject.toml
# Add CLAUDE.md only if it exists
if [ -f CLAUDE.md ]; then
    git add CLAUDE.md
fi
git commit -m "chore(release): bump to $NEW_VERSION"

# 11. Create and push tag
echo -e "${GREEN}Creating tag v$NEW_VERSION...${NC}"
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

# 12. Push changes and tag
echo -e "${GREEN}Pushing to GitHub...${NC}"
git push origin main
git push origin "v$NEW_VERSION"

echo -e "${GREEN}✅ Release process completed successfully!${NC}"
echo
echo -e "${YELLOW}GitHub Actions will now:${NC}"
echo "  1. Build the package"
echo "  2. Publish to TestPyPI (optional)"
echo "  3. Publish to PyPI"
echo "  4. Create GitHub release"
echo
echo -e "${GREEN}Monitor the workflow at:${NC}"
echo "https://github.com/0xferit/bitfinex-maker-kit/actions"
echo
echo -e "${GREEN}Once published, users can install with:${NC}"
echo "pip install bitfinex-maker-kit==$NEW_VERSION"