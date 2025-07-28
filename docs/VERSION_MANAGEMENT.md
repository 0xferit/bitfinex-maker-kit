# Version Management

This document describes the version management system for the Bitfinex Maker-Kit project.

## Overview

The project uses **Semantic Versioning (semver)** for version numbers in the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Breaking changes that require API updates
- **MINOR**: New features that are backward compatible  
- **PATCH**: Bug fixes that are backward compatible

## Version Locations

Version numbers are maintained in these files:
- `pyproject.toml` - Package version for pip/setuptools
- `bitfinex_maker_kit/__init__.py` - Python package version
- `bitfinex_maker_kit/commands/monitor.py` - UI display version
- `CLAUDE.md` - Documentation version

## Usage

### Quick Commands

```bash
# Show current version
./scripts/version show

# Bump patch version (bug fixes)
./scripts/version patch

# Bump minor version (new features) 
./scripts/version minor

# Bump major version (breaking changes)
./scripts/version major

# Validate version files
./scripts/version validate
```

### Advanced Usage

```bash
# Dry run (see what would change)
python scripts/bump_version.py patch --dry-run

# Full help
python scripts/bump_version.py --help
```

## Workflow

### 1. Making Changes

After implementing features or fixes:

```bash
# Check current version
./scripts/version show

# Choose appropriate bump type:
# - patch: Bug fixes, small improvements
# - minor: New features, enhancements  
# - major: Breaking changes, API changes

./scripts/version patch  # or minor/major
```

### 2. Reviewing Changes

```bash
# Review what was changed
git diff

# Verify version in key files
grep -r "4.0.1" pyproject.toml bitfinex_maker_kit/
```

### 3. Committing and Tagging

```bash
# Commit version bump
git add -A
git commit -m "Bump version to 4.0.1"

# Create version tag
git tag v4.0.1

# Push changes and tags
git push origin main
git push origin v4.0.1
```

## Version Bump Examples

### Bug Fix (Patch)
```bash
# Example: Fixed WebSocket connection timeout
./scripts/version patch
# 4.0.0 -> 4.0.1
```

### New Feature (Minor)
```bash
# Example: Added new trading command
./scripts/version minor  
# 4.0.1 -> 4.1.0
```

### Breaking Change (Major)
```bash
# Example: Changed CLI command structure
./scripts/version major
# 4.1.0 -> 5.0.0
```

## Automation

The version bump script automatically:

1. **Validates** all version files exist and have correct patterns
2. **Updates** version in all relevant files simultaneously
3. **Provides** next steps for git operations
4. **Prevents** inconsistent version states

## Troubleshooting

### Script Fails to Find Files

```bash
# Validate all files are present
./scripts/version validate
```

### Version Pattern Not Found

Check that the version format in files matches the expected pattern:
- `version = "X.Y.Z"` in pyproject.toml
- `__version__ = "X.Y.Z"` in __init__.py
- `v{version}` in monitor.py footer
- `**Version**: X.Y.Z` in CLAUDE.md

### Dry Run First

Always test with dry run when unsure:

```bash
python scripts/bump_version.py patch --dry-run
```

## Integration with CI/CD

The version bump script is designed to integrate with automated workflows:

```yaml
# Example GitHub Actions step
- name: Bump version
  run: |
    ./scripts/version patch
    git config user.name "github-actions"
    git config user.email "actions@github.com"
    git add -A
    git commit -m "Automated version bump"
    git push
```

## Best Practices

1. **Always validate** before bumping: `./scripts/version validate`
2. **Use dry runs** for testing: `--dry-run` flag
3. **Commit version bumps** separately from feature commits
4. **Tag versions** immediately after committing
5. **Test thoroughly** before version bumps
6. **Document breaking changes** in commit messages for major bumps

## Script Architecture

The version bump system consists of:

- `scripts/bump_version.py` - Main Python script with full functionality
- `scripts/version` - Simple bash wrapper for common operations
- Automatic file detection and validation
- Semantic versioning logic
- Comprehensive error handling

This ensures version consistency across all project files and reduces manual version management errors.