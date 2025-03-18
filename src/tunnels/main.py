"""The main module for the tunnels package."""

from __future__ import annotations

import shlex
import shutil
import socket
import subprocess
from collections.abc import Generator
from importlib.metadata import metadata
from typing import Literal

import psutil
import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tunnels.config import Config, Tunnel

console: Console = Console()
app: typer.Typer = typer.Typer()

meta = metadata("tunnels")
settings = Config.load()


def _version_callback(*, value: bool) -> None:
    if not value:
        return
    typer.echo(f"{meta['name'].lower()} {meta['version']}")
    raise typer.Exit


_default_cmd: str | None = shutil.which("ssh") or "ssh"


def create_tunnel_cmd(
    tun: Tunnel,
    *,
    name_tag: bool = True,
    ssh_cmd: str = _default_cmd,
) -> list[str]:
    """Create the command to start a tunnel."""
    base_cmd = [ssh_cmd, "-f", "-N", "-n"]
    if tun.dynamic:
        base_cmd.extend(["-D", f"{tun.dynamic.address}"])
    elif tun.local:
        base_cmd.extend(["-L", tun.local.address])
    base_cmd.append(tun.hostname)
    if name_tag:
        name = tun.name.replace(" ", "-").casefold().lower()
        base_cmd.extend(["-o", f"Tag=tunnels-{name}"])
    base_cmd.append("-o")
    base_cmd.append("ExitOnForwardFailure=yes")
    base_cmd.append("-o")
    base_cmd.append("ServerAliveInterval=30")
    base_cmd.append("-o")
    base_cmd.append("ServerAliveCountMax=5")

    cmd = " ".join(base_cmd)
    return shlex.split(cmd)


def _start_tunnel_if_not_running(tunnel: Tunnel) -> None:
    """Start a tunnel if it is not running."""
    tunnel_name: str = tunnel.name_tag()
    for proc in _get_ssh_processes():
        if f"tunnels-{tunnel.name_tag()}" in shlex.join(proc.cmdline()):
            console.print(f"Tunnel {tunnel_name} is already running.")
            return
    subprocess.run(create_tunnel_cmd(tunnel), check=True)  # noqa: S603
    console.print(f"Starting tunnel {tunnel.name}...")


def _stop_tunnel_if_running(tunnel: Tunnel) -> None:
    """Stop a tunnel if it is running."""
    for proc in _get_ssh_processes():
        if f"tunnels-{tunnel.name_tag()}" in shlex.join(proc.cmdline()):
            proc.terminate()
            console.print(f"Stopping tunnel {tunnel.name}...")
            return
    console.print(f"Tunnel {tunnel.name} is not running.")


@app.command("stop", help="Stop a tunnel or tunnel group.")
def stop(
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
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Stop all tunnels.",
    ),
) -> None:
    """Stop a tunnel or tunnel group.

    Args:
        name (str | None): The name of the tunnel.
        group (str | None): The name of the tunnel group.

    Raises:
        typer.BadParameter: Only one of --name or --group must be specified.
    """
    if not (bool(name) ^ bool(group) ^ all):
        msg = "Only one of --name or --group  or --all must be specified."
        raise typer.BadParameter(msg)
    processes = list(_get_ssh_processes())
    if not processes:
        console.print("No tunnels running.")
        return

    if all:
        for proc in _get_ssh_processes():
            proc.terminate()
        console.print("All tunnels stopped.")
        return

    if name:
        tunnel = next((t for t in settings.tunnels if t.name == name), None)
        if not tunnel:
            msg = f"Tunnel not found: {name}"
            raise typer.BadParameter(msg)
        _stop_tunnel_if_running(tunnel)
        return
    if group:
        tunnels_to_stop = [
            tunnel for tunnel in settings.tunnels if tunnel.group == group
        ]
        if not tunnels_to_stop:
            msg = f"Group not found: {group}"
            raise typer.BadParameter(msg)
        for tunnel in tunnels_to_stop:
            _stop_tunnel_if_running(tunnel)
        console.print("All tunnels stopped.")
        return


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
    all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Start all tunnels.",
    ),
) -> None:
    """Start a tunnel or tunnel group.

    Args:
        name (str | None): The name of the tunnel.
        group (str | None): The name of the tunnel group.

    Raises:
        typer.BadParameter: Only one of --name or --group must be specified.
    """
    if not (bool(name) ^ bool(group) ^ all):
        msg = "Only one of --name or --group  or --all must be specified."
        raise typer.BadParameter(msg)
    if name:
        tunnel = next((t for t in settings.tunnels if t.name == name), None)
        if not tunnel:
            msg = f"Tunnel not found: {name}"
            raise typer.BadParameter(msg)
        _start_tunnel_if_not_running(tunnel)
        return
    if group:
        tunnels_to_start = [
            tunnel for tunnel in settings.tunnels if tunnel.group == group
        ]
        if not tunnels_to_start:
            msg = f"Group not found: {group}"
            raise typer.BadParameter(msg)
        for tunnel in tunnels_to_start:
            _start_tunnel_if_not_running(tunnel)
        return

    for tunnel in settings.tunnels:
        _start_tunnel_if_not_running(tunnel)
    console.print("All tunnels started.")
    return


