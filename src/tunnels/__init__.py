"""The Tunnel manager.

A simple tunnel manager that can be used to create and manage tunnels.
"""

from __future__ import annotations

from tunnels.main import run_app

__version__ = "0.1.0"
__author__ = "Joshua Wagner"
__app_name__ = "tunnels"


def main() -> None:
    """Execute the Tunnels application."""
    run_app()
