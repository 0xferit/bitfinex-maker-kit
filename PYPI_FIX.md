# PyPI Publishing Fix Instructions

## Current Issue
The semantic-release workflow fails to publish to PyPI with "invalid-publisher" error.

## Root Cause
Mismatch between PyPI trusted publisher configuration and the GitHub workflow:

### PyPI Configuration (Current)
- Repository: `0xferit/bitfinex-maker-kit`
- Workflow: `publish.yml`
- Environment: `pypi`

### Semantic-Release Workflow
- Repository: `0xferit/bitfinex-maker-kit` ✅
- Workflow: `semantic-release.yml` ❌ (mismatch!)
- Environment: `pypi` ✅

## Solution
Update PyPI trusted publisher configuration:

1. Go to: https://pypi.org/manage/project/bitfinex-maker-kit/settings/publishing/
2. Find the existing trusted publisher
3. Edit it to change:
   - Workflow: `.github/workflows/semantic-release.yml` (from `publish.yml`)
   - Keep everything else the same

OR add a second trusted publisher:
- Repository: `0xferit/bitfinex-maker-kit`
- Workflow: `.github/workflows/semantic-release.yml`
- Environment: `pypi`

## Why This Works
The environment specification in the workflow (lines 23-25) adds `environment:pypi` to the OIDC token claims, which matches what PyPI expects. The only mismatch is the workflow filename.

## After Fix
Once PyPI configuration is updated, the semantic-release workflow will successfully:
1. Create new version tags
2. Publish to PyPI automatically
3. Create GitHub releases

## Alternative Approach (Not Recommended)
We could rename `semantic-release.yml` to `publish.yml`, but this would be confusing since they serve different purposes:
- `semantic-release.yml`: Automated releases on push to main
- `publish.yml`: Manual release via workflow_dispatch