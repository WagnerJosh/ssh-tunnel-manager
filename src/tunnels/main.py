"""The main module for the tunnels package."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from tunnels.config import PACKAGE_NAME, VERSION
from tunnels.manage import manage_app
from tunnels.status import status_app

console: Console = Console()
app: typer.Typer = typer.Typer()
app.add_typer(status_app)
app.add_typer(manage_app)


def _version_callback(*, value: bool) -> None:
    if not value:
        return
    typer.echo(f"{PACKAGE_NAME.lower()} {VERSION}")
    raise typer.Exit


@app.callback()
def main_callback(
    *,
    _: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show the application's version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """\
    The Tunnels Application.
    """  # noqa: D205


def run_app() -> None:
    """Run the Tunnels application."""
    app()
