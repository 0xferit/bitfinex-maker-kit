#!/usr/bin/env python3
"""
Version Bump Script for Bitfinex Maker-Kit

Automatically bumps version numbers following semantic versioning (semver) across all
relevant files in the project. Supports major, minor, and patch version bumps.

Usage:
    python scripts/bump_version.py patch    # 4.0.0 -> 4.0.1
    python scripts/bump_version.py minor    # 4.0.0 -> 4.1.0
    python scripts/bump_version.py major    # 4.0.0 -> 5.0.0
    python scripts/bump_version.py --show   # Show current version
    python scripts/bump_version.py --help   # Show help

Files updated:
    - pyproject.toml
    - bitfinex_maker_kit/__init__.py
    - bitfinex_maker_kit/commands/monitor.py
    - CLAUDE.md
"""

import argparse
import re
import sys
from pathlib import Path


class VersionBumper:
    """Handles semantic version bumping across multiple files."""

    def __init__(self, project_root: Path):
        """Initialize with project root directory."""
        self.project_root = project_root
        self.version_files = {
            "pyproject.toml": {
                "path": project_root / "pyproject.toml",
                "pattern": r'version = "([0-9]+\.[0-9]+\.[0-9]+)"',
                "replacement": r'version = "{new_version}"'
            },
            "__init__.py": {
                "path": project_root / "bitfinex_maker_kit" / "__init__.py",
                "pattern": r'__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"',
                "replacement": r'__version__ = "{new_version}"'
            },
            "monitor.py": {
                "path": project_root / "bitfinex_maker_kit" / "commands" / "monitor.py",
                "pattern": r'footer = f"v([0-9]+\.[0-9]+\.[0-9]+)',
                "replacement": r'footer = f"v{new_version}'
            },
            "CLAUDE.md": {
                "path": project_root / "CLAUDE.md",
                "pattern": r'- \*\*Version\*\*: ([0-9]+\.[0-9]+\.[0-9]+)',
                "replacement": r'- **Version**: {new_version}'
            }
        }

    def get_current_version(self) -> str:
        """Get current version from __init__.py."""
        init_file = self.version_files["__init__.py"]["path"]
        if not init_file.exists():
            raise FileNotFoundError(f"Version file not found: {init_file}")

        content = init_file.read_text(encoding='utf-8')
        pattern = self.version_files["__init__.py"]["pattern"]
        match = re.search(pattern, content)

        if not match:
            raise ValueError(f"Version pattern not found in {init_file}")

        return match.group(1)

    def parse_version(self, version: str) -> tuple[int, int, int]:
        """Parse version string into major, minor, patch tuple."""
        try:
            parts = version.split('.')
            if len(parts) != 3:
                raise ValueError("Version must have exactly 3 parts")
            return tuple(int(part) for part in parts)
        except ValueError as e:
            raise ValueError(f"Invalid version format '{version}': {e}") from e

    def format_version(self, major: int, minor: int, patch: int) -> str:
        """Format version tuple into string."""
        return f"{major}.{minor}.{patch}"

    def bump_version(self, version_type: str) -> str:
        """Bump version according to semantic versioning rules."""
        current = self.get_current_version()
        major, minor, patch = self.parse_version(current)

        if version_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_type == "minor":
            minor += 1
            patch = 0
        elif version_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid version type: {version_type}")

        new_version = self.format_version(major, minor, patch)
        print(f"Bumping version: {current} -> {new_version} ({version_type})")
        return new_version

    def update_file(self, file_key: str, new_version: str) -> bool:
        """Update version in a specific file."""
        file_info = self.version_files[file_key]
        file_path = file_info["path"]

        if not file_path.exists():
            print(f"⚠️  Warning: File not found: {file_path}")
            return False

        try:
            content = file_path.read_text(encoding='utf-8')
            pattern = file_info["pattern"]
            replacement = file_info["replacement"].format(new_version=new_version)

            # Check if pattern exists
            if not re.search(pattern, content):
                print(f"⚠️  Warning: Version pattern not found in {file_path}")
                return False

            # Perform replacement
            new_content = re.sub(pattern, replacement, content)

            # Verify the replacement worked
            if content == new_content:
                print(f"⚠️  Warning: No changes made to {file_path}")
                return False

            # Write updated content
            file_path.write_text(new_content, encoding='utf-8')
            print(f"✅ Updated: {file_path}")
            return True

        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
            return False

    def update_all_files(self, new_version: str) -> bool:
        """Update version in all files."""
        print(f"\n📝 Updating version to {new_version} in all files...")

        success_count = 0
        total_files = len(self.version_files)

        for file_key in self.version_files:
            if self.update_file(file_key, new_version):
                success_count += 1

        print(f"\n📊 Updated {success_count}/{total_files} files successfully")

        if success_count == total_files:
            print("🎉 All files updated successfully!")
            return True
        else:
            print("⚠️  Some files were not updated. Please review the warnings above.")
            return False

    def validate_files(self) -> bool:
        """Validate that all version files exist and have the correct patterns."""
        print("🔍 Validating version files...")

        all_valid = True
        for _file_key, file_info in self.version_files.items():
            file_path = file_info["path"]

            if not file_path.exists():
                print(f"❌ Missing file: {file_path}")
                all_valid = False
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                pattern = file_info["pattern"]

                if not re.search(pattern, content):
                    print(f"❌ Version pattern not found in: {file_path}")
                    all_valid = False
                else:
                    print(f"✅ Valid: {file_path}")

            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")
                all_valid = False

        return all_valid

    def show_current_version(self):
        """Display current version information."""
        try:
            current = self.get_current_version()
            major, minor, patch = self.parse_version(current)

            print("📋 Current Version Information")
            print(f"   Current: {current}")
            print(f"   Major: {major}, Minor: {minor}, Patch: {patch}")
            print()
            print("🔮 Next Version Previews:")
            print(f"   patch: {current} -> {self.format_version(major, minor, patch + 1)}")
            print(f"   minor: {current} -> {self.format_version(major, minor + 1, 0)}")
            print(f"   major: {current} -> {self.format_version(major + 1, 0, 0)}")

        except Exception as e:
            print(f"❌ Error getting current version: {e}")
            return False

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bump version numbers following semantic versioning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bump_version.py patch    # Bug fixes (4.0.0 -> 4.0.1)
  python scripts/bump_version.py minor    # New features (4.0.0 -> 4.1.0)
  python scripts/bump_version.py major    # Breaking changes (4.0.0 -> 5.0.0)
  python scripts/bump_version.py --show   # Show current version info
  python scripts/bump_version.py --validate # Validate version files