def _get_ssh_processes() -> Generator[psutil.Process]:
    yield from (p for p in psutil.process_iter() if p.name() == "ssh")


type ConnectionKind = Literal[
    "inet",
    "inet4",
    "inet6",
    "tcp",
    "tcp4",
    "tcp6",
    "udp",
    "udp4",
    "udp6",
    "unix",
    "all",
]


def _list_process_connections(
    proc: psutil.Process,
    kind: ConnectionKind = "inet4",
) -> list[str]:
    """Return the process connections.

    Return socket connections opened by process as a list of
    (fd, family, type, laddr, raddr, status) namedtuples.
    The *kind* parameter filters for connections that match the
    following criteria:

    +------------+----------------------------------------------------+
    | Kind Value | Connections using                                  |
    +------------+----------------------------------------------------+
    | inet       | IPv4 and IPv6                                      |
    | inet4      | IPv4                                               |
    | inet6      | IPv6                                               |
    | tcp        | TCP                                                |
    | tcp4       | TCP over IPv4                                      |
    | tcp6       | TCP over IPv6                                      |
    | udp        | UDP                                                |
    | udp4       | UDP over IPv4                                      |
    | udp6       | UDP over IPv6                                      |
    | unix       | UNIX socket (both UDP and TCP protocols)           |
    | all        | the sum of all the possible families and protocols |
    +------------+----------------------------------------------------+

    Args:
        proc (psutil.Process): The process.
        kind: The kind of connections to list.

    Returns:
        list[str]: The list of connections.
    """
    all_connections = proc.net_connections(kind=kind)
    connections = [
        f"{conn.laddr.ip}:{conn.laddr.port}" for conn in all_connections if conn.laddr
    ]
    connections.extend([
        f"{conn.raddr.ip}:{conn.raddr.port}" for conn in all_connections if conn.raddr
    ])
    connections.sort()
    return connections


class StatusPanel:
    """A panel to show the status of the tunnels."""

    def __init__(self) -> None:
        """Initialize the panel."""
        self.table = Table(
            show_header=True,
            header_style="bold yellow dim",
            show_lines=True,
            box=None,
            expand=True,
        )
        self.table.add_column("Tunnel Name")
        self.table.add_column("PID", style="dim")
        self.table.add_column("Status")
        self.table.add_column("Connections")
        # self.table.add_column("CMD")

    def add_row(self, *args, **kwargs) -> None:
        """Add a row to the table.

        Args:
            values (dict[str, str]): A key value set of column to value mappings
                for the row. The keys should match the column names, extra
                keys are available for long output.
        """
        self.table.add_row(*args, **kwargs)

    def render(self) -> Panel:
        """Render the panel.

        Returns:
            Panel: The panel to display
        """
        return Panel(
            self.table,
            title="[bold]Active Tunnels",
            title_align="left",
            border_style="dim",
        )

    def clear(self) -> None:
        """Clear the panel."""
        if self.table.rows:
            self.table.rows.clear()


@app.command("status", help="List the tunnels.")
def status() -> None:
    """List the tunnels."""
    output = StatusPanel()

    processes = list(_get_ssh_processes())
    for tunnel in settings.tunnels:
        row: dict[str, str] = {
            "name": tunnel.name,
            "pid": "-",
            "status": "[red]Inactive",
            "connections": "-",
            # "cmd": "-",
        }
        for proc in processes:
            cmd = " ".join(proc.cmdline())
            name = f"tunnels-{tunnel.name_tag()}"
            if name in cmd:
                row.update(
                    pid=str(proc.pid),
                    status=f"[green]{proc.status().title()}",
                    connections="\n".join(set(_list_process_connections(proc))) or "-",
                    # cmd=" ".join(proc.cmdline()),
                )
                break
        output.add_row(*row.values())
    console.print(output.render())


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
