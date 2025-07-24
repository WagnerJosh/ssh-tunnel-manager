"""A helper module for retrieving process information."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Literal

import psutil

if TYPE_CHECKING:
    from collections.abc import Generator


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


def list_ssh_processes() -> Generator[psutil.Process]:
    """List all running SSH processes.

    Yields:
        psutil.Process: An SSH process instances.
    """
    with contextlib.suppress(psutil.AccessDenied, psutil.NoSuchProcess):
        yield from (p for p in psutil.process_iter() if p.name() == "ssh")


def list_process_socket_connections(
    proc: psutil.Process,
    kind: ConnectionKind = "inet4",
) -> list[str]:
    """Return unique socket connections for a process.

    Args:
        proc: The process to get connections for.
        kind: The type of connections to filter (inet4, tcp, udp, etc.).
            see 'ConnectionKind' for a list of valid values.

    Returns:
        list[str]: A sorted list of connections, in the format of "ip_address":"port".
    """
    with contextlib.suppress(psutil.AccessDenied, psutil.NoSuchProcess):
        network_connections = proc.net_connections(kind=kind)
        connections = set()

        for conn in network_connections:
            if conn.laddr:
                connections.add(f"{conn.laddr.ip}:{conn.laddr.port}")
            if conn.raddr:
                connections.add(f"{conn.raddr.ip}:{conn.raddr.port}")
        return sorted(connections)
    return []
