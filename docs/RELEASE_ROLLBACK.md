# Release Rollback Procedures

This document outlines procedures for handling failed releases and rolling back changes when necessary.

## Overview

While our automated semantic versioning system is designed to be reliable, issues can occasionally occur during the release process. This guide provides step-by-step procedures for different failure scenarios.

## Common Failure Scenarios

### 1. PyPI Publishing Failure

**Symptoms:**
- GitHub release created but package not on PyPI
- PyPI upload timeout or authentication error

**Recovery Steps:**

1. **Manual publish attempt:**
   ```bash
   # Trigger manual publish workflow
   gh workflow run publish.yml
   ```

2. **If manual publish fails:**
   ```bash
   # Download artifacts from failed release
   gh run download <RUN_ID> -n python-package-distributions
   
   # Manually upload to PyPI
   python -m twine upload dist/*
   ```

3. **Verify package availability:**
   ```bash
   pip install --index-url https://pypi.org/simple/ bitfinex-maker-kit==<VERSION>
   ```

### 2. Version Conflict

**Symptoms:**
- Version already exists on PyPI
- Git tag already exists

**Recovery Steps:**

1. **Delete conflicting tag (if appropriate):**
   ```bash
   # Delete local tag
   git tag -d v<VERSION>
   
   # Delete remote tag
   git push origin :refs/tags/v<VERSION>
   ```

2. **Manually bump version:**
   ```bash
   # Edit version in pyproject.toml and __init__.py
   # Create new commit with updated version
   git add pyproject.toml bitfinex_maker_kit/__init__.py
   git commit -m "fix: manually bump version to resolve conflict"
   git push origin main
   ```

### 3. Partial Release (Tag Created but No PyPI Upload)

**Symptoms:**
- Git tag exists
- GitHub release exists
- Package not on PyPI

**Recovery Steps:**

1. **Check GitHub release assets:**
   ```bash
   gh release view v<VERSION>
   ```

2. **Download and publish manually:**
   ```bash
   # Download release assets
   gh release download v<VERSION>
   
   # Upload to PyPI
   python -m twine upload *.whl *.tar.gz
   ```

### 4. Broken Release Published to PyPI

**Symptoms:**
- Package published but contains critical bugs
- Users reporting immediate failures

**Recovery Steps:**

1. **Yank the broken release (marks as unsafe):**
   ```bash
   # This prevents new installations but doesn't delete the package
   python -m twine yank bitfinex-maker-kit <VERSION>
   ```

2. **Create hotfix:**
   ```bash
   # Create hotfix branch
   git checkout -b hotfix/<VERSION>
   
   # Fix the issue
   # ... make necessary changes ...
   
   # Commit with fix type (triggers patch release)
   git commit -m "fix: critical bug in <feature>"
   
   # Merge to main via PR
   gh pr create --base main --title "Hotfix: <description>"
   ```

3. **Verify new release:**
   - Wait for automated release
   - Test new version thoroughly
   - Un-yank original if fixed in new patch

## Prevention Strategies

### 1. Pre-release Testing

Before merging to main:
- Run full test suite locally
- Test in paper trading environment
- Review all changes carefully

### 2. Gradual Rollout

For major changes:
1. Release as release candidate first
2. Test with limited users
3. Promote to stable after validation

### 3. Monitoring

After each release:
- Monitor PyPI download stats
- Check GitHub issues for problems
- Review error logs if available

## Emergency Contacts

- **PyPI Issues:** File issue at https://github.com/pypi/support
- **GitHub Actions:** Check https://www.githubstatus.com/
- **Project Maintainers:** Create issue in repository

## Rollback Checklist

- [ ] Identify failure type and scope
- [ ] Document issue in GitHub issue
- [ ] Follow appropriate recovery procedure
- [ ] Test recovery actions
- [ ] Communicate status to users if needed
- [ ] Create post-mortem document
- [ ] Update procedures based on learnings

## Version History Recovery

To restore previous working state:

```bash
# Find last known good version
git tag --sort=-version:refname | head -10

# Checkout that version
git checkout v<LAST_GOOD_VERSION>

# Create recovery branch
git checkout -b recovery/<VERSION>

# Cherry-pick safe commits if needed
git cherry-pick <COMMIT_HASH>
```

## Notes

- Never force push to main branch
- Always create issues for failed releases
- Document all manual interventions
- Consider adding manual approval step for major versions
- Keep this document updated with new scenarios