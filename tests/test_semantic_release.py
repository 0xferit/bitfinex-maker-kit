"""Tests for semantic release configuration and workflow validation."""

import re
import tomllib
from pathlib import Path


def test_semantic_release_configuration():
    """Validate semantic release configuration in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    # Check semantic release configuration exists
    assert "semantic_release" in config["tool"], "Missing semantic release configuration"

    sr_config = config["tool"]["semantic_release"]

    # Validate required fields
    assert sr_config["branch"] == "main", "Release branch should be main"
    assert "pyproject.toml:project.version" in sr_config["version_toml"]
    assert "bitfinex_maker_kit/__init__.py:__version__" in sr_config["version_variable"]
    assert sr_config["tag_format"] == "v{version}"
    assert sr_config["commit_parser"] == "conventional_commits"

    # Validate commit parser options
    parser_opts = sr_config["commit_parser_options"]
    assert "feat" in parser_opts["minor_types"]
    assert "fix" in parser_opts["patch_types"]
    assert "breaking" in parser_opts["major_types"]


def test_conventional_commit_patterns():
    """Test conventional commit message patterns."""
    # Valid conventional commits
    valid_commits = [
        "feat: add new trading strategy",
        "fix: resolve order cancellation bug",
        "feat!: change API response format",
        "fix(orders): correct price validation",
        "chore: update dependencies",
        "docs: improve README",
        "test: add unit tests for market maker",
        "refactor: simplify order validation logic",
        "perf: optimize WebSocket message handling",
    ]

    # Invalid conventional commits
    invalid_commits = [
        "Added new feature",
        "Fixed bug",
        "feat add new feature",  # Missing colon
        "feat :",  # Missing description
        "FEAT: add feature",  # Wrong case
    ]

    # Conventional commit regex pattern
    pattern = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
        r"(\(.+\))?!?: .+"
    )

    for commit in valid_commits:
        assert pattern.match(commit), f"Valid commit failed: {commit}"

    for commit in invalid_commits:
        assert not pattern.match(commit), f"Invalid commit passed: {commit}"


def test_version_format():
    """Test semantic version format validation."""
    import bitfinex_maker_kit

    version = bitfinex_maker_kit.__version__

    # Validate semantic version format (X.Y.Z)
    version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
    assert version_pattern.match(version), f"Invalid version format: {version}"

    # Check version components are integers
    major, minor, patch = version.split(".")
    assert major.isdigit(), f"Major version not a number: {major}"
    assert minor.isdigit(), f"Minor version not a number: {minor}"
    assert patch.isdigit(), f"Patch version not a number: {patch}"


def test_version_consistency():
    """Ensure version is consistent across all files."""
    import bitfinex_maker_kit

    # Get version from __init__.py
    init_version = bitfinex_maker_kit.__version__

    # Get version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)
    pyproject_version = config["project"]["version"]

    # Versions should match
    assert init_version == pyproject_version, (
        f"Version mismatch: __init__.py={init_version}, pyproject.toml={pyproject_version}"
    )


def test_workflow_files_exist():
    """Ensure required workflow files exist."""
    workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"

    required_workflows = [
        "semantic-release.yml",
        "publish.yml",
        "ci.yml",
    ]

    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        assert workflow_path.exists(), f"Missing workflow: {workflow}"

    # Ensure deprecated workflow is marked as such
    deprecated = workflows_dir / "version-bump.yml.deprecated"
    old_workflow = workflows_dir / "version-bump.yml"

    assert not old_workflow.exists(), "Old version-bump.yml should be removed"
    assert deprecated.exists(), "Deprecated workflow should be preserved"


def test_commit_type_version_mapping():
    """Test that commit types map to correct version bumps."""
    commit_type_mapping = {
        # Commit type -> Expected version bump
        "fix": "patch",
        "feat": "minor",
        "breaking": "major",
        "perf": "patch",
        "refactor": "patch",
        "chore": None,  # No version bump
        "docs": None,  # No version bump
        "test": None,  # No version bump
    }

    # Load configuration
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    parser_opts = config["tool"]["semantic_release"]["commit_parser_options"]

    for commit_type, expected_bump in commit_type_mapping.items():
        if expected_bump == "major":
            assert commit_type in parser_opts["major_types"]
        elif expected_bump == "minor":
            assert commit_type in parser_opts["minor_types"]
        elif expected_bump == "patch":
            assert commit_type in parser_opts["patch_types"]
        # Types that don't trigger version bumps shouldn't be in any list
        elif expected_bump is None:
            assert commit_type not in parser_opts.get("major_types", [])
            assert commit_type not in parser_opts.get("minor_types", [])
            assert commit_type not in parser_opts.get("patch_types", [])
