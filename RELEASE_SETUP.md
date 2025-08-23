# Release Setup Instructions

## Current Status
- **Version**: 4.2.50 (current release on PyPI)
- **PyPI Version**: 4.2.50 (last successful release)
- **Automated Release**: Configured with semantic-release

## Automated Release Configuration

The project uses semantic-release for automated versioning. When merging to main:
- Conventional commits trigger automatic version bumps
- `feat:` commits trigger minor version bumps
- `fix:` commits trigger patch version bumps
- Version is updated in pyproject.toml, __init__.py, and CLAUDE.md
- Automatic PyPI publishing via trusted publisher

## Solution Options

### Option 1: Configure PyPI Trusted Publisher (Recommended)
1. Go to https://pypi.org/manage/project/bitfinex-maker-kit/settings/publishing/
2. Add a new publisher:
   - Owner: `0xferit`
   - Repository: `bitfinex-maker-kit`
   - Workflow name: `release.yml`
   - Environment name: `pypi` (optional but recommended)
3. Save the configuration
4. Re-run the failed workflow or trigger a new release

### Option 2: Use API Token (Alternative)
1. Generate an API token at https://pypi.org/manage/account/token/
2. Add it as a GitHub secret named `PYPI_API_TOKEN`
3. Update `.github/workflows/release.yml`:
   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release/v1
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

### Option 3: Manual Release (Temporary)
```bash
# Ensure you're on main branch with latest code
git checkout main
git pull origin main

# Build the distribution
python -m pip install --upgrade build
python -m build

# Upload to PyPI (requires PyPI credentials)
python -m pip install --upgrade twine
python -m twine upload dist/*

# Create GitHub tag and release
git tag -a v4.2.50 -m "Release version 4.2.50"
git push origin v4.2.50

# Create GitHub release via CLI
gh release create v4.2.50 \
  --title "Release v4.2.50: CI Workflow Consolidation" \
  --notes "See PR #16 for details" \
  dist/*
```

## Verification
After successful release:
1. Check PyPI: https://pypi.org/project/bitfinex-maker-kit/4.2.50/
2. Verify installation: `pip install bitfinex-maker-kit==4.2.50`
3. Check GitHub releases: https://github.com/0xferit/bitfinex-maker-kit/releases

## Future Releases
Once Trusted Publisher is configured, releases will be automatic when:
- A PR from `develop` to `main` is merged
- The PR has the `release` label or contains version bump
- All CI checks pass

The workflow will:
1. Build the package
2. Publish to PyPI
3. Create GitHub release with tag
4. Upload distribution files as release assets