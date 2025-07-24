"""The Tunnel status module.

Maintains the cli functions for checking the status of the tunnel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import rich
from pydantic import BaseModel
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from typer import Exit, Option, Typer, echo

from tunnels.config import settings
from tunnels.output import ENCODER, OutputFormat
from tunnels.processes import list_process_socket_connections, list_ssh_processes

status_app: Typer = Typer()
console: Console = Console()


class StatusEntry(BaseModel):
    """A model for tunnel status entries."""

    name: str
    pid: str
    status: str
    connections: str


def create_status_rows() -> list[StatusEntry]:
    """Create a list of rows with the current tunnel status."""
    rows: list[StatusEntry] = []
    for tunnel in settings.configuration.tunnels:
        row: StatusEntry = StatusEntry(
            name=tunnel.name,
            pid="-",
            status="Inactive",
            connections="-",
        )
        for proc in list_ssh_processes():
            if f"tunnels-{tunnel.name_tag()}" in " ".join(proc.cmdline()):
                row.pid = str(proc.pid)
                row.status = f"{proc.status().title()}"
                row.connections = (
                    "\n".join(set(list_process_socket_connections(proc))) or "-"
                )
                break
        rows.append(row)
    return rows


# def create_status_table() -> Table:
#     """Create a status table with the current tunnel status."""
#     table = Table(
#         show_header=True,
#         header_style="bold yellow dim",
#         show_lines=True,
#         box=None,
#         expand=True,
#     )
#     table.add_column("Tunnel Name")
#     table.add_column("PID", style="dim")
#     table.add_column("Status")
#     table.add_column("Connections")
#     for row in create_status_rows():
#         table.add_row(row["name"], row["pid"], row["status"], row["connections"])
#     return table


@status_app.command("status", help="Get the current status of the configured tunnels.")
def status(
    *,
    live: bool = Option(
        False,  # noqa: FBT003
        "--live",
        "-l",
        help="Drop into a live status view that updates every 4 seconds.",
        is_eager=True,
    ),
) -> None:
    """List the tunnels."""
    output = settings.global_options["output"]
    rich.print("output: ", output)
    if live:
        with Live(refresh_per_second=4) as _live:
            while True:
                if output:
                    _live.update(ENCODER[output](create_status_rows()))
                else:
                    _live.update(
                        Panel(
                            ENCODER[OutputFormat.TABLE](create_status_rows()),
                            title="[bold]Active Tunnels",
                            title_align="left",
                            border_style="dim",
                        ),
                    )
        raise Exit

    if output:
        console.print(ENCODER[output](create_status_rows()))
    else:
        console.print(
            Panel(
                ENCODER[OutputFormat.TABLE](create_status_rows()),
                title="[bold]Active Tunnels",
                title_align="left",
                border_style="dim",
            ),
        )


# @status_app.command("live", help="Get the current status of the configured tunnels.")
# def live_status() -> None:
#     """Test the status command."""
#     if output := settings.global_options["output"]:
#         echo(ENCODER[output](create_status_rows()))
#         return
#     with Live(refresh_per_second=4) as live:
#         while True:
#             live.update(
#                 Panel(
#                     create_status_table(),
#                     title="[bold]Active Tunnels",
#                     title_align="left",
#                     border_style="dim",
#                 ),
#             )


if __name__ == "__main__":
    status_app()