Semantic Versioning (semver.org):
  MAJOR: Breaking changes that require API updates
  MINOR: New features that are backward compatible
  PATCH: Bug fixes that are backward compatible
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Type of version bump to perform"
    )
    group.add_argument(
        "--show",
        action="store_true",
        help="Show current version information"
    )
    group.add_argument(
        "--validate",
        action="store_true",
        help="Validate that all version files exist and have correct patterns"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making actual changes"
    )

    args = parser.parse_args()

    # Find project root (directory containing pyproject.toml)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if not (project_root / "pyproject.toml").exists():
        print("❌ Error: Could not find pyproject.toml in project root")
        print(f"   Looking in: {project_root}")
        sys.exit(1)

    bumper = VersionBumper(project_root)

    # Handle different modes
    if args.show:
        print("🔍 Version Information\n")
        success = bumper.show_current_version()
        sys.exit(0 if success else 1)

    if args.validate:
        print("🔍 Validating Version Files\n")
        success = bumper.validate_files()
        print(f"\n{'✅ All files valid!' if success else '❌ Validation failed!'}")
        sys.exit(0 if success else 1)

    # Perform version bump
    try:
        # Validate files first
        if not bumper.validate_files():
            print("\n❌ File validation failed. Please fix the issues above.")
            sys.exit(1)

        # Get new version
        new_version = bumper.bump_version(args.bump_type)

        if args.dry_run:
            print(f"\n🔍 DRY RUN: Would update version to {new_version}")
            print("   Use without --dry-run to apply changes")
            sys.exit(0)

        # Update all files
        success = bumper.update_all_files(new_version)

        if success:
            print(f"\n🎉 Version successfully bumped to {new_version}")
            print("\n📝 Next steps:")
            print("   1. Review the changes: git diff")
            print("   2. Test the application")
            print(f"   3. Commit: git add -A && git commit -m 'Bump version to {new_version}'")
            print(f"   4. Tag: git tag v{new_version}")
            sys.exit(0)
        else:
            print("\n❌ Version bump failed")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
