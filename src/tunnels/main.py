"""The main module for the tunnels package."""

from __future__ import annotations

from importlib.metadata import metadata

import typer
from rich.console import Console

from tunnels.manage import manage_app
from tunnels.status import status_app

console: Console = Console()
app: typer.Typer = typer.Typer()
app.add_typer(status_app)
app.add_typer(manage_app)
meta = metadata("tunnels")


def _version_callback(*, value: bool) -> None:
    if not value:
        return
    typer.echo(f"{meta['name'].lower()} {meta['version']}")
    raise typer.Exit


@app.callback()
def main_callback(
    *,
    _: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """\
    The Tunnels Application.
    """  # noqa: D205


def run_app() -> None:
    """Run the Tunnels application."""
    app()
