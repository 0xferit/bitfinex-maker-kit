#!/usr/bin/env python3
"""
Test Python version requirement for the maker-kit package.
"""

import sys
from pathlib import Path


def test_python_version_requirement():
    """Test that the package requires Python 3.12+"""

    # Get current Python version
    current_version = sys.version_info
    print(
        f"Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}"
    )

    # Verify current Python meets requirement
    if current_version >= (3, 12):
        print("✅ Current Python version meets requirement (>=3.12)")
    else:
        print("❌ Current Python version does not meet requirement (>=3.12)")
        return False

    # Test package metadata shows correct requirement
    try:
        # Read pyproject.toml to verify requirement
        project_root = Path(__file__).parent.parent
        pyproject_path = project_root / "pyproject.toml"

        with open(pyproject_path) as f:
            content = f.read()

        if 'requires-python = ">=3.12"' in content:
            print("✅ pyproject.toml correctly specifies Python >=3.12 requirement")
        else:
            print("❌ pyproject.toml does not specify correct Python requirement")
            return False

        # Verify classifiers only include 3.12+
        if '"Programming Language :: Python :: 3.8"' in content:
            print("❌ pyproject.toml still includes old Python 3.8 classifier")
            return False
        if '"Programming Language :: Python :: 3.12"' in content:
            print("✅ pyproject.toml includes Python 3.12 classifier")
        else:
            print("❌ pyproject.toml missing Python 3.12 classifier")
            return False

    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return False

    print("✅ All Python version requirement tests passed!")
    return True


if __name__ == "__main__":
    success = test_python_version_requirement()
    sys.exit(0 if success else 1)
