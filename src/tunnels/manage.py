"""SSH tunnel management commands for starting and stopping tunnels."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Annotated

import psutil
import typer
from rich.console import Console

from tunnels.config import Tunnel, settings
from tunnels.processes import list_ssh_processes

console: Console = Console()
manage_app: typer.Typer = typer.Typer()


def get_ssh_command() -> str:
    """Get the SSH command for the current platform."""
    if sys.platform == "win32":
        ssh_cmd = (
            shutil.which("ssh.exe")
            or shutil.which("ssh")
            or "C:\\Windows\\System32\\OpenSSH\\ssh.exe"
        )
    else:
        ssh_cmd = shutil.which("ssh") or "ssh"
    return ssh_cmd


def get_autossh_command() -> str | None:
    """Get the autossh command if available."""
    if sys.platform == "win32":
        return shutil.which("autossh.exe") or shutil.which("autossh")
    return shutil.which("autossh")


def create_tunnel_cmd(
    tunnel: Tunnel,
    *,
    use_autossh: bool = True,
) -> list[str]:
    """Create the command to start a tunnel with automatic reconnection support."""
    if autossh_cmd := get_autossh_command() if use_autossh else None:
        base_cmd = [autossh_cmd, "-M", "0", "-f", "-N", "-n"]
    else:
        base_cmd = [get_ssh_command(), "-f", "-N", "-n"]

    if tunnel.dynamic:
        base_cmd.extend(["-D", tunnel.dynamic.address])
    elif tunnel.local:
        base_cmd.extend(["-L", tunnel.local.address])
    base_cmd.extend(
        [
            tunnel.hostname,
            "-o",
            f"Tag=tunnels-{tunnel.name_tag()}-o",
            "ServerAliveInterval=60",
            "-o",
            "ServerAliveCountMax=3",
            "-o",
            "TCPKeepAlive=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ConnectionAttempts=3",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ExitOnForwardFailure=no",
        ],
    )
    return base_cmd


def get_selected_tunnels(
    names: list[str] | None = None,
    group: str | None = None,
    *,
    all_tunnels: bool = False,
) -> list[Tunnel]:
    """Get tunnels based on selection criteria."""
    if not (bool(names) ^ bool(group) ^ all_tunnels):
        msg = "Only one of --name, --group, or --all must be specified."
        raise typer.BadParameter(msg)

    if all_tunnels:
        return settings.configuration.tunnels

    if names:
        response = []
        for name in names:
            tunnel = next(
                (t for t in settings.configuration.tunnels if t.name == name),
                None,
            )
            if not tunnel:
                msg = f"Tunnel not found: {name}"
                raise typer.BadParameter(msg)
            response.append(tunnel)
        return response

    if group:
        tunnels = [t for t in settings.configuration.tunnels if t.group == group]
        if not tunnels:
            msg = f"Group not found: {group}"
            raise typer.BadParameter(msg)
        return tunnels

    return []


def is_tunnel_running(tunnel: Tunnel) -> psutil.Process | None:
    """Check if a tunnel is running and return the process if found."""
    tunnel_tag = f"tunnels-{tunnel.name_tag()}"
    for proc in list_ssh_processes():
        try:
            if tunnel_tag in " ".join(proc.cmdline()):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def start_tunnel(tunnel: Tunnel, *, use_autossh: bool = True) -> bool:
    """Start a tunnel if it's not already running."""
    if is_tunnel_running(tunnel):
        console.print(f"[yellow]Tunnel '{tunnel.name}' is already running[/yellow]")
        return False

    try:
        cmd = create_tunnel_cmd(tunnel, use_autossh=use_autossh)
        subprocess.Popen(cmd)  # noqa: S603

        connection_type = "autossh" if use_autossh and get_autossh_command() else "ssh"
        console.print(
            f"[green]Started tunnel '{tunnel.name}' using {connection_type}[/green]",
        )

        if connection_type == "autossh":
            console.print(
                "[dim]AutoSSH will automatically reconnect if connection drops[/dim]",
            )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start tunnel '{tunnel.name}': {e.stderr}[/red]")
        return False
    except FileNotFoundError:
        console.print(
            "[red]SSH/AutoSSH command not found. Please ensure SSH is installed.[/red]",
        )
        return False
    else:
        return True


