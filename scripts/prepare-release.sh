#!/bin/bash

# Prepare release PR from develop to main
# Usage: ./scripts/prepare-release.sh [patch|minor|major]

set -euo pipefail
trap 'echo "Error on line $LINENO" >&2' ERR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo -e "${BLUE}Preparing release with $BUMP_TYPE version bump...${NC}"

# 1. Ensure we're on develop branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo -e "${YELLOW}Warning: Not on develop branch (currently on $CURRENT_BRANCH)${NC}"
    read -p "Switch to develop branch? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git checkout develop
        git pull origin develop
    else
        echo -e "${RED}Aborting: Must be on develop branch to prepare release${NC}"
        exit 1
    fi
fi

# 2. Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: You have uncommitted changes${NC}"
    git status --short
    exit 1
fi

# 3. Pull latest changes from develop
echo -e "${GREEN}Pulling latest changes from develop...${NC}"
git pull origin develop

# 4. Pull latest from main to ensure we're up to date
echo -e "${GREEN}Fetching latest main branch...${NC}"
git fetch origin main:main

# 5. Get current version
OLD_VERSION=$(python -c "from bitfinex_maker_kit import __version__; print(__version__)")
echo -e "${GREEN}Current version: $OLD_VERSION${NC}"

# Use Python to calculate new version to handle pre-release tags correctly
NEW_VERSION=$(python -c "
import sys
version = '$OLD_VERSION'
bump_type = '$BUMP_TYPE'

# Strip any pre-release or build metadata
if '-' in version:
    version = version.split('-')[0]
if '+' in version:
    version = version.split('+')[0]

parts = version.split('.')
if len(parts) != 3:
    print(f'Error: Invalid version format: {version}', file=sys.stderr)
    sys.exit(1)

try:
    major, minor, patch = map(int, parts)
except ValueError:
    print(f'Error: Non-numeric version parts: {version}', file=sys.stderr)
    sys.exit(1)

if bump_type == 'major':
    print(f'{major + 1}.0.0')
elif bump_type == 'minor':
    print(f'{major}.{minor + 1}.0')
elif bump_type == 'patch':
    print(f'{major}.{minor}.{patch + 1}')
")

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to calculate new version${NC}"
    exit 1
fi

echo -e "${GREEN}Target version: $NEW_VERSION${NC}"

# Create release branch BEFORE any modifications
RELEASE_BRANCH="release/$NEW_VERSION"
echo -e "${GREEN}Creating release branch: $RELEASE_BRANCH${NC}"
git checkout -b "$RELEASE_BRANCH"

# 6. Verify required tools
command -v python >/dev/null 2>&1 || { echo -e "${RED}Error: python is required${NC}"; exit 1; }
command -v ruff >/dev/null 2>&1 || { echo -e "${RED}Error: ruff is required${NC}"; exit 1; }
command -v bandit >/dev/null 2>&1 || { echo -e "${RED}Error: bandit is required${NC}"; exit 1; }
python -c "import twine" 2>/dev/null || { echo -e "${RED}Error: twine module is required (pip install twine)${NC}"; exit 1; }
python -c "import build" 2>/dev/null || { echo -e "${RED}Error: build module is required (pip install build)${NC}"; exit 1; }

# 7. Run all tests BEFORE bumping version
echo -e "${GREEN}Running complete test suite...${NC}"
if ! python -m pytest tests/ -v --tb=short; then
    echo -e "${RED}Error: Tests failed. Fix issues before releasing.${NC}"
    git checkout develop  # Return to develop
    git branch -D "$RELEASE_BRANCH"  # Delete release branch
    exit 1
fi

# 8. Run linting
echo -e "${GREEN}Running linting checks...${NC}"
if ! ruff check .; then
    echo -e "${RED}Error: Linting failed. Fix issues before releasing.${NC}"
    git checkout develop  # Return to develop
    git branch -D "$RELEASE_BRANCH"  # Delete release branch
    exit 1
fi

# 9. Run security checks
echo -e "${GREEN}Running security checks...${NC}"
if ! bandit -r bitfinex_maker_kit -ll; then
    echo -e "${YELLOW}Warning: Security issues found. Review before releasing.${NC}"
fi

# 10. Now bump the version (only after tests pass)
echo -e "${GREEN}Bumping version from $OLD_VERSION to $NEW_VERSION...${NC}"
if [ ! -f scripts/bump_version.py ]; then
    echo -e "${RED}Error: scripts/bump_version.py not found${NC}"
    git checkout develop  # Return to develop
    git branch -D "$RELEASE_BRANCH"  # Delete release branch
    exit 1
fi
python scripts/bump_version.py $BUMP_TYPE

# 11. Build package to verify
echo -e "${GREEN}Building package to verify...${NC}"
rm -rf dist/ build/ *.egg-info/
python -m build

# 12. Check package with twine
echo -e "${GREEN}Checking package with twine...${NC}"
if ! python -m twine check dist/*; then
    echo -e "${RED}Error: Package validation failed${NC}"
    git checkout -- .  # Revert version bump
    git checkout develop  # Return to develop
    git branch -D "$RELEASE_BRANCH"  # Delete release branch
    exit 1
fi

# 13. Generate changelog entry
echo -e "${GREEN}Generating changelog entry...${NC}"
CHANGELOG_ENTRY="## [$NEW_VERSION] - $(date +%Y-%m-%d)

### Added
- (Add new features here)

### Changed
- Version bump from $OLD_VERSION to $NEW_VERSION

### Fixed
- (Add bug fixes here)

### Security
- (Add security updates here)
"

# Create or update CHANGELOG.md
if [ ! -f CHANGELOG.md ]; then
    echo "# Changelog" > CHANGELOG.md
    echo "" >> CHANGELOG.md
fi

# Prepend new entry to changelog
echo "$CHANGELOG_ENTRY" > CHANGELOG.tmp
cat CHANGELOG.md >> CHANGELOG.tmp
mv CHANGELOG.tmp CHANGELOG.md

# 14. Commit version bump and changelog
echo -e "${GREEN}Committing version bump and changelog...${NC}"
# Add all files that bump_version.py modifies plus changelog
git add bitfinex_maker_kit/__init__.py pyproject.toml CHANGELOG.md
# Add CLAUDE.md only if it exists
if [ -f CLAUDE.md ]; then
    git add CLAUDE.md
fi
git commit -m "chore(release): prepare $NEW_VERSION"

# 15. Push to origin
echo -e "${GREEN}Pushing $RELEASE_BRANCH to origin...${NC}"
git push origin "HEAD:$RELEASE_BRANCH"

# 16. Create PR from release branch to main
echo -e "${GREEN}Creating Pull Request...${NC}"

PR_BODY="## Release v$NEW_VERSION

### Type
$BUMP_TYPE release

### Changes
- Version bump from $OLD_VERSION to $NEW_VERSION
- See CHANGELOG.md for detailed changes

### Checklist
- [ ] All tests passing
- [ ] Linting checks pass
- [ ] Security scan complete
- [ ] Package builds successfully
- [ ] Changelog updated

### Post-Merge Actions
This PR will trigger automatic PyPI deployment when merged.

---
*Merging this PR will:*
1. Trigger GitHub Actions release workflow
2. Create git tag v$NEW_VERSION
3. Publish to PyPI
4. Create GitHub release"

# Use GitHub CLI to create PR
if command -v gh &> /dev/null; then
    if ! gh auth status >/dev/null 2>&1; then
        echo -e "${YELLOW}GitHub CLI not authenticated. Run: gh auth login${NC}"
    fi
    gh pr create \
        --title "Release v$NEW_VERSION" \
        --body "$PR_BODY" \
        --base main \
        --head "$RELEASE_BRANCH" \
        --label "release" \
        --web
else
    echo -e "${YELLOW}GitHub CLI not found. Please create PR manually:${NC}"
    echo "  From: $RELEASE_BRANCH"
    echo "  To: main"
    echo "  Title: Release v$NEW_VERSION"
    echo ""
    echo "Or install GitHub CLI:"
    echo "  brew install gh  # macOS"
    echo "  sudo apt install gh  # Ubuntu/Debian"
fi

echo -e "${GREEN}✅ Release preparation completed!${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review and update CHANGELOG.md with actual changes"
echo "2. Review the pull request"
echo "3. Get approval from reviewers"
echo "4. Merge PR to trigger automatic release"
echo
echo -e "${GREEN}The release will be automatically published to PyPI when the PR is merged.${NC}"