# PyPI Publishing Guide

This project uses GitHub Actions with PyPI Trusted Publishers for secure, automated package publishing.

## Setup Trusted Publisher

### 1. Configure PyPI

1. Go to https://pypi.org/manage/project/bitfinex-maker-kit/settings/publishing/
2. Add a new trusted publisher:
   - **Publisher**: GitHub
   - **Owner**: `0xferit`
   - **Repository**: `bitfinex-maker-kit`
   - **Workflow name**: `release.yml`
   - **Environment**: `pypi` (optional but recommended)

### 2. Configure TestPyPI (Optional)

1. Go to https://test.pypi.org/manage/project/bitfinex-maker-kit/settings/publishing/
2. Add trusted publisher with same settings:
   - **Environment**: `testpypi`

### 3. Configure GitHub Environments (Optional but Recommended)

1. Go to GitHub repository Settings → Environments
2. Create `pypi` environment:
   - Add protection rules (require reviewers, etc.)
   - Add environment URL: `https://pypi.org/p/bitfinex-maker-kit`
3. Create `testpypi` environment:
   - Add environment URL: `https://test.pypi.org/p/bitfinex-maker-kit`

## Publishing Process

### Automated Release (Recommended)

Use the release script for automated version bumping and publishing:

```bash
# For bug fixes (x.x.Z)
./scripts/release.sh patch

# For new features (x.Y.x)
./scripts/release.sh minor

# For breaking changes (X.x.x)
./scripts/release.sh major
```

The script will:
1. Ensure you're on main branch
2. Run tests and linting
3. Bump version using `scripts/bump_version.py` (Python 3.12+, pip install build, twine)
4. Build and validate package
5. Commit and tag the version
6. Push to GitHub
7. Trigger GitHub Actions workflow

### Manual Release

If you prefer manual control:

```bash
# 1. Bump version
python scripts/bump_version.py patch

# 2. Commit changes
git add -A
git commit -m "chore: bump version to X.Y.Z"

# 3. Create tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"

# 4. Push to GitHub
git push origin main
git push origin vX.Y.Z
```

GitHub Actions will automatically:
- Build the package
- Publish to TestPyPI (if configured)
- Publish to PyPI
- Create GitHub release with artifacts

## Manual Publishing (Fallback)

If GitHub Actions fails, you can publish manually:

```bash
# 1. Build package
rm -rf dist/ build/
python -m build

# 2. Check package
twine check dist/*

# 3. Upload to TestPyPI
twine upload --repository testpypi dist/*

# 4. Test installation
pip install --index-url https://test.pypi.org/simple/ bitfinex-maker-kit

# 5. Upload to PyPI
twine upload dist/*
```

## Benefits of Trusted Publishers

1. **No API tokens in GitHub Secrets** - Uses OIDC for authentication
2. **Improved security** - No long-lived credentials
3. **Audit trail** - All publishes linked to GitHub Actions
4. **Environment protection** - Can require approval for production releases

## Troubleshooting

### Common Issues

1. **"No trusted publisher configured"**
   - Ensure the workflow name matches exactly
   - Check repository owner and name spelling

2. **"Environment not found"**
   - Create environments in GitHub Settings → Environments
   - Or remove environment configuration from workflow

3. **"Package already exists"**
   - Version already published - bump to next version
   - Delete package version from TestPyPI if testing

### Verification

After publishing, verify the package:

```bash
# Install latest version
pip install --upgrade bitfinex-maker-kit

# Check version
python -c "import bitfinex_maker_kit; print(bitfinex_maker_kit.__version__)"

# Test basic functionality
python -m bitfinex_maker_kit test
```

## Resources

- [PyPI Trusted Publishers Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [PyPA Publishing Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)