def stop_tunnel(tunnel: Tunnel) -> bool:
    """Stop a tunnel if it's running."""
    proc = is_tunnel_running(tunnel)
    if not proc:
        console.print(f"[yellow]Tunnel '{tunnel.name}' is not running[/yellow]")
        return False

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        console.print(f"[yellow]Tunnel '{tunnel.name}' was already stopped[/yellow]")
        return False
    except psutil.TimeoutExpired:
        try:
            # Force kill if graceful termination failed
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            console.print(f"[red]Failed to stop tunnel '{tunnel.name}'[/red]")
            return False
        else:
            console.print(f"[green]Force stopped tunnel '{tunnel.name}'[/green]")
            return True
    else:
        console.print(f"[green]Stopped tunnel '{tunnel.name}'[/green]")
        return True


def _stop_selected_tunnels(tunnels: list[Tunnel]) -> None:
    """Stop the selected tunnels."""
    if not tunnels:
        console.print("[yellow]No tunnels found matching criteria[/yellow]")
        return

    stopped = [int(stop_tunnel(tunnel)) for tunnel in tunnels]
    total = len(tunnels)
    success_count = sum(stopped)
    if success_count == total:
        console.print(f"[green]Successfully stopped {success_count} tunnel(s)[/green]")
    elif success_count > 0:
        console.print(f"[yellow]Stopped {success_count}/{total} tunnel(s)[/yellow]")
    else:
        console.print("[red]Failed to stop any tunnels[/red]")


@manage_app.command("start", help="Start tunnels by name, group, or all.")
def start(
    names: Annotated[
        list[str] | None,
        typer.Option("--name", "-n", help="The name of the tunnel."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="The name of the tunnel group."),
    ] = None,
    *,
    all_tunnels: Annotated[
        bool,
        typer.Option("--all", "-a", help="Start all tunnels."),
    ] = False,
    no_autossh: Annotated[
        bool,
        typer.Option("--no-autossh", help="Disable autossh and use regular SSH."),
    ] = False,
) -> None:
    """Start tunnels based on selection criteria."""
    tunnels = get_selected_tunnels(names, group, all_tunnels=all_tunnels)

    if not tunnels:
        console.print("[yellow]No tunnels found matching criteria[/yellow]")
        return

    use_autossh = not no_autossh
    if use_autossh and not get_autossh_command():
        console.print("[yellow]AutoSSH not found, using regular SSH[/yellow]")
        use_autossh = False
    started = [int(start_tunnel(tunnel, use_autossh=use_autossh)) for tunnel in tunnels]
    total = len(tunnels)
    success_count = sum(started)
    if success_count == total:
        console.print(f"[green]Successfully started {success_count} tunnel(s)[/green]")
    elif success_count > 0:
        console.print(f"[yellow]Started {success_count}/{total} tunnel(s)[/yellow]")
    else:
        console.print("[red]Failed to start any tunnels[/red]")


@manage_app.command("stop", help="Stop tunnels by name, group, or all.")
def stop(
    names: Annotated[
        list[str] | None,
        typer.Option("--name", "-n", help="The name of the tunnel."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", "-g", help="The name of the tunnel group."),
    ] = None,
    *,
    all_tunnels: Annotated[
        bool,
        typer.Option("--all", "-a", help="Stop all tunnels."),
    ] = False,
) -> None:
    """Stop tunnels based on selection criteria."""
    # Handle stopping all tunnels separately for efficiency
    if all_tunnels:
        _stop_selected_tunnels(settings.configuration.tunnels)
        return

    tunnels = get_selected_tunnels(names, group, all_tunnels=all_tunnels)
    _stop_selected_tunnels(tunnels)
