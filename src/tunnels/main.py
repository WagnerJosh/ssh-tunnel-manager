"""The main module for the tunnels package."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from hashlib import sha256
from importlib.metadata import metadata

import psutil
import rich.box
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

from tunnels.config import Config, create_tunnel_cmd

console: Console = Console()
app: typer.Typer = typer.Typer()

meta = metadata("tunnels")


tunnel_active_table: Table = Table(
    show_header=True,
    header_style="bold yellow dim",
    show_lines=True,
    box=None,
    expand=True,
)
tunnel_active_table.add_column("PID", style="dim", width=12)
tunnel_active_table.add_column("CMD")
tunnel_active_table.add_column("Status")
tunnel_active_table.add_column("Connections")


def _version_callback(*, value: bool) -> None:
    if not value:
        return
    typer.echo(f"{meta['name'].lower()} {meta['version']}")
    raise typer.Exit


@app.command("start", help="Start a tunnel or tunnel group.")
def start(
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="The name of the tunnel.",
    ),
    group: str | None = typer.Option(
        None,
        "--group",
        "-g",
        help="The name of the tunnel group.",
    ),
) -> None:
    """Start a tunnel or tunnel group.

    Args:
        name (str | None): The name of the tunnel.
        group (str | None): The name of the tunnel group.

    Raises:
        typer.BadParameter: Only one of --name or --group must be specified.
    """
    settings = Config.load()
    console.print(f"Name: {name} | Group: {group}")
    if not (bool(name) ^ bool(group)):
        msg = "Only one of --name or --group must be specified."
        raise typer.BadParameter(msg)
    tunnel = name or group
    print(f"Starting tunnel: {tunnel}")
    tuns: list[list[str]] = [
        create_tunnel_cmd(tunnel) for tunnel in settings.tunnels or []
    ]
    for _group in settings.groups or []:
        tuns.extend(create_tunnel_cmd(tunnel) for tunnel in _group.tunnels or [])
    print(tuns)
    for tun in tuns:
        console.print(f"{tun}: {sha256(' '.join(tun).encode()).hexdigest()[:8]}")
        subprocess.run(tun)  # noqa: S603


@app.command("list", help="List the tunnels.")
def _list() -> None:
    """List the tunnels."""
    processes: Generator[psutil.Process] = (
        p for p in psutil.process_iter() if p.name() == "ssh"
    )
    for proc in processes:
        all_connections = proc.net_connections(kind="inet4")
        connections = [
            f"{conn.laddr.ip}:{conn.laddr.port}"
            for conn in all_connections
            if conn.laddr
        ]
        connections.extend([
            f"{conn.raddr.ip}:{conn.raddr.port}"
            for conn in all_connections
            if conn.raddr
        ])
        connections.sort()
        tunnel_active_table.add_row(
            str(proc.pid),
            " ".join(proc.cmdline()),
            proc.status(),
            "\n".join(set(connections)) or "",
        )
        console.print(proc.as_dict())
    console.print(
        Panel(
            tunnel_active_table,
            title="[bold]Active Tunnels",
            title_align="left",
            border_style="dim",
        ),
    )
    # IF THE STATUS CHANGES TO CLOSE OR CLOSE_WAIT, THEN THE TUNNEL IS CLOSED
    # WE NEED TO CHECK IF WE SHOULD REESTABLISH THE TUNNEL
    # IF THE TUNNEL IS CLOSED, THEN REESTABLISH IT


@app.callback()
def version(
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
    return
