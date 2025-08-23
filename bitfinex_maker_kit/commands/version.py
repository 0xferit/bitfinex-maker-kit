"""
Version command for displaying the application version.
"""

from .. import __version__
from ..utilities.console import print_info


def execute_version_command() -> None:
    """
    Display the current version of the application.
    """
    print_info(f"Bitfinex Maker-Kit v{__version__}")
