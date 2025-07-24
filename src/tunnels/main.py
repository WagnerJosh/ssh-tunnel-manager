"""The main module for the tunnels package."""

from __future__ import annotations

import contextlib
import shlex
import shutil
import subprocess
from collections.abc import Generator
from importlib.metadata import metadata
from typing import Any

import psutil
import typer
from rich.console import Console

from tunnels.config import Config, Tunnel, settings
from tunnels.output import OutputFormat
from tunnels.status import status_app

console: Console = Console()
app: typer.Typer = typer.Typer()
app.add_typer(
    status_app,
    name="status",
    invoke_without_command=True,
    help="Check the status of tunnels.",
)

meta = metadata("tunnels")
# settings = Config.load()


# global_options: dict[str, Any] = {
#     "output": None,
# }


# _default_cmd: str | None = shutil.which("ssh") or "ssh"


# def create_tunnel_cmd(
#     tun: Tunnel,
#     *,
#     name_tag: bool = True,
#     ssh_cmd: str = _default_cmd,
# ) -> list[str]:
#     """Create the command to start a tunnel."""
#     base_cmd = [ssh_cmd, "-f", "-N", "-n"]
#     if tun.dynamic:
#         base_cmd.extend(["-D", f"{tun.dynamic.address}"])
#     elif tun.local:
#         base_cmd.extend(["-L", tun.local.address])
#     base_cmd.append(tun.hostname)
#     if name_tag:
#         name = tun.name.replace(" ", "-").casefold().lower()
#         base_cmd.extend(["-o", f"Tag=tunnels-{name}"])
#     base_cmd.append("-o")
#     base_cmd.append("ExitOnForwardFailure=yes")
#     base_cmd.append("-o")
#     base_cmd.append("ServerAliveInterval=30")
#     base_cmd.append("-o")
#     base_cmd.append("ServerAliveCountMax=5")

#     cmd = " ".join(base_cmd)
#     return shlex.split(cmd)


# def _start_tunnel_if_not_running(tunnel: Tunnel) -> None:
#     """Start a tunnel if it is not running."""
#     tunnel_name: str = tunnel.name_tag()
#     for proc in _get_ssh_processes():
#         if f"tunnels-{tunnel.name_tag()}" in shlex.join(proc.cmdline()):
#             console.print(f"Tunnel {tunnel_name} is already running.")
#             return
#     subprocess.run(create_tunnel_cmd(tunnel), check=True)  # noqa: S603
#     console.print(f"Starting tunnel {tunnel.name}...")


# def _stop_tunnel_if_running(tunnel: Tunnel) -> None:
#     """Stop a tunnel if it is running."""
#     for proc in _get_ssh_processes():
#         if f"tunnels-{tunnel.name_tag()}" in shlex.join(proc.cmdline()):
#             proc.terminate()
#             console.print(f"Stopping tunnel {tunnel.name}...")
#             return
#     console.print(f"Tunnel {tunnel.name} is not running.")


# @app.command("stop", help="Stop a tunnel or tunnel group.")
# def stop(
#     name: str | None = typer.Option(
#         None,
#         "--name",
#         "-n",
#         help="The name of the tunnel.",
#     ),
#     group: str | None = typer.Option(
#         None,
#         "--group",
#         "-g",
#         help="The name of the tunnel group.",
#     ),
#     all: bool = typer.Option(
#         False,
#         "--all",
#         "-a",
#         help="Stop all tunnels.",
#     ),
# ) -> None:
#     """Stop a tunnel or tunnel group.

#     Args:
#         name (str | None): The name of the tunnel.
#         group (str | None): The name of the tunnel group.

#     Raises:
#         typer.BadParameter: Only one of --name or --group must be specified.
#     """
#     if not (bool(name) ^ bool(group) ^ all):
#         msg = "Only one of --name or --group  or --all must be specified."
#         raise typer.BadParameter(msg)
#     processes = list(_get_ssh_processes())
#     if not processes:
#         console.print("No tunnels running.")
#         return

#     if all:
#         for proc in _get_ssh_processes():
#             proc.terminate()
#         console.print("All tunnels stopped.")
#         return

#     if name:
#         tunnel = next((t for t in settings.tunnels if t.name == name), None)
#         if not tunnel:
#             msg = f"Tunnel not found: {name}"
#             raise typer.BadParameter(msg)
#         _stop_tunnel_if_running(tunnel)
#         return
#     if group:
#         tunnels_to_stop = [
#             tunnel for tunnel in settings.tunnels if tunnel.group == group
#         ]
#         if not tunnels_to_stop:
#             msg = f"Group not found: {group}"
#             raise typer.BadParameter(msg)
#         for tunnel in tunnels_to_stop:
#             _stop_tunnel_if_running(tunnel)
#         console.print("All tunnels stopped.")
#         return


# @app.command("start", help="Start a tunnel or tunnel group.")
# def start(
#     name: str | None = typer.Option(
#         None,
#         "--name",
#         "-n",
#         help="The name of the tunnel.",
#     ),
#     group: str | None = typer.Option(
#         None,
#         "--group",
#         "-g",
#         help="The name of the tunnel group.",
#     ),
#     all_tunnels: bool = typer.Option(  # noqa: FBT001
#         False,  # noqa: FBT003
#         "--all",
#         "-a",
#         help="Start all tunnels.",
#     ),
# ) -> None:
#     """Start a tunnel or tunnel group.

#     Args:
#         name (str | None): The name of the tunnel.
#         group (str | None): The name of the tunnel group.
#         all_tunnels (bool): Start all tunnels.

#     Raises:
#         typer.BadParameter: Only one of --name or --group must be specified.
#     """
#     if not (bool(name) ^ bool(group) ^ all_tunnels):
#         msg = "Only one of --name or --group  or --all must be specified."
#         raise typer.BadParameter(msg)
#     if name:
#         tunnel = next((t for t in settings.tunnels if t.name == name), None)
#         if not tunnel:
#             msg = f"Tunnel not found: {name}"
#             raise typer.BadParameter(msg)
#         _start_tunnel_if_not_running(tunnel)
#         raise typer.Exit
#     if group:
#         tunnels_to_start = [
#             tunnel for tunnel in settings.tunnels if tunnel.group == group
#         ]
#         if not tunnels_to_start:
#             msg = f"Group not found: {group}"
#             raise typer.BadParameter(msg)
#         for tunnel in tunnels_to_start:
#             _start_tunnel_if_not_running(tunnel)
#             raise typer.Exit

#     for tunnel in settings.tunnels:
#         _start_tunnel_if_not_running(tunnel)
#     console.print("All tunnels started.")


# def _get_ssh_processes() -> Generator[psutil.Process]:
#     with contextlib.suppress(psutil.AccessDenied, psutil.NoSuchProcess):
#         yield from (p for p in psutil.process_iter() if p.name() == "ssh")


def _version_callback(*, value: bool) -> None:
    if not value:
        return
    typer.echo(f"{meta['name'].lower()} {meta['version']}")
    raise typer.Exit


@app.callback()
def main_callback(
    _format: OutputFormat | None = typer.Option(  # noqa: B008
        None,
        "-f",
        "--format",
        help="Choose a specific output format that should be used.",
    ),
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
    settings.global_options["output"] = _format


def run_app() -> None:
    """Run the Tunnels application."""
    app()
