"""The Tunnel status module.

Maintains the cli functions for checking the status of the tunnel.
"""

from __future__ import annotations

from functools import partial
from typing import Annotated, Any

import psutil
from rich.console import Console
from rich.live import Live
from typer import Exit, Option, Typer

from tunnels.config import settings
from tunnels.output import OutputFormat, format_output
from tunnels.processes import list_process_socket_connections, list_ssh_processes

status_app: Typer = Typer()
console: Console = Console()


def create_status_rows() -> list[dict[str, Any]]:
    """Create a list of rows with the current tunnel status.

    Each row contains the tunnel name, group, PID, status, and connections.

    Returns:
        list[dict[str, str]]: A list of dictionaries representing the status of
            each tunnel.

    """
    rows: list[dict[str, Any]] = []
    processes = list(list_ssh_processes())
    for tunnel in settings.configuration.tunnels:
        row: dict[str, Any] = {
            "name": tunnel.name,
            "group": tunnel.group or "default",
            "pid": "",
            "status": "Inactive",
            "connections": "",
        }
        try:
            for proc in processes:
                if f"tunnels-{tunnel.name_tag()}" not in " ".join(proc.cmdline()):
                    continue
                row["pid"] = str(proc.pid)
                row["status"] = f"{proc.status().title()}"
                row["connections"] = (
                    list(set(list_process_socket_connections(proc))) or ""
                )
                break
        except psutil.NoSuchProcess:
            pass
        finally:
            rows.append(row)
    return rows


@status_app.command("status", help="Get the current status of the tunnels.")
def status(
    *,
    live: Annotated[
        bool,
        Option(
            "--live",
            "-l",
            help="Drop into a live status view that updates every 4 seconds.",
            is_eager=True,
        ),
    ] = False,
    format_: Annotated[
        OutputFormat,
        Option(
            "--format",
            "-f",
            help="The output format to use for the status.",
            case_sensitive=False,
            show_default=False,
        ),
    ] = OutputFormat.PANEL,
    columns: Annotated[
        list[str] | None,
        Option(
            "--column",
            "-c",
            help=(
                "The columns to display in the status output. If not specified, "
                "all columns are displayed."
            ),
            case_sensitive=False,
            show_default=False,
        ),
    ] = None,
) -> None:
    """Get the current status of the configured tunnels.

    Args:
        live (bool): If True, drop into a live status view that updates every 4
        seconds.
        format_ (OutputFormat): The output format to use for the status.
        columns (list[str] | None): The columns to display in the status output.
            If not specified, all columns are displayed.

    Raises:
        Exit: If live is True, this will raise an Exit exception to stop the
        application after displaying the live status.
    """
    output_render = partial(format_output, format_=format_, columns=columns)
    if not live:
        console.print(output_render(create_status_rows()))
        raise Exit

    with Live(refresh_per_second=4) as _live:
        while True:
            _live.update(output_render(create_status_rows()))


if __name__ == "__main__":
    status_app()
