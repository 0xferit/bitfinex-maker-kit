# Branching Strategy & Release Process

## Git Flow Overview

This project follows a modified Git Flow branching strategy:

```
feature/* → develop → release/* → main → PyPI
```

### Branch Types

- **`main`**: Production branch - releases to PyPI
- **`develop`**: Integration branch - latest development code
- **`feature/*`**: Feature branches - individual features/fixes
- **`release/*`**: Release preparation branches
- **`hotfix/*`**: Emergency production fixes

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# Work on feature
# ... make changes ...

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push feature branch
git push origin feature/my-new-feature

# Create PR to develop
gh pr create --base develop
```

### 2. Develop Branch

- All feature branches merge into `develop`
- Continuous integration runs on every push
- Integration tests run on PRs to develop

## Release Process

### Automated Release Flow

```
1. develop branch has accumulated features
2. Run prepare-release script
3. Script creates release branch and PR to main
4. PR merge triggers automatic PyPI deployment
```

### Step-by-Step Release

#### 1. Prepare Release from Develop

```bash
# On develop branch with all features ready
./scripts/prepare-release.sh minor  # or patch/major
```

This script will:
- Ensure you're on develop branch
- Run all tests and checks
- Bump version number
- Update CHANGELOG.md
- Create release branch
- Push to GitHub
- Create PR from release branch to main

#### 2. Review Release PR

The PR will include:
- Version bump changes
- Updated changelog
- Release checklist
- Automatic "release" label

#### 3. Merge to Main

When the PR is merged to main:
1. GitHub Actions checks for release label
2. Builds Python package
3. Creates git tag (v.X.Y.Z)
4. Publishes to PyPI via Trusted Publisher
5. Creates GitHub release with artifacts

### Manual Release Trigger

If needed, you can manually trigger a release:

```bash
# From GitHub Actions page
# Run "Publish to PyPI" workflow manually
```

## Version Management

### Version Bump Types

- **`patch`**: Bug fixes (0.0.X)
- **`minor`**: New features (0.X.0)
- **`major`**: Breaking changes (X.0.0)

### Version Files

Version is synchronized across:
- `bitfinex_maker_kit/__init__.py`
- `pyproject.toml`
- `setup.py`

## Hotfix Process

For emergency production fixes:

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# Fix issue and bump patch version
python scripts/bump_version.py patch

# Commit and push
git add .
git commit -m "hotfix: fix critical issue"
git push origin hotfix/critical-fix

# Create PR to main
gh pr create --base main --label "release,hotfix"

# After merge, cherry-pick to develop
git checkout develop
git cherry-pick <commit-hash>
git push origin develop
```

## CI/CD Pipeline

### Develop Branch CI

Runs on every push and PR to develop:
- Python 3.12+ tests
- Linting (ruff)
- Type checking (mypy)
- Security scan (bandit)
- Coverage report
- Package build verification

### Main Branch CD

Runs when PR merged to main:
1. Check for release label
2. Build distribution
3. Create git tag
4. Publish to PyPI
5. Create GitHub release

## Best Practices

### Commit Messages

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Test changes
- `chore:` Maintenance

### PR Guidelines

1. Always PR to develop (not main)
2. Include tests for new features
3. Update documentation
4. Pass all CI checks
5. Get review approval

### Release Checklist

Before releasing:
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Security scan clean
- [ ] Package builds successfully
- [ ] Version bumped appropriately

## Environment Configuration

### Required GitHub Settings

1. **Branch Protection Rules**
   - `main`: Require PR reviews, status checks
   - `develop`: Require status checks

2. **Environments**
   - `pypi`: Production PyPI deployment
   - `testpypi`: Test PyPI deployment (optional)

3. **PyPI Trusted Publisher**
   - Configure at pypi.org/manage/project
   - Repository: `0xferit/bitfinex-maker-kit`
   - Workflow: `release.yml`

## Troubleshooting

### Release Not Triggering

Check:
1. PR has "release" label
2. PR is from `develop` or `release/*` to `main`
3. GitHub Actions enabled
4. Trusted Publisher configured

### Version Conflicts

```bash
# Reset version files
git checkout develop
python scripts/bump_version.py patch
git add .
git commit -m "chore: fix version sync"
```

### Failed PyPI Upload

1. Check PyPI Trusted Publisher settings
2. Verify workflow permissions
3. Ensure version not already published
4. Check package validation with `twine check`