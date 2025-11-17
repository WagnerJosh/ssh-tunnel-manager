"""The Tunnel status module.

Maintains the cli functions for checking the status of the tunnel.
"""

from __future__ import annotations

import os
import subprocess
from functools import partial
from typing import Annotated, Any

import psutil
import rich
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text
from typer import Exit, Option, Typer

from tunnels.config import settings
from tunnels.output import OutputFormat, format_output
from tunnels.processes import list_process_socket_connections, list_ssh_processes

status_app: Typer = Typer()
console: Console = Console()


def _run_command(command: list[str]) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def _detect_vpn_type() -> tuple[str, str | None]:
    """Detect VPN type and return (type, ip).

    Returns:
        tuple: (vpn_type, ip_address) where vpn_type is one of:
            - "cisco": Cisco Secure Client (Production)
            - "ivanti": Ivanti Secure Access (Lab)
            - "none": No VPN connected
    """
    # Check if utun8 exists
    returncode, _ = _run_command(["ifconfig", "utun8"])
    if returncode != 0:
        return "none", None

    # Get IP address
    returncode, output = _run_command(["ifconfig", "utun8"])
    ip_address: str | None = None
    if returncode == 0:
        for line in output.split("\n"):
            if "inet " in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    ip_address = parts[1]
                    break

    # Check for Cisco VPN (has routes to proxy servers)
    returncode, route_output = _run_command(["netstat", "-rn"])
    has_proxy_routes = (
        returncode == 0 and "198.161.14" in route_output and "utun8" in route_output
    )
    if has_proxy_routes:
        return "cisco", ip_address

    # Has utun8 but no proxy routes = Ivanti VPN
    return "ivanti", ip_address


def create_vpn_status_rows() -> list[dict[str, Any]]:
    """Create VPN and proxy status information.

    Returns:
        list[dict[str, Any]]: A list with VPN and proxy status.
    """
    vpn_type, vpn_ip = _detect_vpn_type()
    proxy_https: str | None = os.environ.get("HTTPS_PROXY")
    proxy_http: str | None = os.environ.get("HTTP_PROXY")

    vpn_status: str = "Disconnected"
    vpn_details: str = "-"

    if vpn_type == "cisco":
        vpn_status = "Connected"
        vpn_details = f"Cisco (Production) - {vpn_ip}"
    elif vpn_type == "ivanti":
        vpn_status = "Connected"
        vpn_details = f"Ivanti (Lab) - {vpn_ip}"

    proxy_status: str = "Enabled" if proxy_https else "Disabled"
    proxy_details: str = proxy_https or "-"

    return [
        {"item": "VPN", "status": vpn_status, "details": vpn_details},
        {"item": "Proxy", "status": proxy_status, "details": proxy_details},
    ]


def create_status_rows() -> list[dict[str, Any]]:
    """Create a list of rows with the current tunnel status.

    Each row contains the tunnel name, group, hostname, PID, status, and connections.

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
            "hostname": tunnel.hostname,
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
        Exit: If live is not True, this will raise an Exit exception to stop the
        application after displaying the status.
    """
    output_render = partial(format_output, format_=format_, columns=columns)
    if not live:
        console.print(output_render(create_status_rows()))
        raise Exit

    with Live(refresh_per_second=4) as live_view:
        while True:
            output = output_render(create_status_rows())
            live_view.update(output)


@status_app.command("vpn-status", help="Get the current status of vpn connections.")
def vpn_status(
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
    """Get the current status of the configured VPN.

    Args:
        live (bool): If True, drop into a live status view that updates every 4
        seconds.
        format_ (OutputFormat): The output format to use for the status.
        columns (list[str] | None): The columns to display in the status output.
            If not specified, all columns are displayed.

    Raises:
        Exit: If live is not True, this will raise an Exit exception to stop the
        application after displaying the status.
    """
    output_render = partial(format_output, format_=format_, columns=columns)
    if not live:
        console.print(output_render(create_vpn_status_rows()))
        raise Exit

    with Live(refresh_per_second=4) as live_view:
        while True:
            output = output_render(create_vpn_status_rows())
            live_view.update(output)


@status_app.command("list", help="List the configured tunnels.")
def list_tunnels(
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
        Exit: If live is not True, this will raise an Exit exception to stop the
        application after displaying the status.
    """
    output_render = partial(format_output, format_=format_, columns=columns)

    if not live:
        console.print(output_render(settings.configuration.tunnels))
        raise Exit

    with Live(refresh_per_second=4) as live_view:
        while True:
            output = output_render(settings.configuration.tunnels)
            live_view.update(output)
